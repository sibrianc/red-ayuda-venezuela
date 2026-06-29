from app.extensions import db
from app.models import CommunicationSignal
from app.services.operational import public_comms_zones


def test_comms_report_form_renders(client):
    assert client.get("/reportes/sin-comunicacion").status_code == 200


def test_comms_report_creates_advisory_alert(client, app):
    response = client.post(
        "/reportes/sin-comunicacion",
        data={
            "zone_label": "Sector La Cruz, Petare",
            "public_note": "Sin señal de teléfono ni internet desde el sismo.",
            "reporter_contact_private": "+58 000 0000000",
            "privacy_consent": "y",
            "website": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302  # redirige al directorio
    with app.app_context():
        signal = CommunicationSignal.query.one()
        assert signal.zone_label == "Sector La Cruz, Petare"
        assert signal.status == "advisory"
        assert signal.source == "community"
        assert signal.reporter_contact_private == "+58 000 0000000"


def test_public_comms_zones_hide_private_and_filter(app):
    with app.app_context():
        db.session.add(CommunicationSignal(
            zone_label="Petare", public_note="incomunicado",
            reporter_contact_private="CONTACTO-SECRETO", status="advisory", source="community",
        ))
        db.session.add(CommunicationSignal(
            zone_label="Chacao", status="resolved", source="community",
        ))
        db.session.commit()

    zones = public_comms_zones()
    assert len(zones) == 1  # la resuelta no aparece
    assert zones[0]["zone_label"] == "Petare"
    assert "reporter_contact_private" not in zones[0]
    assert "CONTACTO-SECRETO" not in str(zones)
    assert len(public_comms_zones(q="petare")) == 1
    assert len(public_comms_zones(q="zzz")) == 0


def test_directory_shows_comms_section(client):
    html = client.get("/directorio").text
    assert "Zonas sin comunicación" in html
    assert "Reportar zona sin comunicación" in html
