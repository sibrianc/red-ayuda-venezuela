from app.extensions import db
from app.ingestion.connectors import build_overpass_query, parse_overpass
from app.ingestion.pipeline import directory_overview, ingest_directory
from app.models import DirectoryEntry


def overpass_payload():
    return {
        "version": 0.6,
        "generator": "Overpass",
        "elements": [
            {"type": "node", "id": 1, "lat": 10.5, "lon": -66.9,
             "tags": {"amenity": "hospital", "name": "Hospital Central",
                      "addr:street": "Av Urdaneta", "addr:housenumber": "10",
                      "addr:city": "Caracas", "phone": "+58 212 0000000",
                      "operator": "MPPS", "emergency": "yes"}},
            {"type": "way", "id": 2, "center": {"lat": 10.2, "lon": -67.0},
             "tags": {"amenity": "clinic", "name": "Clínica Norte"}},
            {"type": "node", "id": 3, "lat": 9.0, "lon": -67.5,
             "tags": {"amenity": "drinking_water"}},  # sin nombre → etiqueta por categoría
            {"type": "node", "id": 4, "tags": {"amenity": "hospital", "name": "Sin coords"}},  # descartar
            {"type": "node", "lat": 10.0, "lon": -66.0,
             "tags": {"amenity": "pharmacy", "name": "Sin id"}},  # sin id → descartar
            {"type": "node", "id": 6, "lat": 40.4, "lon": -3.7,
             "tags": {"amenity": "hospital", "name": "Hospital Madrid"}},  # fuera de región
        ],
    }


# --- Parseo puro -----------------------------------------------------------


def test_parse_overpass_maps_fields_and_skips_invalid():
    entries = {e.external_id: e for e in parse_overpass(overpass_payload())}
    assert set(entries) == {"node/1", "way/2", "node/3", "node/6"}  # descarta sin coords y sin id

    hospital = entries["node/1"]
    assert hospital.category == "hospital"
    assert hospital.emergency is True
    assert hospital.address_public == "Av Urdaneta 10, Caracas"
    assert hospital.phone_public == "+58 212 0000000"
    assert hospital.operator == "MPPS"
    assert hospital.source_url == "https://www.openstreetmap.org/node/1"

    clinic = entries["way/2"]
    assert clinic.category == "clinic"
    assert clinic.latitude == 10.2 and clinic.longitude == -67.0  # usa center de la vía

    water = entries["node/3"]
    assert water.category == "water_point"
    assert water.name == "Punto de agua"  # etiqueta por defecto al no tener nombre
    assert water.emergency is False


def test_build_overpass_query_targets_venezuela():
    query = build_overpass_query()
    assert "hospital" in query and "shelter" in query and "out center tags" in query
    assert "-74.5" in query and "13.0" in query  # recuadro de Venezuela


# --- Ingesta (requiere app + base) -----------------------------------------


def test_ingest_directory_persists_and_flags_region(app):
    stats = ingest_directory(parse_overpass(overpass_payload()))
    assert stats.new == 4
    assert db.session.query(DirectoryEntry).count() == 4
    assert db.session.query(DirectoryEntry).filter_by(in_region=True).count() == 3  # Madrid fuera


def test_ingest_directory_region_only(app):
    stats = ingest_directory(parse_overpass(overpass_payload()), region_only=True)
    assert stats.new == 3
    assert stats.filtered_out == 1  # descarta Madrid
    assert db.session.query(DirectoryEntry).filter_by(name="Hospital Madrid").count() == 0


def test_ingest_directory_is_idempotent(app):
    ingest_directory(parse_overpass(overpass_payload()))
    second = ingest_directory(parse_overpass(overpass_payload()))
    assert second.new == 0
    assert second.unchanged == 4
    assert db.session.query(DirectoryEntry).count() == 4  # sin duplicados


def test_directory_overview_by_category(app):
    ingest_directory(parse_overpass(overpass_payload()))
    overview = directory_overview()
    assert overview["total"] == 4
    assert overview["por_categoria"]["hospital"] == 2
    assert overview["por_categoria"]["clinic"] == 1
    assert overview["por_categoria"]["water_point"] == 1
