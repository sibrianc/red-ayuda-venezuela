import pyotp
import pytest

from app import create_app
from app.constants import UserRole
from app.extensions import db
from app.models import User

# Secreto TOTP fijo para las cuentas de prueba (permite calcular códigos 2FA válidos).
TEST_TOTP_SECRET = "JBSWY3DPEHPK3PXP"


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin(app):
    with app.app_context():
        user = User(
            name="Admin", email="admin@example.org", role=UserRole.ADMIN,
            totp_secret=TEST_TOTP_SECRET, totp_enabled=True,
        )
        user.set_password("correct-horse-battery-staple")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture()
def reviewer(app):
    with app.app_context():
        user = User(
            name="Reviewer", email="reviewer@example.org", role=UserRole.REVIEWER,
            totp_secret=TEST_TOTP_SECRET, totp_enabled=True,
        )
        user.set_password("correct-horse-battery-staple")
        db.session.add(user)
        db.session.commit()
        return user.id


def login(client, email="admin@example.org"):
    """Inicia sesión completa: contraseña + segundo factor (2FA)."""
    client.post(
        "/cuenta/login",
        data={"email": email, "password": "correct-horse-battery-staple"},
        follow_redirects=False,
    )
    return client.post(
        "/cuenta/2fa",
        data={"code": pyotp.TOTP(TEST_TOTP_SECRET).now()},
        follow_redirects=False,
    )


@pytest.fixture()
def base_report_data():
    return {
        "location_text": "Parroquia La Guaira",
        "exact_address_private": "Calle privada 123",
        "latitude": "10.60",
        "longitude": "-66.93",
        "description_public": "Se requiere revisión de esta situación en la zona general indicada.",
        "description_private": "Detalle interno reservado.",
        "reporter_name_private": "Persona Reportante",
        "reporter_contact_private": "+58 000 0000000",
        "privacy_consent": "y",
        "website": "",
    }
