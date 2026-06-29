import json

from app.extensions import db
from app.ingestion.localizados import parse_localizados
from app.ingestion.pipeline import ingest_persons
from app.models import PersonRecord
from app.services.operational import public_person_records

PAYLOAD = json.loads(json.dumps({
    "meta": {"total": 2, "totalPages": 1},
    "data": [
        {"slug": "juan-perez-x1", "nombreCompleto": "Juan Pérez", "direccion": "Hospital Vargas",
         "observaciones": "Sobreviviente, estable", "condicion": "vivo", "lugarNombre": "Hospital Vargas",
         "fuente": {"nombre": "consolidado.csv"}, "publicadoEn": "2026-06-27"},
        {"slug": "nina-x2", "nombreCompleto": "(niña menor) Martínez Camargo", "direccion": "Refugio Poliedro",
         "observaciones": "", "condicion": "desconocido", "lugarNombre": "Refugio Poliedro",
         "fuente": {}, "publicadoEn": "2026-06-27"},
    ],
}))


def test_parse_localizados_maps_and_flags_minor():
    people = {p.external_id: p for p in parse_localizados(PAYLOAD)}
    juan = people["juan-perez-x1"]
    assert juan.full_name == "Juan Pérez"
    assert juan.person_status == "found"
    assert juan.last_known_location == "Hospital Vargas"
    assert juan.is_minor is False
    assert juan.source_slug == "localizados-venezuela"
    # El registro marcado "(niña menor)" se detecta como menor (a proteger).
    assert people["nina-x2"].is_minor is True


def test_localizados_minor_excluded_from_public(app):
    with app.app_context():
        ingest_persons(parse_localizados(PAYLOAD))
        assert db.session.query(PersonRecord).count() == 2

    found = public_person_records(status="found")
    assert any(p["full_name"] == "Juan Pérez" for p in found)
    assert all("menor" not in p["full_name"].lower() for p in found)  # el menor no aparece
