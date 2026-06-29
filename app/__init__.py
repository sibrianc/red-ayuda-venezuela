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

    @app.cli.command("seed-sample")
    def seed_sample():
        """Siembra datos de MUESTRA para previsualizar el mapa (no son datos reales)."""
        import random
        from uuid import uuid4

        from app.models import DirectoryEntry, IngestedEvent, Incident

        sample_attr = "Muestra de previsualización"
        # Limpia muestras previas para que el comando sea repetible.
        DirectoryEntry.query.filter_by(source_slug="sample").delete()
        IngestedEvent.query.filter_by(source_slug="sample").delete()
        Incident.query.filter_by(source_slug="sample").delete()

        services = [
            ("hospital", "Hospital Universitario de Caracas", 10.4945, -66.8987, True),
            ("hospital", "Hospital Vargas de Caracas", 10.5103, -66.9098, True),
            ("hospital", "Hospital J. M. de los Ríos", 10.5008, -66.8930, True),
            ("hospital", "Hospital Domingo Luciani", 10.4760, -66.8200, True),
            ("clinic", "Ambulatorio La Pastora", 10.5180, -66.9200, False),
            ("shelter", "Refugio temporal Parque del Este", 10.4960, -66.8370, False),
            ("shelter", "Refugio temporal Poliedro", 10.4530, -66.9420, False),
            ("fire_station", "Estación de Bomberos Cotiza", 10.5160, -66.9050, True),
            ("water_point", "Punto de agua Plaza Bolívar", 10.5061, -66.9146, False),
            ("pharmacy", "Farmacia comunitaria El Valle", 10.4500, -66.9100, False),
        ]
        for index, (category, name, lat, lon, emergency) in enumerate(services):
            db.session.add(DirectoryEntry(
                public_id=str(uuid4()), source_slug="sample", external_id=f"svc-{index}",
                content_hash=str(index), category=category, name=name,
                latitude=lat, longitude=lon, emergency=emergency, in_region=True,
                service_status="unknown", attribution=sample_attr,
            ))

        random.seed(42)
        for index in range(40):
            magnitude = round(random.uniform(2.4, 5.6), 1)
            db.session.add(IngestedEvent(
                public_id=str(uuid4()), source_slug="sample", external_id=f"eq-{index}",
                content_hash=str(index), event_type="earthquake", hazard_code="EQ",
                title=f"M {magnitude} — réplica de muestra",
                magnitude=magnitude, severity_value=magnitude,
                place="Región Capital (muestra)",
                latitude=round(10.5 + random.uniform(-0.9, 0.9), 4),
                longitude=round(-66.9 + random.uniform(-0.9, 0.9), 4),
                depth_km=round(random.uniform(5, 40), 1),
                occurred_at=datetime.now(timezone.utc) - timedelta(hours=random.uniform(0, 96)),
                alert_level=random.choice([None, "green", "green", "yellow"]),
                in_region=True, attribution=sample_attr,
            ))

        incidents = [
            ("collapsed_structure", "critical", "Residencias Altamira", "Av. Luis Roche, Altamira", 10.4965, -66.8531, "Se reportan personas atrapadas en pisos inferiores"),
            ("collapsed_structure", "critical", "Edificio Catia 7", "Av. Sucre, Catia", 10.5232, -66.9281, "Colapso parcial; equipos de rescate en sitio"),
            ("trapped_persons", "critical", "Centro comercial El Recreo", "Sabana Grande", 10.4921, -66.8782, "Personas atrapadas reportadas"),
            ("buried_persons", "critical", "Barrio La Cruz", "Petare", 10.4872, -66.8051, "Deslizamiento; posibles personas sepultadas"),
            ("collapsed_structure", "high", "Bloque 12, 23 de Enero", "23 de Enero", 10.5161, -66.9272, "Daño estructural severo"),
            ("fire", "high", "Galpón industrial", "Los Cortijos", 10.4991, -66.8202, "Incendio activo"),
            ("blocked_road", "medium", "Autopista Caracas–La Guaira", "km 8", 10.5803, -66.9301, "Vía bloqueada por derrumbe"),
            ("medical", "high", "Ambulatorio El Valle", "El Valle", 10.4502, -66.9121, "Saturación; faltan insumos"),
            ("missing_zone", "high", "Sector Antímano", "Antímano", 10.4601, -66.9602, "Varios reportes de desaparecidos en la zona"),
            ("collapsed_structure", "medium", "Casa parroquial", "Chacao", 10.4981, -66.8542, "Colapso parcial, sin víctimas confirmadas"),
            ("no_comms", "medium", "Zona alta de Petare", "Petare", 10.4801, -66.7951, "Sin comunicación reportada"),
            ("trapped_persons", "high", "Edificio residencial", "Los Teques", 10.3451, -67.0411, "Personas atrapadas, en evaluación"),
        ]
        for index, (category, severity, label, address, lat, lon, note) in enumerate(incidents):
            db.session.add(Incident(
                public_id=str(uuid4()), source_slug="sample", external_id=f"inc-{index}",
                content_hash=str(index), category=category, severity=severity, label=label,
                address_public=address, latitude=lat, longitude=lon,
                status=random.choice(["reported", "in_progress"]),
                situation_note=note, source_name="Reporte comunitario (muestra)",
                attribution=sample_attr, in_region=True,
                occurred_at=datetime.now(timezone.utc) - timedelta(hours=random.uniform(0, 72)),
            ))

        db.session.commit()
        click.echo("Datos de MUESTRA sembrados (solo previsualización del mapa): "
                   "12 incidentes específicos con dirección, 10 servicios, 40 sismos.")
        click.echo("El mapa de calor usa la capa de intensidad de zonas afectadas (no incidentes falsos).")
        click.echo("Datos reales: flask ingest-usgs / flask ingest-directory / flask load-official-figures")

    @app.cli.command("load-official-figures")
    def load_official_figures():
        """Carga cifras REALES citadas de fuentes oficiales (terremoto Venezuela 24 jun 2026)."""
        from datetime import date

        from app.models import SituationMetric

        UN_NEWS = "https://news.un.org/en/story/2026/06/1167825"
        OCHA = ("https://www.unocha.org/publications/report/venezuela-bolivarian-republic/"
                "latin-america-caribbean-weekly-situation-update-26-june-2026")
        as_of = datetime(2026, 6, 27, tzinfo=timezone.utc)

        figures = [
            ("missing", 50000, "ONU/OCHA — Tom Fletcher (coord. humanitario)", UN_NEWS,
             "La ONU estima más de 50.000 desaparecidos; el gobierno reporta cientos y un "
             "registro ciudadano ~68.900. Cifra en disputa, en verificación."),
            ("dead", 1430, "Autoridades de Venezuela / OCHA", OCHA,
             "Cifra al 27 jun 2026; en aumento conforme avanza la búsqueda."),
            ("injured", 3238, "Autoridades de Venezuela / OCHA", OCHA,
             "Cifra al 27 jun 2026."),
            ("responders", 2245, "OCHA / INSARAG", UN_NEWS,
             "44 equipos internacionales USAR desplegados."),
            ("search_dogs", 140, "OCHA / INSARAG", UN_NEWS,
             "Perros de búsqueda y rescate desplegados."),
        ]
        SituationMetric.query.delete()
        for metric_key, value, source_name, url, note in figures:
            db.session.add(SituationMetric(
                metric_key=metric_key, value=value, unit="personas",
                source_name=source_name, attribution=url,
                verification_status="reported", as_of=as_of, note=note,
            ))
        db.session.commit()
        click.echo(f"Cargadas {len(figures)} cifras oficiales citadas (al {date(2026,6,27)}).")
        click.echo("Fuentes: ONU News y OCHA. Cifras en verificación y en aumento.")

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
            "img-src 'self' data: https://tile.openstreetmap.org https://*.basemaps.cartocdn.com https://unpkg.com; "
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
