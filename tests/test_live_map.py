from datetime import datetime, timezone

from app.extensions import db
from app.models import DirectoryEntry, IngestedEvent, Incident


def test_live_endpoint_empty(client):
    payload = client.get("/mapa/live").json
    assert payload["situation"] == []
    assert payload["incidents"] == []
    assert payload["events"] == []
    assert payload["services"] == []
    # La capa de intensidad de zonas afectadas es un modelo fijo, siempre presente.
    assert len(payload["intensity"]) > 100
    assert all(len(point) == 3 for point in payload["intensity"])


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
            public_id="inc-1", source_slug="sample", external_id="inc-1", content_hash="h",
            category="collapsed_structure", severity="critical", label="Edificio X",
            address_public="Av. Principal", latitude=10.49, longitude=-66.85,
            status="reported", situation_note="Personas atrapadas", in_region=True,
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

    event = payload["events"][0]
    assert event["magnitude"] == 4.6
    assert event["place"] == "Región Capital"
    assert event["attribution"] == "U.S. Geological Survey"

    service = payload["services"][0]
    assert service["category"] == "hospital"
    assert service["category_label"] == "Hospital"
    assert service["name"] == "Hospital Central"
    assert service["emergency"] is True
