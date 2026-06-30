from pathlib import Path


def test_offline_drafts_exclude_sensitive_fields():
    script = Path("app/static/js/offline_forms.js").read_text()
    for field in (
        "exact_address_private",
        "description_private",
        "reporter_contact_private",
        "medical_information_private",
    ):
        assert field in script
    assert "24 * 60 * 60 * 1000" in script


def test_public_pages_work_without_loading_map(client):
    # Las páginas públicas (agregador) no dependen del JS del mapa (Leaflet).
    response = client.get("/directorio")
    assert response.status_code == 200
    assert "leaflet" not in response.text.lower()


def test_map_uses_policy_compliant_osm_tile_url(client):
    response = client.get("/mapa")
    assert 'data-tile-url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"' in response.text


def test_csp_allows_https_images_for_map_and_photos(client):
    # Los íconos de Leaflet (unpkg), las teselas del mapa y las fotos (mascotas/
    # reconocimientos) son imágenes https. El CSP debe permitir imágenes https inertes;
    # nunca http ni scripts. Sin esto, pines del mapa y fotos se ven rotos.
    csp = client.get("/mapa").headers["Content-Security-Policy"]
    img_src = csp.split("img-src", 1)[1].split(";", 1)[0]
    assert "https:" in img_src
    assert "object-src 'none'" in csp  # sin plugins/objetos


def test_login_is_rate_limited(client):
    # Anti-fuerza bruta: el login admite 10/min por IP; el intento 11 recibe 429.
    statuses = [
        client.post("/cuenta/login", data={"email": "x@example.org", "password": "bad"}).status_code
        for _ in range(12)
    ]
    assert 429 in statuses
    assert statuses[-1] == 429
