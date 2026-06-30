from pathlib import Path

from app.constants import ReportStatus
from app.extensions import db
from app.ingestion.pfif import parse_pfif
from app.ingestion.pipeline import ingest_persons
from app.models import DirectoryEntry, Incident, MissingPersonReport
from app.services.operational import (
    public_directory,
    public_incidents,
    public_missing_persons,
)


def _person(first, last, **overrides):
    values = {
        "first_name": first, "last_name": last, "age": 30, "involves_minor": False,
        "status": ReportStatus.APPROVED, "is_public": True,
        "location_text": "Caracas", "description_public": "Visto por última vez en la zona.",
        "reporter_name_private": "Reportante", "reporter_contact_private": "+58 000",
    }
    values.update(overrides)
    return MissingPersonReport(**values)


def test_directory_hub_lists_sections(client):
    response = client.get("/directorio")
    assert response.status_code == 200
    html = response.text
    assert "Directorio del terremoto" in html
    assert "Edificios e incidentes" in html
    assert "Registros oficiales" in html
    # el hub enlaza a cada subpágina por su propia ruta
    assert "/directorio/personas" in html
    assert "/directorio/incidentes" in html
    assert "/directorio/servicios" in html
    assert "/directorio/zonas" in html


def test_directory_subpages_render(client):
    people = client.get("/directorio/personas")
    assert people.status_code == 200
    assert "Reportar un familiar" in people.text
    assert "Registros oficiales" in people.text
    # Fallecidas: no hay lista navegable, sí una nota digna en la página de personas.
    assert "Personas fallecidas" in people.text
    assert "Incidentes y evaluación estructural" in client.get("/directorio/incidentes").text
    assert client.get("/directorio/servicios").status_code == 200
    assert client.get("/directorio/zonas").status_code == 200


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


def _incident(label, address, **overrides):
    values = {
        "source_slug": "test", "external_id": label, "content_hash": "h",
        "category": "collapsed_structure", "severity": "high", "label": label,
        "address_public": address, "latitude": 10.5, "longitude": -66.9, "in_region": True,
        "verification_status": "corroborated", "people_trapped_status": "unknown",
    }
    values.update(overrides)
    return Incident(**values)


def test_public_incidents_search(app):
    with app.app_context():
        db.session.add(_incident("Edificio Catia 7", "Av. Sucre, Catia"))
        db.session.add(_incident("Residencias Altamira", "Av. Luis Roche"))
        db.session.commit()

    assert len(public_incidents(q="catia")) == 1
    assert len(public_incidents(q="Av.")) == 2  # ambos por dirección
    assert len(public_incidents(q="zzz")) == 0


def test_public_incidents_hide_samples_and_unverified_trapped_claims(app):
    with app.app_context():
        db.session.add(_incident("Muestra peligrosa", "Caracas", source_slug="sample"))
        db.session.add(_incident(
            "Atrapamiento sin verificar",
            "Caracas",
            category="trapped_persons",
            verification_status="unverified",
            people_trapped_status="reported",
        ))
        db.session.add(_incident(
            "Atrapamiento confirmado",
            "La Guaira",
            category="trapped_persons",
            verification_status="verified",
            people_trapped_status="confirmed",
            people_trapped_count=2,
        ))
        db.session.commit()

    incidents = public_incidents()
    assert [incident["label"] for incident in incidents] == ["Atrapamiento confirmado"]
    assert incidents[0]["people_trapped_count"] == 2


def test_public_incidents_can_list_unlocated_but_map_requires_coordinates(app):
    with app.app_context():
        db.session.add(_incident(
            "Edificio publicado",
            "La Guaira · ubicación pendiente",
            latitude=None,
            longitude=None,
        ))
        db.session.commit()

    assert len(public_incidents()) == 1
    assert public_incidents(require_coordinates=True) == []


def test_public_directory_search(app):
    with app.app_context():
        db.session.add(DirectoryEntry(
            source_slug="test", external_id="h1", content_hash="h", category="hospital",
            name="Hospital Vargas", address_public="La Guaira", latitude=10.6, longitude=-66.9,
            in_region=True,
        ))
        db.session.commit()

    assert len(public_directory(q="vargas")) == 1
    assert len(public_directory(q="guaira")) == 1
    assert len(public_directory(q="zzz")) == 0


def test_directory_combines_reviewed_and_pfif_people_and_excludes_minors(app, client):
    fixture = (
        Path(__file__).parent / "fixtures" / "pfif_people_1_4.xml"
    ).read_text(encoding="utf-8")
    with app.app_context():
        db.session.add(_person("Ana", "Pérez", location_text="Maracay"))
        ingest_persons(
            parse_pfif(
                fixture,
                source_slug="official-test",
                attribution="Fuente oficial de prueba",
            )
        )

    # Desaparecidas: comunidad (Ana) + PFIF "information_sought" (Elena)
    missing = client.get("/directorio/personas").text
    assert "Ana Pérez" in missing
    assert "Elena Salazar" in missing
    assert "Persona Menor Protegida" not in missing
    # Fallecidas: NO se publica una lista de nombres (decisión de dignidad). 'deceased'
    # ya no es un estado navegable: redirige a desaparecidas y Rafael no aparece listado.
    redirected = client.get("/directorio/personas?estado=deceased").text
    assert "Rafael Mendoza" not in redirected
    # En su lugar, una nota digna que remite a fuentes oficiales.
    assert "Personas fallecidas" in redirected
    assert "no publicamos una lista de nombres" in redirected


def test_directory_has_live_search_hooks(client):
    # Búsqueda en vivo: contenedor de resultados con id estable + script cargado.
    html = client.get("/directorio/personas").text
    assert 'id="dir-results"' in html
    assert "directory_search.js" in html
    # El filtro por servidor (que usa el JS) responde con el contenedor de resultados.
    assert 'id="dir-results"' in client.get("/directorio/servicios?q=hospital").text
