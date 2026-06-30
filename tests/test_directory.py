from app.extensions import db
from app.ingestion import connectors
from app.ingestion.connectors import build_overpass_query, fetch_overpass, parse_overpass
from app.ingestion.pipeline import directory_overview, ingest_directory
from app.models import DirectoryEntry


def test_fetch_overpass_falls_back_to_next_mirror(monkeypatch):
    # Si un mirror de Overpass falla/encola, debe intentar el siguiente y usar el que
    # responda (evita cuelgues desde IPs de nube como Render).
    calls = []

    class FakeResp:
        def read(self):
            return b'{"elements": []}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(request, timeout=None, context=None):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise OSError("primer mirror caído")
        return FakeResp()

    monkeypatch.setattr(connectors.urllib.request, "urlopen", fake_urlopen)
    result = fetch_overpass(query="[out:json];")
    assert result == {"elements": []}
    assert len(calls) == 2  # falló el primero, usó el segundo


def overpass_payload():
    return {
        "version": 0.6,
        "generator": "Overpass",
        "elements": [
            {"type": "node", "id": 1, "lat": 10.5, "lon": -66.9,
             "tags": {"amenity": "hospital", "name": "Hospital Central",
                      "addr:street": "Av Urdaneta", "addr:housenumber": "10",
                      "addr:city": "Caracas", "phone": "+58 212 0000000",
                      "operator": "MPPS", "emergency": "yes"}},
            {"type": "way", "id": 2, "center": {"lat": 10.2, "lon": -67.0},
             "tags": {"amenity": "clinic", "name": "Clínica Norte"}},
            {"type": "node", "id": 3, "lat": 9.0, "lon": -67.5,
             "tags": {"amenity": "drinking_water"}},  # sin nombre → etiqueta por categoría
            {"type": "node", "id": 4, "tags": {"amenity": "hospital", "name": "Sin coords"}},  # descartar
            {"type": "node", "lat": 10.0, "lon": -66.0,
             "tags": {"amenity": "pharmacy", "name": "Sin id"}},  # sin id → descartar
            {"type": "node", "id": 6, "lat": 40.4, "lon": -3.7,
             "tags": {"amenity": "hospital", "name": "Hospital Madrid"}},  # fuera de región
        ],
    }


# --- Parseo puro -----------------------------------------------------------


def test_parse_overpass_maps_fields_and_skips_invalid():
    entries = {e.external_id: e for e in parse_overpass(overpass_payload())}
    assert set(entries) == {"node/1", "way/2", "node/3", "node/6"}  # descarta sin coords y sin id

    hospital = entries["node/1"]
    assert hospital.category == "hospital"
    assert hospital.emergency is True
    assert hospital.address_public == "Av Urdaneta 10, Caracas"
    assert hospital.phone_public == "+58 212 0000000"
    assert hospital.operator == "MPPS"
    assert hospital.source_url == "https://www.openstreetmap.org/node/1"

    clinic = entries["way/2"]
    assert clinic.category == "clinic"
    assert clinic.latitude == 10.2 and clinic.longitude == -67.0  # usa center de la vía

    water = entries["node/3"]
    assert water.category == "water_point"
    assert water.name == "Punto de agua"  # etiqueta por defecto al no tener nombre
    assert water.emergency is False


def test_parse_overpass_sanitizes_long_phone_and_caps_fields():
    # OSM trae texto libre: el teléfono puede venir como lista ';' (varios números) y
    # el operador muy largo. Debe saquedar el primer número y acotar a los límites de
    # columna (phone ≤120, operator ≤200) para no romper el INSERT en Postgres.
    long_phone = "; ".join(f"+58 286-71322{n:02d}" for n in range(20))
    payload = {"elements": [{
        "type": "node", "id": 99, "lat": 10.5, "lon": -66.9,
        "tags": {"amenity": "clinic", "name": "Clínica X",
                 "phone": long_phone, "operator": "O" * 400},
    }]}
    entry = parse_overpass(payload)[0]
    assert entry.phone_public == "+58 286-7132200"  # primer número de la lista
    assert len(entry.phone_public) <= 120
    assert len(entry.operator) <= 200


def test_ingest_directory_handles_long_osm_phone(app):
    long_phone = "; ".join(f"+58 286-71322{n:02d}" for n in range(20))
    payload = {"elements": [{
        "type": "node", "id": 99, "lat": 10.5, "lon": -66.9,
        "tags": {"amenity": "clinic", "name": "Clínica X", "phone": long_phone},
    }]}
    with app.app_context():
        stats = ingest_directory(parse_overpass(payload))
        assert stats.new == 1
        assert DirectoryEntry.query.one().phone_public == "+58 286-7132200"


def test_public_directory_near_epicenter_orders_by_proximity(app):
    # El feed del mapa debe priorizar servicios cercanos a La Guaira; si no, con miles de
    # servicios en todo el país el radio del epicentro sale casi vacío.
    from app.services.operational import public_directory
    with app.app_context():
        db.session.add(DirectoryEntry(
            source_slug="s", external_id="far", content_hash="a", category="hospital",
            name="Lejos (Maracaibo)", latitude=10.65, longitude=-71.6, in_region=True))
        db.session.add(DirectoryEntry(
            source_slug="s", external_id="near", content_hash="b", category="hospital",
            name="Cerca (La Guaira)", latitude=10.60, longitude=-66.93, in_region=True))
        db.session.commit()
        rows = public_directory(category="hospital", near_epicenter=True)
        assert rows[0]["name"] == "Cerca (La Guaira)"  # el más cercano primero


def test_build_overpass_query_targets_venezuela():
    query = build_overpass_query()
    assert "hospital" in query and "shelter" in query and "out center tags" in query
    assert "-74.5" in query and "13.0" in query  # recuadro de Venezuela


# --- Ingesta (requiere app + base) -----------------------------------------


def test_ingest_directory_persists_and_flags_region(app):
    stats = ingest_directory(parse_overpass(overpass_payload()))
    assert stats.new == 4
    assert db.session.query(DirectoryEntry).count() == 4
    assert db.session.query(DirectoryEntry).filter_by(in_region=True).count() == 3  # Madrid fuera


def test_ingest_directory_region_only(app):
    stats = ingest_directory(parse_overpass(overpass_payload()), region_only=True)
    assert stats.new == 3
    assert stats.filtered_out == 1  # descarta Madrid
    assert db.session.query(DirectoryEntry).filter_by(name="Hospital Madrid").count() == 0


def test_ingest_directory_is_idempotent(app):
    ingest_directory(parse_overpass(overpass_payload()))
    second = ingest_directory(parse_overpass(overpass_payload()))
    assert second.new == 0
    assert second.unchanged == 4
    assert db.session.query(DirectoryEntry).count() == 4  # sin duplicados


def test_directory_overview_by_category(app):
    ingest_directory(parse_overpass(overpass_payload()))
    overview = directory_overview()
    assert overview["total"] == 4
    assert overview["por_categoria"]["hospital"] == 2
    assert overview["por_categoria"]["clinic"] == 1
    assert overview["por_categoria"]["water_point"] == 1
