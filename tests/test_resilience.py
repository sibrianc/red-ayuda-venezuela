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


def test_forms_work_without_loading_map(client):
    response = client.get("/reportes/ayuda")
    assert response.status_code == 200
    assert "leaflet" not in response.text.lower()


def test_map_uses_policy_compliant_osm_tile_url(client):
    response = client.get("/mapa")
    assert 'data-tile-url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"' in response.text
