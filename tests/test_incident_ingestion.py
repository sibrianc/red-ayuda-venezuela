from app.extensions import db
from app.ingestion.incidents import (
    curated_collapsed_structures,
    parse_hdx_damage_geojson,
)
from app.ingestion.pipeline import ingest_incidents
from app.models import Incident
from app.services.operational import public_incidents


def _feature(identifier, damage, confidence, longitude=-66.9, latitude=10.6):
    return {
        "type": "Feature",
        "properties": {
            "id": identifier,
            "damage": damage,
            "confidence": confidence,
        },
        "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
    }


def test_parse_hdx_damage_keeps_candidate_status_and_never_infers_people():
    payload = {
        "type": "FeatureCollection",
        "features": [
            _feature("1", "destroyed", 0.91),
            _feature("2", "major-damage", 0.72),
            _feature("3", "minor-damage", 0.44),
            _feature("4", "unknown", 0.99),
            _feature("5", "destroyed", 1.4),
            _feature("6", "destroyed", 0.8, longitude=20, latitude=20),
        ],
    }

    incidents = parse_hdx_damage_geojson(payload)

    assert [incident.category for incident in incidents] == [
        "destroyed_structure_candidate",
        "major_damage_candidate",
        "minor_damage_candidate",
    ]
    assert all(incident.verification_status == "candidate" for incident in incidents)
    assert all(incident.people_trapped_status == "unknown" for incident in incidents)
    assert incidents[0].confidence == 0.91
    assert "requiere validación" in incidents[0].situation_note


def test_incident_ingestion_is_idempotent_and_updates(app):
    original = parse_hdx_damage_geojson({"features": [_feature("1", "destroyed", 0.91)]})
    first = ingest_incidents(original)
    second = ingest_incidents(original)

    changed_payload = {"features": [_feature("1", "destroyed", 0.95)]}
    changed = ingest_incidents(parse_hdx_damage_geojson(changed_payload))

    assert first.new == 1
    assert second.unchanged == 1
    assert changed.updated == 1
    assert db.session.query(Incident).count() == 1
    assert db.session.query(Incident).one().confidence == 0.95


def test_damage_candidates_are_public_only_as_candidates(app):
    ingest_incidents(
        parse_hdx_damage_geojson({"features": [_feature("1", "destroyed", 0.91)]})
    )

    result = public_incidents(require_coordinates=True)
    assert len(result) == 1
    assert result[0]["is_damage_candidate"] is True
    assert result[0]["verification_status"] == "candidate"
    assert result[0]["people_trapped_status"] == "unknown"
    assert result[0]["source_url"].startswith("https://data.humdata.org/")


def test_curated_collapses_are_named_but_not_fake_geocoded():
    records = curated_collapsed_structures()

    assert len(records) >= 40
    assert len({record.external_id for record in records}) == len(records)
    assert all(record.category == "collapsed_structure" for record in records)
    assert all(record.verification_status == "reported" for record in records)
    assert all(record.latitude is None and record.longitude is None for record in records)
    assert all(record.people_trapped_status == "unknown" for record in records)


def test_map_links_unlocated_structures_to_nominal_directory(app, client):
    ingest_incidents(curated_collapsed_structures())

    html = client.get("/mapa").text
    assert "41 estructuras publicadas" in html
    assert "Ver lista nominal y fuentes" in html
    assert "category=collapsed_structure" in html
