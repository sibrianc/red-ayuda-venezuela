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
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "style-src-attr 'unsafe-inline'" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "form-action 'self'" in csp
    # los scripts nunca permiten 'unsafe-inline' (anti-XSS)
    script_src = csp.split("script-src", 1)[1].split(";", 1)[0]
    assert "unsafe-inline" not in script_src


def test_favicon_served_at_root(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("image/")
    assert "max-age" in response.headers.get("Cache-Control", "")


def test_home_links_favicon_and_manifest(client):
    html = client.get("/").text
    assert 'rel="icon"' in html
    assert "icons/favicon.svg" in html
    assert "site.webmanifest" in html


def test_robots_txt(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/plain")
    body = response.text
    assert "User-agent: *" in body
    assert "Disallow: /admin/" in body
    assert "Disallow: /cuenta/" in body
    assert "Sitemap: http" in body


def test_sitemap_xml(client):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/xml")
    body = response.text
    assert "<urlset" in body and "</urlset>" in body
    assert "/directorio" in body
    # No expone superficies privadas ni de detalle sensible.
    assert "/admin" not in body
    assert "/cuenta" not in body
    assert "/reportes/confirmacion" not in body


def test_security_txt(client):
    response = client.get("/.well-known/security.txt")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/plain")
    body = response.text
    assert "Contact:" in body
    assert "Expires:" in body


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


def test_minor_report_is_held_and_never_public(app):
    # El reporte público de personas se delega al registro canónico, pero la protección de
    # menores del pipeline se mantiene: un MissingPersonReport con menor nunca se publica.
    from app.constants import ReportType
    from app.services.intake import evaluate_intake

    with app.app_context():
        report = MissingPersonReport(
            first_name="Niño", last_name="Protegido", age=8, involves_minor=True,
            location_text="Caracas", description_public="Descripción suficiente del caso.",
            reporter_name_private="Reportante", reporter_contact_private="+58 000",
        )
        decision = evaluate_intake(ReportType.MISSING_PERSON, report)
        assert decision.is_public is False
        assert decision.status is ReportStatus.NEEDS_VERIFICATION


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
    # El sitio se centra en mapa/servicios/coordinación; personas → registro oficial (externo).
    assert "Ir al registro oficial" in html          # CTA al registro ciudadano
    assert "/directorio/personas" in html             # vista agregada de personas
    assert "Directorio de incidentes y servicios" in html
    assert "/contactos" in html
