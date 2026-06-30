from app.extensions import db
from app.models import CommunicationSignal
from app.services.operational import public_comms_zones


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
    # Ya no hay formulario; la sección sigue mostrando las zonas (ingeridas/existentes).
    html = client.get("/directorio/zonas").text
    assert "Zonas sin comunicación" in html
