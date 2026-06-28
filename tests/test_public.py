import pytest

from app.constants import ReportStatus
from app.extensions import db
from app.models import HelpRequest, LocationReport, MissingPersonReport, ResourceOffer


def test_home_loads_with_security_headers(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Conectamos reportes" in response.text
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


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


def test_map_page_has_operational_filters_and_density_view(client):
    html = client.get("/mapa").text
    assert 'data-map-filter="help_request"' in html
    assert 'data-map-filter="resource_offer"' in html
    assert 'data-map-mode="density"' in html
    assert "Concentración" in html


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
def test_public_forms_create_pending_private_reports(app, client, base_report_data, endpoint, extra, model):
    response = client.post(endpoint, data={**base_report_data, **extra})
    assert response.status_code == 302
    with app.app_context():
        report = model.query.one()
        assert report.status is ReportStatus.PENDING
        assert report.is_public is False
        assert report.public_id


def test_pending_report_is_never_public(app, client, base_report_data):
    client.post(
        "/reportes/ayuda",
        data={
            **base_report_data,
            "title": "Necesidad pendiente secreta",
            "request_type": "water",
            "people_affected": "2",
        },
    )
    with app.app_context():
        report = HelpRequest.query.one()
        public_id = report.public_id
    assert "Necesidad pendiente secreta" not in client.get("/reportes").text
    assert client.get(f"/reportes/help_request/{public_id}").status_code == 404
    assert client.get("/mapa/data").json == {"reports": []}


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
