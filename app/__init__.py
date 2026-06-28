import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import click
from flask import Flask, request

from app.config import CONFIGS, ProductionConfig
from app.constants import PRIORITY_LABELS, REPORT_TYPE_LABELS, STATUS_LABELS, VERIFICATION_LABELS
from app.extensions import csrf, db, login_manager, migrate
from app.models import User


def create_app(config_name: str | None = None) -> Flask:
    env_name = config_name or os.getenv("FLASK_ENV", "development")
    config_class = CONFIGS.get(env_name, CONFIGS["development"])
    if config_class is ProductionConfig:
        config_class.validate()

    app = Flask(__name__)
    app.config.from_object(config_class)
    app.instance_path and os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.admin import bp as admin_bp
    from app.auth import bp as auth_bp
    from app.errors import bp as errors_bp
    from app.map import bp as map_bp
    from app.public import bp as public_bp
    from app.reports import bp as reports_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(errors_bp)

    register_cli(app)
    register_template_helpers(app)
    register_security_headers(app)
    return app


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


def register_cli(app: Flask) -> None:
    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt=True)
    @click.password_option(confirmation_prompt=True)
    def create_admin(email: str, name: str, password: str):
        """Crea el primer administrador sin exponer la contraseña en argumentos."""
        from app.constants import UserRole

        normalized_email = email.strip().lower()
        if User.query.filter_by(email=normalized_email).first():
            raise click.ClickException("Ya existe un usuario con ese correo.")
        if len(password) < 12:
            raise click.ClickException("La contraseña debe tener al menos 12 caracteres.")
        user = User(name=name.strip(), email=normalized_email, role=UserRole.ADMIN)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo("Administrador creado.")


def register_template_helpers(app: Flask) -> None:
    venezuela_tz = ZoneInfo("America/Caracas")

    @app.template_filter("venezuela_time")
    def venezuela_time(value: datetime | None, format_string: str = "%d/%m/%Y %H:%M"):
        if not value:
            return ""
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(venezuela_tz).strftime(format_string)

    @app.context_processor
    def labels():
        return {
            "report_type_labels": REPORT_TYPE_LABELS,
            "status_labels": STATUS_LABELS,
            "priority_labels": PRIORITY_LABELS,
            "verification_labels": VERIFICATION_LABELS,
        }


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def secure_response(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "style-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
            "script-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
            "img-src 'self' data: https://tile.openstreetmap.org https://unpkg.com; "
            "connect-src 'self'; font-src 'self' https://cdn.jsdelivr.net; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        if request.blueprint in {"admin", "auth"}:
            response.headers["Cache-Control"] = "no-store, private"
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
