def test_default_locale_is_spanish(client):
    html = client.get("/").text
    assert "Ayuda coordinada para Venezuela" in html
    assert "Directorio" in html  # nav en español
    assert 'lang="es"' in html


def test_english_toggle_translates_nav_and_home(client):
    html = client.get("/?lang=en").text
    assert 'lang="en"' in html
    # navegación traducida
    assert ">Map<" in html
    assert ">Directory<" in html
    # home traducida
    assert "Coordinated help for Venezuela" in html
    assert "What do you want to report?" in html
    # el botón de idioma está presente
    assert "lang-toggle" in html


def test_language_choice_persists_via_cookie(client):
    client.get("/?lang=en")  # fija la cookie
    # sin ?lang, debe recordar inglés por la cookie
    html = client.get("/").text
    assert "Coordinated help for Venezuela" in html


def test_unknown_lang_falls_back_to_spanish(client):
    html = client.get("/?lang=zz").text
    assert 'lang="es"' in html
    assert "Ayuda coordinada para Venezuela" in html
