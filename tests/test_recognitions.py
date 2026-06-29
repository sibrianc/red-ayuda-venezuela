import json

from app.ingestion.pipeline import ingest_recognitions
from app.ingestion.recognitions import parse_recognitions_json
from app.services.operational import count_recognitions, public_recognitions

_FEED = json.dumps([
    {"id": "u1", "kind": "responder_unit", "name": "USAR España", "org": "España",
     "role": "Búsqueda y rescate urbano", "source_url": "https://example.org/usar"},
    {"id": "d1", "kind": "perro", "name": "Ayudín", "org": "Bomberos de Caracas",
     "photo_url": "https://example.org/dog.jpg", "source_url": "https://example.org/dog"},
])


def test_recognition_ingest_splits_units_and_dogs(app, client):
    with app.app_context():
        recs = parse_recognitions_json(_FEED, source_slug="oficial", attribution="Protección Civil")
        assert len(recs) == 2
        stats = ingest_recognitions(recs)
        assert stats.new == 2
        assert count_recognitions("responder_unit") == 1
        assert count_recognitions("rescue_dog") == 1
        # idempotente por origen
        again = ingest_recognitions(parse_recognitions_json(_FEED, source_slug="oficial", attribution="Protección Civil"))
        assert again.unchanged == 2
        assert public_recognitions("rescue_dog")[0]["name"] == "Ayudín"

    html = client.get("/reconocimientos").text
    assert "USAR España" in html
    assert "Ayudín" in html
    assert "Unidades y organizaciones" in html
    assert "Perro rescatista" in html


def test_recognition_parser_validates_photo_and_maps_kind():
    recs = parse_recognitions_json(
        json.dumps([{"name": "K9 Unit", "kind": "dog", "photo_url": "http://inseguro/a.exe"}]),
        source_slug="s",
    )
    assert recs[0].kind == "rescue_dog"
    assert recs[0].photo_url is None


def test_recognitions_linked_in_footer(client):
    assert "/reconocimientos" in client.get("/").text


def test_recognition_country_maps_to_flag(app, client):
    feed = json.dumps([{"id": "x", "kind": "responder_unit", "name": "UME", "country": "ES"}])
    with app.app_context():
        recs = parse_recognitions_json(feed, source_slug="o")
        assert recs[0].country == "es"  # normalizado a ISO alpha-2 minúsculas
        ingest_recognitions(recs)
    assert "flags/es.svg" in client.get("/reconocimientos").text
