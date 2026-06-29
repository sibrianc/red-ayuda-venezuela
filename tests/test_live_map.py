from datetime import datetime, timezone

from app.extensions import db
from app.models import DirectoryEntry, IngestedEvent, Incident


def test_live_endpoint_empty(client):
    payload = client.get("/mapa/live").json
    assert payload["situation"] == []
    assert payload["incidents"] == []
    assert payload["events"] == []
    assert payload["services"] == []
    assert payload["intensity"] == []


def test_live_endpoint_returns_events_and_services(app, client):
    with app.app_context():
        db.session.add(IngestedEvent(
            public_id="evt-1", source_slug="usgs-earthquake-geojson", external_id="us1",
            content_hash="h", event_type="earthquake", hazard_code="EQ", magnitude=4.6,
            place="Región Capital", latitude=10.5, longitude=-66.9, depth_km=12.0,
            occurred_at=datetime(2026, 6, 25, tzinfo=timezone.utc), in_region=True,
            attribution="U.S. Geological Survey",
        ))
        db.session.add(DirectoryEntry(
            public_id="svc-1", source_slug="osm-overpass", external_id="node/1",
            content_hash="h", category="hospital", name="Hospital Central",
            latitude=10.51, longitude=-66.91, emergency=True, in_region=True,
            service_status="unknown", attribution="© OpenStreetMap contributors",
        ))
        db.session.add(Incident(
            public_id="inc-1", source_slug="official-test", external_id="inc-1", content_hash="h",
            category="collapsed_structure", severity="critical", label="Edificio X",
            address_public="Av. Principal", latitude=10.49, longitude=-66.85,
            status="active", verification_status="verified",
            people_trapped_status="unknown",
            situation_note="Colapso confirmado; ocupación sin determinar", in_region=True,
        ))
        db.session.commit()

    payload = client.get("/mapa/live").json
    assert len(payload["incidents"]) == 1
    assert len(payload["events"]) == 1
    assert len(payload["services"]) == 1

    incident = payload["incidents"][0]
    assert incident["category"] == "collapsed_structure"
    assert incident["category_label"] == "Edificio colapsado"
    assert incident["severity"] == "critical"
    assert incident["weight"] == 1.0
    assert incident["label"] == "Edificio X"
    assert incident["verification_status"] == "verified"
    assert incident["people_trapped_status"] == "unknown"
    assert len(payload["intensity"]) == 1

    event = payload["events"][0]
    assert event["magnitude"] == 4.6
    assert event["place"] == "Región Capital"
    assert event["attribution"] == "U.S. Geological Survey"

    service = payload["services"][0]
    assert service["category"] == "hospital"
    assert service["category_label"] == "Hospital"
    assert service["name"] == "Hospital Central"
    assert service["emergency"] is True


def test_missing_persons_drive_heat_intensity(app):
    from app.models import PersonRecord
    from app.services.operational import affected_intensity, missing_person_hotspots

    with app.app_context():
        for i in range(4):
            db.session.add(PersonRecord(
                source_slug="t", external_id=f"m{i}", content_hash=str(i),
                full_name=f"Persona {i}", person_status="missing", is_minor=False,
                last_known_location="La Guaira",
            ))
        db.session.commit()
        hot = missing_person_hotspots()
        assert hot[0]["label"] == "La Guaira"
        assert hot[0]["count"] == 4
        # La zona con más desaparecidos es la más intensa del mapa de calor.
        assert any(round(p[2], 2) >= 0.99 for p in affected_intensity())
