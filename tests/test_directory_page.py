from app.constants import ReportStatus
from app.extensions import db
from app.models import MissingPersonReport
from app.services.operational import public_missing_persons


def _person(first, last, **overrides):
    values = {
        "first_name": first, "last_name": last, "age": 30, "involves_minor": False,
        "status": ReportStatus.APPROVED, "is_public": True,
        "location_text": "Caracas", "description_public": "Visto por última vez en la zona.",
        "reporter_name_private": "Reportante", "reporter_contact_private": "+58 000",
    }
    values.update(overrides)
    return MissingPersonReport(**values)


def test_directory_page_renders(client):
    response = client.get("/directorio")
    assert response.status_code == 200
    html = response.text
    assert "Reportar un familiar" in html
    assert "Incidentes de prioridad" in html
    assert "Registros oficiales" in html


def test_public_missing_persons_excludes_minors_and_unapproved(app):
    with app.app_context():
        db.session.add(_person("Ana", "Pérez"))  # adulto público aprobado → visible
        db.session.add(_person("Niño", "Protegido", involves_minor=True))  # menor → oculto
        db.session.add(_person("Juan", "Pendiente", status=ReportStatus.PENDING))  # no aprobado → oculto
        db.session.add(_person("Eva", "Privada", is_public=False))  # no público → oculto
        db.session.commit()

    people = public_missing_persons()
    assert [(p["first_name"], p["last_name"]) for p in people] == [("Ana", "Pérez")]
    assert people[0]["last_seen"] == "Caracas"
    assert people[0]["age"] == 30


def test_public_missing_persons_search(app):
    with app.app_context():
        db.session.add(_person("Ana", "Pérez", location_text="Maracay"))
        db.session.add(_person("Luis", "Gómez", location_text="Valencia"))
        db.session.commit()

    assert len(public_missing_persons(q="maracay")) == 1
    assert len(public_missing_persons(q="Luis")) == 1
    assert len(public_missing_persons(q="zzz")) == 0
