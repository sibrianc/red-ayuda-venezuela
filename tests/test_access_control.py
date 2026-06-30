from app.extensions import db
from tests.conftest import login


def test_2fa_enrollment_page_renders_qr(client, app):
    with app.app_context():
        from app.constants import UserRole
        from app.models import User

        u = User(name="Nuevo", email="nuevo@example.org", role=UserRole.ADMIN)
        u.set_password("correct-horse-battery-staple")
        db.session.add(u)
        db.session.commit()
    client.post(
        "/cuenta/login",
        data={"email": "nuevo@example.org", "password": "correct-horse-battery-staple"},
    )
    page = client.get("/cuenta/2fa")
    assert page.status_code == 200
    assert "<svg" in page.text  # código QR de inscripción


def test_admin_requires_second_factor(client, admin):
    # Solo contraseña (sin 2FA) no basta: /admin redirige al segundo factor.
    client.post(
        "/cuenta/login",
        data={"email": "admin@example.org", "password": "correct-horse-battery-staple"},
    )
    resp = client.get("/admin")
    assert resp.status_code == 302
    assert "/cuenta/2fa" in resp.headers["Location"]


def test_full_login_with_2fa_reaches_admin(client, admin):
    assert login(client).status_code == 302  # password + 2FA
    assert client.get("/admin").status_code == 200


def test_admin_invites_and_collaborator_activates(client, app, admin):
    login(client)
    resp = client.post(
        "/admin/usuarios",
        data={"name": "Colaborador", "email": "colab@example.org", "role": "reviewer"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        from app.models import User

        u = User.query.filter_by(email="colab@example.org").first()
        assert u is not None and u.invite_token and u.password_hash is None
        token = u.invite_token

    client.post("/cuenta/logout")
    assert client.get(f"/cuenta/invitacion/{token}").status_code == 200
    done = client.post(
        f"/cuenta/invitacion/{token}",
        data={"password": "clave-muy-larga-123", "confirm": "clave-muy-larga-123"},
        follow_redirects=False,
    )
    assert done.status_code == 302  # activada → pasa a configurar 2FA
    with app.app_context():
        from app.models import User

        u = User.query.filter_by(email="colab@example.org").first()
        assert u.password_hash is not None and u.invite_token is None


def test_invalid_invite_token_is_rejected(client):
    resp = client.get("/cuenta/invitacion/no-existe", follow_redirects=False)
    assert resp.status_code == 302
    assert "/cuenta/login" in resp.headers["Location"]


def test_audit_log_records_sensitive_actions(client, app, admin):
    login(client)
    client.get("/admin/exportar/help_request.csv")
    with app.app_context():
        from app.models import AuditLog

        actions = {a.action for a in AuditLog.query.all()}
        assert "login_password" in actions
        assert "2fa_verified" in actions
        assert "export_csv" in actions


def test_operations_requires_login(client):
    assert client.get("/admin/operacion").status_code == 302


def test_operations_4w_lists_needs_and_gaps(client, app, admin):
    with app.app_context():
        from app.constants import ReportStatus
        from app.models import HelpRequest

        db.session.add(HelpRequest(
            title="Agua para 20 familias", request_type="water", people_affected=20,
            location_text="Caraballeda", description_public="Se necesita agua potable urgente.",
            reporter_name_private="X", reporter_contact_private="y",
            status=ReportStatus.APPROVED, is_public=True,
        ))
        db.session.commit()
    login(client)
    page = client.get("/admin/operacion")
    assert page.status_code == 200
    assert "Resumen operativo" in page.text
    assert "Agua para 20 familias" in page.text  # necesidad
    assert "Brechas" in page.text  # análisis de brecha (sin recurso → gap)


def test_recognitions_management_requires_login(client):
    assert client.get("/admin/reconocimientos").status_code == 302


def test_admin_creates_recognition_from_panel(client, app, admin):
    login(client)
    resp = client.post(
        "/admin/reconocimientos",
        data={
            "kind": "rescue_dog", "name": "Capitán", "org": "Bomberos de Caracas",
            "country": "ve", "role": "Perro de búsqueda",
            "description": "Perro rescatista de prueba.", "photo_url": "",
            "source_name": "Prensa", "source_url": "https://example.org/cap",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Capitán" in resp.text  # aparece en el listado del panel
    assert "Capitán" in client.get("/reconocimientos").text  # y en público
    with app.app_context():
        from app.models import AuditLog, Recognition

        assert Recognition.query.filter_by(name="Capitán").count() == 1
        assert "recognition_created" in {a.action for a in AuditLog.query.all()}


def test_sources_overview_renders(client, admin):
    login(client)
    page = client.get("/admin/fuentes")
    assert page.status_code == 200
    assert "Inventario" in page.text
    assert "Reconocimientos" in page.text


def _pending_help_with_pii():
    from app.constants import ReportStatus
    from app.models import HelpRequest

    r = HelpRequest(
        title="Necesita agua", request_type="water", people_affected=3,
        location_text="Macuto", description_public="Texto público del caso.",
        reporter_name_private="Juan Privado", reporter_contact_private="+58 secreto",
        exact_address_private="Calle secreta 1", description_private="detalle privado",
        status=ReportStatus.PENDING,
    )
    db.session.add(r)
    db.session.commit()
    return r.id


def test_volunteer_reviews_without_pii_and_can_note(client, app, volunteer):
    with app.app_context():
        rid = _pending_help_with_pii()
    login(client, "vol@example.org")
    page = client.get(f"/admin/reportes/help_request/{rid}")
    assert page.status_code == 200
    assert "+58 secreto" not in page.text
    assert "Calle secreta 1" not in page.text
    assert "Juan Privado" not in page.text
    client.post(f"/admin/reportes/help_request/{rid}", data={"note": "Revisé el caso."})
    with app.app_context():
        from app.models import AdminNote

        assert AdminNote.query.count() == 1
    # No puede moderar ni acceder a gestión/export
    assert client.get("/admin/reconocimientos").status_code == 403
    assert client.get("/admin/exportar/help_request.csv").status_code == 403


def test_volunteer_cannot_change_status(client, app, volunteer):
    with app.app_context():
        rid = _pending_help_with_pii()
    login(client, "vol@example.org")
    client.post(
        f"/admin/reportes/help_request/{rid}",
        data={"status": "approved", "verification_status": "unverified",
              "priority": "high", "description_public": "x" * 20, "is_public": "y"},
    )
    with app.app_context():
        from app.constants import ReportStatus
        from app.models import HelpRequest

        report = db.session.get(HelpRequest, rid)
        assert report.status is ReportStatus.PENDING
        assert report.is_public is False


def test_viewer_sees_operations_but_not_review_or_admin(client, viewer):
    login(client, "viewer@example.org")
    assert client.get("/admin/operacion").status_code == 200
    assert client.get("/admin").status_code == 200  # tablero de solo lectura
    assert client.get("/admin/reportes/help_request/1").status_code == 403  # no revisa
    assert client.get("/admin/exportar/help_request.csv").status_code == 403
    assert client.get("/admin/usuarios").status_code == 403
