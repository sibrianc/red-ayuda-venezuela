import os
from datetime import datetime, timedelta, timezone
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

    @app.cli.command("ingest-usgs")
    @click.option("--feed", default="month_2.5", show_default=True,
                  help="Feed USGS: hour_all, day_all, week_all, month_2.5, month_4.5, month_all.")
    @click.option("--min-magnitude", type=float, default=None,
                  help="Filtra eventos por magnitud mínima.")
    @click.option("--since-days", type=int, default=None,
                  help="Solo eventos de los últimos N días (p. ej. desde el sismo principal).")
    @click.option("--all-world", is_flag=True, default=False,
                  help="No limitar a Venezuela (por defecto SOLO Venezuela).")
    def ingest_usgs(feed: str, min_magnitude: float | None, since_days: int | None,
                    all_world: bool):
        """Descarga terremotos de USGS (por defecto solo Venezuela) y los procesa."""
        from app.ingestion.connectors import fetch_usgs, parse_usgs_geojson
        from app.ingestion.pipeline import event_overview, ingest_events

        click.echo(f"Descargando feed USGS '{feed}'...")
        try:
            payload = fetch_usgs(feed)
        except Exception as exc:  # noqa: BLE001 — el CLI reporta el error legible
            raise click.ClickException(
                f"No se pudo descargar el feed ({type(exc).__name__}: {exc}). "
                "Si ves un error de certificado en macOS, ejecuta "
                "'Install Certificates.command' de tu instalación de Python."
            ) from exc

        since = datetime.now(timezone.utc) - timedelta(days=since_days) if since_days else None
        scope = "todo el mundo" if all_world else "solo Venezuela"
        click.echo(f"Enfoque: terremotos, {scope}"
                   + (f", últimos {since_days} días" if since_days else ""))
        events = parse_usgs_geojson(payload)
        stats = ingest_events(
            events,
            min_magnitude=min_magnitude,
            region_only=not all_world,
            event_types={"earthquake"},
            since=since,
        )
        click.echo("Resultado de la ingesta:")
        for key, value in stats.as_dict().items():
            click.echo(f"  {key}: {value}")
        if stats.errors:
            click.echo(f"  errores: {len(stats.errors)}")

        overview = event_overview()
        click.echo("Total acumulado en base:")
        click.echo(f"  eventos: {overview['total']} (en región Venezuela: {overview['en_region']})")
        click.echo(f"  por magnitud: {overview['por_magnitud']}")
        click.echo(f"  evento más reciente: {overview['evento_mas_reciente']}")

    @app.cli.command("ingest-gdacs")
    @click.option("--feed", default="map", show_default=True,
                  help="Feed GDACS: map (eventos actuales) o search.")
    @click.option("--all-hazards", is_flag=True, default=False,
                  help="Incluir todas las amenazas (por defecto SOLO terremotos).")
    @click.option("--all-world", is_flag=True, default=False,
                  help="No limitar a Venezuela (por defecto SOLO Venezuela).")
    def ingest_gdacs(feed: str, all_hazards: bool, all_world: bool):
        """Descarga la alerta oficial de GDACS del terremoto (por defecto solo EQ + Venezuela)."""
        from app.ingestion.connectors import fetch_gdacs, parse_gdacs_geojson
        from app.ingestion.pipeline import event_overview, ingest_events

        click.echo(f"Descargando feed GDACS '{feed}'...")
        try:
            payload = fetch_gdacs(feed)
        except Exception as exc:  # noqa: BLE001 — el CLI reporta el error legible
            raise click.ClickException(
                f"No se pudo descargar el feed ({type(exc).__name__}: {exc}). "
                "Si ves un error de certificado en macOS, ejecuta "
                "'Install Certificates.command' de tu instalación de Python."
            ) from exc

        event_types = None if all_hazards else {"earthquake"}
        hazard_scope = "todas las amenazas" if all_hazards else "solo terremotos"
        region_scope = "todo el mundo" if all_world else "solo Venezuela"
        click.echo(f"Enfoque: {hazard_scope}, {region_scope}")
        events = parse_gdacs_geojson(payload)
        stats = ingest_events(events, region_only=not all_world, event_types=event_types)
        click.echo("Resultado de la ingesta:")
        for key, value in stats.as_dict().items():
            click.echo(f"  {key}: {value}")

        overview = event_overview()
        click.echo("Total acumulado en base:")
        click.echo(f"  eventos: {overview['total']} (en región Venezuela: {overview['en_region']})")
        click.echo(f"  por tipo: {overview['por_tipo']}")
        click.echo(f"  evento más reciente: {overview['evento_mas_reciente']}")

    @app.cli.command("ingest-directory")
    def ingest_directory_cmd():
        """Descarga el directorio de servicios de Venezuela desde OpenStreetMap."""
        from app.ingestion.connectors import fetch_overpass, parse_overpass
        from app.ingestion.pipeline import directory_overview, ingest_directory

        click.echo("Descargando servicios de OpenStreetMap (Overpass)...")
        try:
            payload = fetch_overpass()
        except Exception as exc:  # noqa: BLE001 — el CLI reporta el error legible
            raise click.ClickException(
                f"No se pudo descargar de Overpass ({type(exc).__name__}: {exc}). "
                "Si ves un error de certificado en macOS, ejecuta "
                "'Install Certificates.command' de tu instalación de Python."
            ) from exc

        entries = parse_overpass(payload)
        stats = ingest_directory(entries, region_only=True)
        click.echo("Resultado de la ingesta del directorio:")
        for key, value in stats.as_dict().items():
            click.echo(f"  {key}: {value}")
        overview = directory_overview()
        click.echo(f"Total en directorio: {overview['total']}")
        click.echo(f"por categoría: {overview['por_categoria']}")

    @app.cli.command("ingest-stats")
    def ingest_stats():
        """Muestra el volumen agregado de eventos y directorio ya ingeridos."""
        from app.ingestion.pipeline import directory_overview, event_overview

        overview = event_overview()
        click.echo(f"eventos: {overview['total']} (en región Venezuela: {overview['en_region']})")
        click.echo(f"por tipo: {overview['por_tipo']}")
        click.echo(f"por magnitud (sismos): {overview['por_magnitud']}")
        click.echo(f"evento más reciente: {overview['evento_mas_reciente']}")
        directory = directory_overview()
        click.echo(f"directorio: {directory['total']} servicios")
        click.echo(f"por categoría: {directory['por_categoria']}")


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
