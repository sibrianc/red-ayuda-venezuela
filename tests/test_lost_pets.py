from app.constants import ReportStatus
from app.extensions import db
from app.models import LostPetReport
from app.services.operational import public_lost_pets


def _pet_data(base_report_data, **overrides):
    data = dict(base_report_data)
    data.update(
        {
            "title": "Max",
            "species": "dog",
            "breed": "Mestizo",
            "color": "Marrón con collar rojo",
            "last_seen_date": "2026-06-27",
            "photo_url": "https://example.com/max.jpg",
        }
    )
    data.update(overrides)
    return data


def test_lost_pet_form_renders(client):
    response = client.get("/reportes/mascota")
    assert response.status_code == 200
    assert 'name="species"' in response.text
    assert 'name="photo_url"' in response.text


def test_valid_lost_pet_auto_publishes_and_hides_owner_contact(client, app):
    response = client.post("/reportes/mascota", data=_pet_data({
        "location_text": "Caraballeda, La Guaira",
        "exact_address_private": "Calle privada 123",
        "description_public": "Perro mediano muy asustadizo, responde a su nombre.",
        "description_private": "Detalle interno reservado.",
        "reporter_name_private": "Dueño",
        "reporter_contact_private": "+58 000 0000000",
        "privacy_consent": "y",
        "website": "",
    }), follow_redirects=False)
    assert response.status_code == 302  # publicado → confirmación

    with app.app_context():
        pet = LostPetReport.query.one()
        assert pet.status is ReportStatus.APPROVED
        assert pet.is_public is True

    page = client.get("/directorio/mascotas").text
    assert "Max" in page
    assert "Caraballeda" in page
    # el contacto privado del dueño nunca aparece en público
    assert "+58 000 0000000" not in page
    assert "Calle privada 123" not in page


def test_lost_pet_photo_url_must_be_https_image(client, app):
    response = client.post(
        "/reportes/mascota",
        data=_pet_data({"photo_url": "http://example.com/no-segura.exe"}),
        follow_redirects=False,
    )
    assert response.status_code == 200  # re-renderiza el formulario con error
    with app.app_context():
        assert LostPetReport.query.count() == 0


def test_directory_hub_and_pet_page_expose_pets(client):
    hub = client.get("/directorio").text
    assert "Mascotas desaparecidas" in hub
    assert "/directorio/mascotas" in hub
    assert "Reportar mascota" in client.get("/directorio/mascotas").text


def test_public_lost_pets_excludes_non_public(app):
    with app.app_context():
        db.session.add(LostPetReport(
            title="Publicada", species="cat", location_text="Macuto",
            description_public="Gata gris con placa.",
            reporter_name_private="Dueño", reporter_contact_private="x",
            status=ReportStatus.APPROVED, is_public=True,
        ))
        db.session.add(LostPetReport(
            title="Oculta", species="dog", location_text="Macuto",
            description_public="Aún en revisión.",
            reporter_name_private="Dueño", reporter_contact_private="x",
            status=ReportStatus.NEEDS_VERIFICATION, is_public=False,
        ))
        db.session.commit()

        pets = public_lost_pets()
        assert [p["title"] for p in pets] == ["Publicada"]
        assert pets[0]["species_label"] == "Gato"
