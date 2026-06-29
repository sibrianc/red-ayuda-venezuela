from app.constants import ReportStatus
from app.extensions import db
from app.models import HelpRequest, ReportStatusHistory
from tests.conftest import login


def create_help_request():
    report = HelpRequest(
        title="Solicitud para revisar",
        request_type="medical",
        people_affected=2,
        medical_need=True,
        location_text="Zona aproximada",
        exact_address_private="Secreto 100",
        description_public="Descripción pública que debe revisarse.",
        description_private="Nota privada",
        reporter_name_private="Nombre privado",
        reporter_contact_private="contacto-privado",
    )
    db.session.add(report)
    db.session.commit()
    return report


def test_admin_requires_authentication(client):
    response = client.get("/admin")
    assert response.status_code == 302
    assert "/cuenta/login" in response.headers["Location"]


def test_csv_export_is_admin_only(client, reviewer):
    # La exportación (datos sensibles) es solo para ADMIN; un REVIEWER recibe 403.
    assert login(client, "reviewer@example.org").status_code == 302
    response = client.get("/admin/exportar/help_request.csv")
    assert response.status_code == 403


def test_admin_can_approve_and_history_is_written(app, client, admin):
    with app.app_context():
        report = create_help_request()
        report_id = report.id
        public_id = report.public_id
    assert login(client).status_code == 302
    review_page = client.get(f"/admin/reportes/help_request/{report_id}")
    assert "Aprobado" in review_page.text
    assert "No verificado" in review_page.text
    response = client.post(
        f"/admin/reportes/help_request/{report_id}",
        data={
            "status": "approved",
            "verification_status": "volunteer",
            "priority": "high",
            "is_public": "y",
            "description_public": "Descripción pública sanitizada para publicación.",
            "reason": "Verificación telefónica completada.",
            "note": "Contacto confirmado internamente.",
        },
    )
    assert response.status_code == 302
    with app.app_context():
        report = db.session.get(HelpRequest, report_id)
        assert report.status is ReportStatus.APPROVED
        assert report.is_public is True
        history = ReportStatusHistory.query.one()
        assert history.old_status is ReportStatus.PENDING
        assert history.new_status is ReportStatus.APPROVED
    public_html = client.get(f"/reportes/help_request/{public_id}").text
    assert "Descripción pública sanitizada" in public_html
    assert "contacto-privado" not in public_html
    assert "Contacto confirmado internamente" not in public_html


def test_nonapproved_status_forces_private(app, client, admin):
    with app.app_context():
        report = create_help_request()
        report_id = report.id
    login(client)
    client.post(
        f"/admin/reportes/help_request/{report_id}",
        data={
            "status": "rejected",
            "verification_status": "unverified",
            "priority": "medium",
            "is_public": "y",
            "description_public": "Descripción pública suficientemente extensa.",
        },
    )
    with app.app_context():
        assert db.session.get(HelpRequest, report_id).is_public is False


def test_export_requires_admin_and_escapes_formula(app, client, reviewer):
    with app.app_context():
        report = create_help_request()
        report.reporter_name_private = "=HYPERLINK(\"bad\")"
        db.session.commit()
    login(client, "reviewer@example.org")
    assert client.get("/admin/exportar/help_request.csv?scope=internal").status_code == 403
    client.post("/cuenta/logout")
    with app.app_context():
        from app.constants import UserRole
        from app.models import User

        user = User(name="Admin2", email="admin2@example.org", role=UserRole.ADMIN)
        user.set_password("correct-horse-battery-staple")
        db.session.add(user)
        db.session.commit()
    login(client, "admin2@example.org")
    response = client.get("/admin/exportar/help_request.csv?scope=internal")
    assert response.status_code == 200
    assert response.headers["X-Data-Classification"] == "sensitive"
    assert "'=HYPERLINK" in response.text
