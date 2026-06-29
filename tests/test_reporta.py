from app.extensions import db
from app.ingestion.pipeline import ingest_persons
from app.ingestion.venezuelareporta import parse_reporta
from app.models import PersonRecord
from app.services.operational import public_person_records

HTML = """
<div class="grid">
<a class="card" href="/reporte/af9fa7fd-619b-49eb-b6d7-9d1c10fd6227">
  <img alt="Foto de Carlos Castillo"/>
  <span class="chip bg-buscando-soft"><span></span>Se busca</span>
  <h3>Carlos Castillo</h3><p>La Guaira</p></a>
<a class="card" href="/reporte/2ba4ef6f-aaaa-bbbb-cccc-111122223333">
  <img alt="Foto de Ana Perez"/>
  <span class="chip bg-salvo-soft"><span></span>A salvo</span>
  <h3>Ana Perez</h3><p>Reportado aquí</p></a>
<a class="card" href="/reporte/33334444-aaaa-bbbb-cccc-555566667777">
  <img alt="Foto de (niño menor) Gómez"/>
  <span class="chip bg-buscando-soft"><span></span>Se busca</span>
  <h3>(niño menor) Gómez</h3><p>Petare</p></a>
</div>
"""


def test_parse_reporta_cards():
    people = {p.external_id: p for p in parse_reporta(HTML)}
    assert len(people) == 3
    carlos = people["af9fa7fd-619b-49eb-b6d7-9d1c10fd6227"]
    assert carlos.full_name == "Carlos Castillo"
    assert carlos.person_status == "missing"
    assert carlos.last_known_location == "La Guaira"
    assert carlos.is_minor is False
    assert carlos.source_url.endswith("/reporte/af9fa7fd-619b-49eb-b6d7-9d1c10fd6227")
    ana = people["2ba4ef6f-aaaa-bbbb-cccc-111122223333"]
    assert ana.person_status == "found"
    assert ana.last_known_location is None  # "Reportado aquí" genérico se descarta
    assert people["33334444-aaaa-bbbb-cccc-555566667777"].is_minor is True


def test_reporta_minor_excluded_from_public(app):
    with app.app_context():
        ingest_persons(parse_reporta(HTML))
        assert db.session.query(PersonRecord).count() == 3

    missing = public_person_records(status="missing")
    assert any(p["full_name"] == "Carlos Castillo" for p in missing)
    assert all("menor" not in p["full_name"].lower() for p in missing)
