from datetime import datetime, timezone

from app.extensions import db
from app.ingestion.connectors import (
    in_venezuela_region,
    parse_gdacs_geojson,
    parse_usgs_geojson,
)
from app.ingestion.pipeline import event_overview, ingest_events
from app.models import IngestedEvent, SourceRecord


CARACAS_TIME_MS = int(datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc).timestamp() * 1000)


def feature(event_id, mag, lon, lat, depth=10.0, *, time_ms=CARACAS_TIME_MS, **props):
    base_props = {
        "mag": mag,
        "place": props.get("place", "zona de prueba"),
        "time": time_ms,
        "url": f"https://earthquake.usgs.gov/earthquakes/eventpage/{event_id}",
        "type": "earthquake",
        "title": props.get("title", f"M {mag}"),
        "tsunami": props.get("tsunami", 0),
        "alert": props.get("alert"),
        "sig": props.get("sig"),
        "felt": props.get("felt"),
    }
    return {
        "type": "Feature",
        "id": event_id,
        "properties": base_props,
        "geometry": {"type": "Point", "coordinates": [lon, lat, depth]},
    }


def collection(*features):
    return {"type": "FeatureCollection", "metadata": {"api": "1.0"}, "features": list(features)}


# Venezuela ~ (lon -66.9, lat 10.5); Japón ~ (lon 140, lat 35).
VENEZUELA = dict(lon=-66.9, lat=10.5)
JAPAN = dict(lon=140.0, lat=35.0)


def sample_collection():
    return collection(
        feature("vz1", 4.5, time_ms=CARACAS_TIME_MS, tsunami=1, alert="green", sig=312, **VENEZUELA),
        feature("vz2", 1.8, lon=-67.0, lat=9.0),
        feature("jp1", 6.0, **JAPAN),
        {"type": "Feature", "id": "bad1", "properties": {"mag": 3}, "geometry": None},
        {"type": "Feature", "id": None, "properties": {}, "geometry": {"coordinates": [-66, 10, 5]}},
    )


# --- Parseo puro (sin red, sin base) ---------------------------------------


def test_parse_extracts_canonical_fields():
    events = {e.external_id: e for e in parse_usgs_geojson(sample_collection())}
    vz1 = events["vz1"]
    assert vz1.magnitude == 4.5
    assert vz1.latitude == 10.5 and vz1.longitude == -66.9  # respeta orden lon,lat
    assert vz1.depth_km == 10.0
    assert vz1.tsunami is True
    assert vz1.alert_level == "green"
    assert vz1.significance == 312
    assert vz1.occurred_at == datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)
    assert vz1.attribution == "U.S. Geological Survey"


def test_parse_skips_invalid_features():
    ids = {e.external_id for e in parse_usgs_geojson(sample_collection())}
    assert ids == {"vz1", "vz2", "jp1"}  # descarta sin geometría y sin id


def test_region_flagging():
    assert in_venezuela_region(10.5, -66.9) is True
    assert in_venezuela_region(35.0, 140.0) is False
    assert in_venezuela_region(None, None) is False


# --- Pipeline (requiere app + base) ----------------------------------------


def test_ingest_persists_new_events(app):
    stats = ingest_events(parse_usgs_geojson(sample_collection()))
    assert stats.new == 3
    assert stats.received == 3  # parse ya descartó los 2 features inválidos
    assert db.session.query(IngestedEvent).count() == 3
    assert db.session.query(SourceRecord).count() == 3
    assert db.session.query(IngestedEvent).filter_by(in_region=True).count() == 2


def test_ingest_is_idempotent(app):
    events = parse_usgs_geojson(sample_collection())
    ingest_events(events)
    second = ingest_events(parse_usgs_geojson(sample_collection()))
    assert second.new == 0
    assert second.updated == 0
    assert second.unchanged == 3
    assert db.session.query(IngestedEvent).count() == 3  # sin duplicados


def test_ingest_detects_changes(app):
    ingest_events(parse_usgs_geojson(sample_collection()))
    changed = collection(feature("vz1", 5.1, **VENEZUELA))  # mismo id, magnitud distinta
    stats = ingest_events(parse_usgs_geojson(changed))
    assert stats.updated == 1
    assert stats.new == 0
    event = db.session.query(IngestedEvent).filter_by(external_id="vz1").one()
    assert event.magnitude == 5.1
    assert db.session.query(IngestedEvent).count() == 3  # sigue sin duplicar


def test_min_magnitude_filter(app):
    stats = ingest_events(parse_usgs_geojson(sample_collection()), min_magnitude=4.0)
    assert stats.new == 2  # descarta vz2 (1.8)
    assert stats.filtered_out == 1
    assert db.session.query(IngestedEvent).filter_by(external_id="vz2").count() == 0


def test_region_only_filter(app):
    stats = ingest_events(parse_usgs_geojson(sample_collection()), region_only=True)
    assert stats.new == 2  # descarta jp1 (Japón)
    assert stats.filtered_out == 1
    assert db.session.query(IngestedEvent).filter_by(external_id="jp1").count() == 0


def test_event_overview_aggregates(app):
    ingest_events(parse_usgs_geojson(sample_collection()))
    overview = event_overview()
    assert overview["total"] == 3
    assert overview["en_region"] == 2
    assert overview["por_magnitud"]["<2.5"] == 1
    assert overview["por_magnitud"]["4.0–4.9"] == 1
    assert overview["por_magnitud"]["6.0+"] == 1
    assert overview["por_tipo"]["earthquake"] == 3
    assert overview["evento_mas_reciente"] is not None


# --- GDACS (multi-amenaza) -------------------------------------------------


def gdacs_feature(event_id, eventtype, alertlevel, country, lon, lat, severity,
                  *, fromdate="2026-06-21T03:00:00", geometry=None):
    return {
        "type": "Feature",
        "properties": {
            "eventtype": eventtype,
            "eventid": event_id,
            "name": f"{eventtype} en {country}",
            "description": f"{eventtype} en {country}",
            "alertlevel": alertlevel,
            "country": country,
            "fromdate": fromdate,
            "severitydata": {
                "severity": severity,
                "severitytext": f"Severidad {severity}",
                "severityunit": "x",
            },
            "url": {"report": f"https://www.gdacs.org/report.aspx?eventid={event_id}"},
        },
        "geometry": geometry or {"type": "Point", "coordinates": [lon, lat]},
    }


def gdacs_collection():
    return {
        "type": "FeatureCollection",
        "features": [
            gdacs_feature(1001, "EQ", "Orange", "Venezuela", -67.0, 10.2, 5.5),
            gdacs_feature(1002, "FL", "Green", "Brazil", -50.0, -10.0, 2.0),
            gdacs_feature(
                1003, "TC", "Red", "Philippines", 0, 0, 3.0,
                geometry={"type": "Polygon",
                          "coordinates": [[[120.0, 14.0], [122.0, 14.0], [122.0, 16.0], [120.0, 16.0]]]},
            ),
            {"type": "Feature", "properties": {"eventtype": "EQ"}, "geometry": None},  # sin eventid
        ],
    }


def test_parse_gdacs_maps_multihazard_fields():
    events = {e.external_id: e for e in parse_gdacs_geojson(gdacs_collection())}
    eq = events["EQ1001"]
    assert eq.event_type == "earthquake"
    assert eq.hazard_code == "EQ"
    assert eq.magnitude == 5.5  # solo los sismos llevan magnitud
    assert eq.severity_value == 5.5
    assert eq.country == "Venezuela"
    assert eq.alert_level == "orange"
    assert eq.occurred_at == datetime(2026, 6, 21, 3, 0, tzinfo=timezone.utc)
    assert eq.attribution.startswith("GDACS")

    flood = events["FL1002"]
    assert flood.event_type == "flood"
    assert flood.magnitude is None  # las inundaciones no tienen magnitud sísmica
    assert flood.severity_value == 2.0


def test_parse_gdacs_polygon_centroid_and_skips_invalid():
    events = {e.external_id: e for e in parse_gdacs_geojson(gdacs_collection())}
    assert set(events) == {"EQ1001", "FL1002", "TC1003"}  # descarta el sin eventid
    cyclone = events["TC1003"]
    assert cyclone.longitude == 121.0 and cyclone.latitude == 15.0  # centroide del polígono


def test_gdacs_pipeline_flags_region_and_persists(app):
    stats = ingest_events(parse_gdacs_geojson(gdacs_collection()))
    assert stats.new == 3
    assert db.session.query(IngestedEvent).filter_by(in_region=True).count() == 1  # solo Venezuela
    overview = event_overview()
    assert overview["por_tipo"]["earthquake"] == 1
    assert overview["por_tipo"]["flood"] == 1
    assert overview["por_tipo"]["cyclone"] == 1


def test_event_types_filter_keeps_only_earthquakes(app):
    # GDACS trae multi-amenaza; el filtro deja entrar solo terremotos (el enfoque real).
    stats = ingest_events(parse_gdacs_geojson(gdacs_collection()), event_types={"earthquake"})
    assert stats.new == 1  # solo EQ1001
    assert stats.filtered_out == 2  # se descartan inundación y ciclón
    assert db.session.query(IngestedEvent).filter_by(event_type="flood").count() == 0
    assert db.session.query(IngestedEvent).filter_by(event_type="cyclone").count() == 0


def test_since_filter_drops_older_events(app):
    after = datetime(2026, 6, 25, tzinfo=timezone.utc)  # los sismos de muestra son del 2026-06-20
    stats = ingest_events(parse_usgs_geojson(sample_collection()), since=after)
    assert stats.new == 0
    assert stats.filtered_out == 3
    before = datetime(2026, 6, 1, tzinfo=timezone.utc)
    stats2 = ingest_events(parse_usgs_geojson(sample_collection()), since=before)
    assert stats2.new == 3


def test_mixed_sources_do_not_collide(app):
    ingest_events(parse_usgs_geojson(sample_collection()))
    ingest_events(parse_gdacs_geojson(gdacs_collection()))
    assert db.session.query(IngestedEvent).count() == 6  # 3 USGS + 3 GDACS
    assert db.session.query(SourceRecord).count() == 6
    # Re-correr ambos no duplica nada.
    s_usgs = ingest_events(parse_usgs_geojson(sample_collection()))
    s_gdacs = ingest_events(parse_gdacs_geojson(gdacs_collection()))
    assert s_usgs.new == 0 and s_gdacs.new == 0
    assert db.session.query(IngestedEvent).count() == 6
