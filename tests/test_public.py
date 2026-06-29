import pytest

from app.constants import ReportStatus
from app.extensions import db
from app.models import HelpRequest, LocationReport, MissingPersonReport, ResourceOffer


def test_home_loads_with_security_headers(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Panorama humanitario público" in response.text
    assert "data-bandwidth-toggle" in response.text
    assert "js/preferences.js" in response.text
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert "style-src-attr 'unsafe-inline'" in response.headers["Content-Security-Policy"]


def test_home_summary_only_counts_approved_public_reports(app, client):
    with app.app_context():
        approved_need = HelpRequest(
            title="Agua pública",
            request_type="water",
            people_affected=4,
            location_text="Zona segura A",
            description_public="Necesidad pública revisada.",
            description_private="Privado aprobado que nunca debe aparecer",
            reporter_name_private="Nombre reservado",
            reporter_contact_private="contacto-reservado",
            status=ReportStatus.APPROVED,
            is_public=True,
        )
        approved_resource = ResourceOffer(
            title="Recurso público",
            resource_type="water",
            location_text="Zona segura B",
            description_public="Recurso público revisado.",
            reporter_name_private="Nombre reservado",
            reporter_contact_private="contacto-reservado-2",
            status=ReportStatus.APPROVED,
            is_public=True,
        )
        pending = HelpRequest(
            title="Pendiente que no se cuenta",
            request_type="medical",
            people_affected=99,
            location_text="Zona privada",
            description_public="Texto pendiente oculto.",
            description_private="Secreto pendiente",
            reporter_name_private="Nombre pendiente",
            reporter_contact_private="contacto-pendiente",
        )
        db.session.add_all([approved_need, approved_resource, pending])
        db.session.commit()

    html = client.get("/").text
    assert 'data-summary-total>2<' in html
    assert "Agua pública" in html
    assert "Recurso público" in html
    assert "Pendiente que no se cuenta" not in html
    assert "Privado aprobado que nunca debe aparecer" not in html
    assert "contacto-reservado" not in html


def test_map_supports_text_only_low_bandwidth_fallback(client):
    page = client.get("/mapa").text
    script = client.get("/static/js/map.js").text
    assert "data-bandwidth-toggle" in page
    assert "lowBandwidth" in script
    assert "El modo ligero evita descargar teselas" in script


@pytest.mark.parametrize(
    "endpoint",
    ["/reportes/persona", "/reportes/ayuda", "/reportes/recurso", "/reportes/zona"],
)
def test_public_forms_use_guided_flow_and_hide_manual_coordinates(client, endpoint):
    response = client.get(endpoint)
    assert response.status_code == 200
    html = response.text
    assert "data-report-wizard" in html
    assert html.count("data-wizard-panel=") == 3
    assert "data-use-location" in html
    assert 'name="latitude"' in html and 'type="hidden"' in html
    assert 'name="longitude"' in html
    assert "Latitud aproximada (opcional)" not in html
    assert "Longitud aproximada (opcional)" not in html


def test_map_page_is_command_center(client):
    html = client.get("/mapa").text
    # Centro de Operaciones: mapa, panel de capas, radio, GPS y panel de inteligencia.
    assert 'id="cmd-map"' in html
    assert 'id="cmd-layers"' in html
    assert 'id="cmd-radius"' in html
    assert "data-cmd-gps" in html
    assert "CENTRO DE OPERACIONES" in html
    assert "RADIO DE BÚSQUEDA" in html
    assert "INTEL · EN RADIO" in html


@pytest.mark.parametrize(
    ("endpoint", "extra", "model"),
    [
        (
            "/reportes/persona",
            {
                "first_name": "María",
                "last_name": "Pérez",
                "age": "32",
                "last_contact_date": "2026-06-26",
                "involves_minor": "",
            },
            MissingPersonReport,
        ),
        (
            "/reportes/ayuda",
            {
                "title": "Agua para comunidad",
                "request_type": "water",
                "people_affected": "12",
                "water_need": "y",
            },
            HelpRequest,
        ),
        (
            "/reportes/recurso",
            {
                "title": "Agua disponible",
                "resource_type": "water",
                "capacity": "100 litros",
                "availability": "Hoy",
            },
            ResourceOffer,
        ),
        (
            "/reportes/zona",
            {
                "title": "Daños en la zona",
                "damage_level": "high",
                "needs_water": "y",
            },
            LocationReport,
        ),
    ],
)
def test_valid_reports_auto_publish_after_cleaning(app, client, base_report_data, endpoint, extra, model):
    # Operación autónoma: un reporte limpio y completo se publica solo, sin revisión.
    response = client.post(endpoint, data={**base_report_data, **extra})
    assert response.status_code == 302
    with app.app_context():
        report = model.query.one()
        assert report.status is ReportStatus.APPROVED
        assert report.is_public is True
        assert report.public_id


def test_minor_report_is_held_and_never_public(app, client, base_report_data):
    client.post(
        "/reportes/persona",
        data={
            **base_report_data,
            "first_name": "Niño",
            "last_name": "Protegido",
            "age": "8",
            "last_contact_date": "2026-06-26",
            "involves_minor": "y",
        },
    )
    with app.app_context():
        report = MissingPersonReport.query.one()
        assert report.is_public is False
        assert report.status is ReportStatus.NEEDS_VERIFICATION
        public_id = report.public_id
    assert client.get(f"/reportes/missing_person/{public_id}").status_code == 404
    assert client.get("/mapa/data").json == {"reports": []}


def test_manual_review_mode_queues_without_publishing(app, client, base_report_data):
    app.config["AUTO_PUBLISH"] = False
    client.post(
        "/reportes/ayuda",
        data={**base_report_data, "title": "Agua potable", "request_type": "water", "people_affected": "2"},
    )
    with app.app_context():
        report = HelpRequest.query.one()
        assert report.status is ReportStatus.PENDING
        assert report.is_public is False


def test_auto_published_report_still_hides_private_fields(app, client, base_report_data):
    client.post(
        "/reportes/ayuda",
        data={**base_report_data, "title": "Agua potable urgente", "request_type": "water", "people_affected": "5"},
    )
    with app.app_context():
        report = HelpRequest.query.one()
        assert report.is_public is True
        public_id = report.public_id
    html = client.get(f"/reportes/help_request/{public_id}").text
    assert "+58 000 0000000" not in html
    assert "Calle privada 123" not in html
    assert "Detalle interno reservado." not in html


def test_approved_report_exposes_only_public_projection(app, client):
    with app.app_context():
        report = HelpRequest(
            title="Agua aprobada",
            request_type="water",
            people_affected=4,
            location_text="Zona general segura",
            exact_address_private="Dirección secreta 77",
            latitude=10.612345,
            longitude=-66.934567,
            description_public="Descripción pública revisada y segura.",
            description_private="Nota interna muy secreta",
            reporter_name_private="Nombre secreto",
            reporter_contact_private="telefono-secreto-123",
            status=ReportStatus.APPROVED,
            is_public=True,
        )
        db.session.add(report)
        db.session.commit()
        public_id = report.public_id
    html = client.get(f"/reportes/help_request/{public_id}").text
    assert "Agua aprobada" in html
    assert "telefono-secreto-123" not in html
    assert "Dirección secreta 77" not in html
    assert "Nota interna muy secreta" not in html
    payload = client.get("/mapa/data").json["reports"][0]
    serialized = str(payload)
    assert "telefono-secreto-123" not in serialized
    assert "Dirección secreta 77" not in serialized
    assert payload["location"]["latitude"] == 10.61
    assert payload["location"]["longitude"] == -66.93
    assert payload["location"]["precision"] == "approximate"
    assert set(payload) == {
        "public_id",
        "type",
        "title",
        "summary",
        "status",
        "priority",
        "verification",
        "location",
        "updated_at",
        "url",
    }


def test_abuse_can_only_target_public_report(app, client):
    with app.app_context():
        report = HelpRequest(
            title="Pendiente",
            request_type="water",
            people_affected=1,
            location_text="Zona",
            description_public="Descripción suficientemente extensa.",
            reporter_name_private="Privado",
            reporter_contact_private="Privado",
        )
        db.session.add(report)
        db.session.commit()
        public_id = report.public_id
    assert client.get(f"/reportes/help_request/{public_id}/abuso").status_code == 404


def test_coordination_hub_connects_actors(client):
    html = client.get("/coordinacion").text
    assert "Centro de coordinación" in html
    assert "Familias" in html
    assert "Rescatistas" in html
    assert "Prioridades de rescate" in html
    assert "Zonas con más desaparecidos" in html


def test_emergency_contacts_page_lists_verified_channels(client):
    html = client.get("/contactos").text
    assert "Contactos de emergencia" in html
    assert 'href="tel:911"' in html
    assert "0800-7372282" in html
    assert "Cruz Roja" in html
    # entrada para buscar familiares presente
    assert "Buscar a un familiar" in html


def test_home_links_to_family_search_and_emergency(client):
    html = client.get("/").text
    assert "Buscar personas" in html
    assert "/directorio/personas" in html
    assert "Directorio de incidentes y servicios" in html
    assert "/contactos" in html
