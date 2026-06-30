from app.services.operational import maps_url


def test_maps_url_pins_exact_point_with_readable_label():
    # Con nombre: pin en el PUNTO EXACTO, rotulado con el nombre (no un código Plus suelto).
    url = maps_url(10.485085, -66.739667, label="CDI William Lara")
    assert url == "https://www.google.com/maps?q=10.485085,-66.739667(CDI%20William%20Lara)"


def test_maps_url_without_label_uses_coordinates():
    url = maps_url(10.485085, -66.739667)
    assert "query=10.485085,-66.739667" in url


def test_maps_url_without_coordinates_searches_text():
    url = maps_url(text="Caracas")
    assert url is not None and "Caracas" in url


def test_maps_url_none_when_no_data():
    assert maps_url() is None
