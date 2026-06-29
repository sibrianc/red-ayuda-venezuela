import json

from app.extensions import db
from app.ingestion.pfif import parse_persons_json
from app.ingestion.pipeline import ingest_persons
from app.models import PersonRecord
from app.services.operational import public_person_records

SAMPLE = json.dumps({
    "personas": [
        {"nombre": "Ana", "apellido": "Pérez", "edad": "34", "ubicacion": "Caracas",
         "estado": "desaparecido", "id": "a1", "fuente": "Venezuela Te Busca"},
        {"full_name": "Juan Gómez", "edad": 40, "last_known_location": "La Guaira",
         "status": "fallecido", "id": "d1"},
        {"nombre": "Niño", "apellido": "Protegido", "edad": "10", "ubicacion": "Petare",
         "estado": "desaparecido", "id": "m1"},
    ]
})


def test_parse_persons_json_maps_spanish_fields_and_status():
    people = {p.external_id: p for p in parse_persons_json(SAMPLE, source_slug="vtb", attribution="VTB")}
    assert people["a1"].full_name == "Ana Pérez"
    assert people["a1"].age == 34
    assert people["a1"].last_known_location == "Caracas"
    assert people["a1"].person_status == "missing"
    assert people["d1"].full_name == "Juan Gómez"
    assert people["d1"].person_status == "deceased"
    assert people["m1"].is_minor is True


def test_ingest_persons_json_excludes_minors_in_public(app):
    with app.app_context():
        stats = ingest_persons(parse_persons_json(SAMPLE, source_slug="vtb", attribution="VTB"))
        assert stats.new == 3
        assert db.session.query(PersonRecord).count() == 3

    missing = public_person_records(status="missing")
    assert any(p["full_name"] == "Ana Pérez" for p in missing)
    assert all("Niño" not in p["full_name"] for p in missing)  # el menor no aparece en público

    deceased = public_person_records(status="deceased")
    assert any(p["full_name"] == "Juan Gómez" for p in deceased)
