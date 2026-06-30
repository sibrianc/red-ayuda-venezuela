from app.ingestion.ioda import parse_ioda_alerts
from app.ingestion.pipeline import ingest_comms_zones
from app.models import CommunicationSignal
from app.services.operational import public_comms_zones


def _payload(*names):
    return {"data": [
        {"entity": {"type": "region", "code": f"VE-{n[:2].upper()}", "name": n,
                    "attrs": {"latitude": 10.6, "longitude": -66.9}},
         "time": 1_700_000_000 + i, "level": "critical", "datasource": "ping-slash24"}
        for i, n in enumerate(names)
    ]}


def test_parse_ioda_alerts_extracts_zone_and_geo():
    zones = parse_ioda_alerts(_payload("Vargas"))
    assert len(zones) == 1
    z = zones[0]
    assert z.zone_label == "Vargas"
    assert z.latitude == 10.6 and z.longitude == -66.9
    assert "IODA" in z.public_note


def test_parse_ioda_alerts_handles_alerts_wrapper_and_missing_geo():
    payload = {"data": {"alerts": [
        {"entity": {"code": "VE-A", "name": "Distrito Capital", "attrs": {}}, "time": 1, "level": "warning"},
        {"entity": {"name": ""}, "time": 2},  # sin nombre → se ignora
    ]}}
    zones = parse_ioda_alerts(payload)
    assert [z.zone_label for z in zones] == ["Distrito Capital"]
    assert zones[0].latitude is None and zones[0].longitude is None


def test_parse_ioda_keeps_latest_alert_per_region():
    payload = {"data": [
        {"entity": {"code": "VE-V", "name": "Vargas"}, "time": 10, "level": "warning"},
        {"entity": {"code": "VE-V", "name": "Vargas"}, "time": 99, "level": "critical"},
    ]}
    zones = parse_ioda_alerts(payload)
    assert len(zones) == 1
    assert "critical" in zones[0].public_note


def test_ingest_comms_zones_is_idempotent_and_auto_resolves(app):
    with app.app_context():
        first = ingest_comms_zones(parse_ioda_alerts(_payload("Vargas", "Distrito Capital")))
        assert first.new == 2
        assert CommunicationSignal.query.filter_by(source="ioda").count() == 2
        assert {z["zone_label"] for z in public_comms_zones()} == {"Vargas", "Distrito Capital"}

        # Reingesta con solo Vargas activa: Distrito Capital debe quedar 'resolved'.
        second = ingest_comms_zones(parse_ioda_alerts(_payload("Vargas")))
        assert second.updated == 1
        labels = {z["zone_label"] for z in public_comms_zones()}
        assert labels == {"Vargas"}  # la recuperada ya no aparece
        resolved = CommunicationSignal.query.filter_by(zone_label="Distrito Capital").one()
        assert resolved.status == "resolved"
