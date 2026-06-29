from app.extensions import db
from app.ingestion.normalize import match_key, normalize_name
from app.ingestion.pfif import ParsedPerson
from app.ingestion.pipeline import ingest_persons, recompute_corroboration
from app.models import PersonRecord


def test_normalize_name_strips_accents_case_punct():
    assert normalize_name("José Pérez-Gómez") == "jose perez gomez"
    assert normalize_name("  María   José  ") == "maria jose"


def test_match_key_order_accent_insensitive_and_drops_initials():
    assert match_key("Juan Pérez") == match_key("PEREZ juan")
    assert match_key("(niña menor) Ana López") == match_key("ana lopez")
    assert match_key("Juan A Pérez") == match_key("Juan Pérez")  # descarta inicial suelta


def _person(slug, eid, name, minor=False):
    return ParsedPerson(
        source_slug=slug, external_id=eid, content_hash=eid, full_name=name,
        given_name=None, family_name=None, age=None, sex=None, last_known_location=None,
        home_location=None, person_status="missing", description=None, source_name=slug,
        source_url=None, source_date=None, is_minor=minor, attribution=slug,
    )


def test_corroboration_counts_distinct_sources(app):
    with app.app_context():
        ingest_persons([
            _person("fuente-a", "1", "Juan Pérez"),
            _person("fuente-b", "2", "PÉREZ Juan"),   # misma persona, otra fuente y orden
            _person("fuente-a", "3", "Ana Solo"),
        ])
        corroborated = recompute_corroboration()
        assert corroborated == 1  # solo "juan perez" tiene 2 fuentes
        assert PersonRecord.query.filter_by(external_id="1").one().corroboration == 2
        assert PersonRecord.query.filter_by(external_id="3").one().corroboration == 1
