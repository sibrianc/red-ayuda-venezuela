from dataclasses import replace
from pathlib import Path

from app.extensions import db
from app.ingestion.pfif import parse_pfif
from app.ingestion.pipeline import ingest_persons
from app.models import PersonRecord
from app.services.operational import public_person_records


FIXTURE = Path(__file__).parent / "fixtures" / "pfif_people_1_4.xml"


def parsed_people():
    return parse_pfif(
        FIXTURE.read_text(encoding="utf-8"),
        source_slug="official-test",
        attribution="Fuente oficial de prueba",
    )


def test_pfif_14_parser_maps_names_statuses_dates_and_minors():
    people = {person.external_id: person for person in parsed_people()}

    missing = people["adult-missing-1"]
    assert missing.full_name == "Elena Salazar"
    assert missing.person_status == "missing"
    assert missing.home_location == "Caracas, Venezuela"
    assert missing.source_date.isoformat() == "2026-06-27T16:30:00+00:00"

    deceased = people["adult-deceased-1"]
    assert deceased.full_name == "Rafael Mendoza"
    assert deceased.age == 61
    assert deceased.person_status == "deceased"

    minor = people["minor-1"]
    assert minor.full_name == "Persona Menor Protegida"
    assert minor.is_minor is True


def test_pfif_ingest_is_idempotent_and_scoped_by_source(app):
    people = parsed_people()
    first = ingest_persons(people)
    second = ingest_persons(parsed_people())

    assert first.new == 3
    assert second.new == 0
    assert second.unchanged == 3
    assert db.session.query(PersonRecord).count() == 3

    another_source = [replace(people[0], source_slug="another-official-source")]
    third = ingest_persons(another_source)
    assert third.new == 1
    assert db.session.query(PersonRecord).count() == 4


def test_pfif_note_change_updates_status_and_content_hash(app):
    original = parsed_people()[0]
    ingest_persons([original])
    changed_xml = FIXTURE.read_text(encoding="utf-8").replace(
        "information_sought", "believed_dead", 1
    )
    changed = parse_pfif(changed_xml, source_slug="official-test")[0]

    stats = ingest_persons([changed])
    stored = db.session.query(PersonRecord).filter_by(external_id=original.external_id).one()
    assert stats.updated == 1
    assert stored.person_status == "deceased"
    assert stored.content_hash != original.content_hash


def test_public_person_projection_filters_status_search_and_minors(app):
    ingest_persons(parsed_people())

    missing = public_person_records(status="missing")
    deceased = public_person_records(status="deceased")
    assert [person["full_name"] for person in missing] == ["Elena Salazar"]
    assert [person["full_name"] for person in deceased] == ["Rafael Mendoza"]
    assert public_person_records(status="missing", q="Macuto")[0]["full_name"] == "Elena Salazar"
    assert public_person_records(q="Menor") == []


def test_public_person_projection_rejects_unsafe_source_url(app):
    person = replace(parsed_people()[0], source_url="javascript:alert(1)")
    ingest_persons([person])
    assert public_person_records(status="missing")[0]["source_url"] is None
