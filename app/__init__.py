import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import click
from flask import Flask, request

from app.config import CONFIGS, ProductionConfig
from app.constants import PRIORITY_LABELS, REPORT_TYPE_LABELS, STATUS_LABELS, VERIFICATION_LABELS
from app.extensions import csrf, db, limiter, login_manager, migrate
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
    limiter.init_app(app)

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

    from app import i18n
    i18n.init_app(app)

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

    @app.cli.command("ingest-building-damage")
    def ingest_building_damage():
        """Carga daño satelital candidato y la lista nominal trazable de colapsos."""
        from app.ingestion.catalog import build_public_staging_sources
        from app.ingestion.incidents import (
            curated_collapsed_structures,
            fetch_hdx_damage,
            parse_hdx_damage_geojson,
        )
        from app.ingestion.pipeline import ingest_incidents
        from app.ingestion.registry import require_staging_authorization

        sources = {source.slug: source for source in build_public_staging_sources()}
        require_staging_authorization(sources["hot-fair-damage"])
        require_staging_authorization(sources["el-estimulo-collapse-list"])

        click.echo("Cargando lista nominal de estructuras colapsadas...")
        listed = ingest_incidents(curated_collapsed_structures())
        click.echo(
            f"  lista: {listed.new} nuevos, {listed.updated} actualizados, "
            f"{listed.unchanged} sin cambios"
        )
        click.echo("Descargando evaluación satelital HOT/OCHA HDX...")
        try:
            payload = fetch_hdx_damage()
        except Exception as exc:  # noqa: BLE001 — error legible de fuente externa
            raise click.ClickException(
                f"No se pudo descargar HOT/OCHA HDX ({type(exc).__name__}: {exc})."
            ) from exc
        assessed = ingest_incidents(parse_hdx_damage_geojson(payload))
        click.echo(
            f"  satélite: {assessed.new} nuevos, {assessed.updated} actualizados, "
            f"{assessed.unchanged} sin cambios"
        )
        click.echo(
            "Las predicciones satelitales permanecen como candidatas; "
            "no confirman ocupantes ni personas atrapadas."
        )

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

    @app.cli.command("ingest-all")
    @click.option("--pfif", default=None, help="URL de un feed PFIF para importar personas.")
    def ingest_all(pfif: str | None):
        """Recopila TODOS los datos reales en un paso (USGS, GDACS, OSM, +PFIF opcional)."""
        from app.ingestion.connectors import (
            fetch_gdacs, fetch_overpass, fetch_usgs,
            parse_gdacs_geojson, parse_overpass, parse_usgs_geojson,
        )
        import time

        from app.ingestion.localizados import fetch_localizados, parse_localizados
        from app.ingestion.catalog import build_public_staging_sources
        from app.ingestion.incidents import (
            curated_collapsed_structures, fetch_hdx_damage, parse_hdx_damage_geojson,
        )
        from app.ingestion.pipeline import (
            directory_overview, event_overview, ingest_directory, ingest_events,
            ingest_incidents, ingest_persons,
        )
        from app.ingestion.venezuelareporta import fetch_reporta, parse_reporta
        from app.ingestion.registry import require_staging_authorization

        registered_sources = {
            source.slug: source for source in build_public_staging_sources()
        }

        def step(name, action):
            try:
                action()
                click.echo(f"  ✓ {name}")
            except Exception as exc:  # noqa: BLE001 — seguir con las demás fuentes
                click.echo(f"  ✗ {name}: {type(exc).__name__}: {exc}")

        click.echo("Recopilando datos reales (solo Venezuela, solo terremotos)...")
        step("USGS — sismos/réplicas",
             lambda: ingest_events(parse_usgs_geojson(fetch_usgs("month_2.5")),
                                   region_only=True, event_types={"earthquake"}))
        step("GDACS — alerta oficial",
             lambda: ingest_events(parse_gdacs_geojson(fetch_gdacs("map")),
                                   region_only=True, event_types={"earthquake"}))
        step("OpenStreetMap — directorio de servicios",
             lambda: ingest_directory(parse_overpass(fetch_overpass()), region_only=True))

        def _hdx_damage():
            require_staging_authorization(registered_sources["hot-fair-damage"])
            return ingest_incidents(parse_hdx_damage_geojson(fetch_hdx_damage()))

        def _collapsed_list():
            require_staging_authorization(registered_sources["el-estimulo-collapse-list"])
            return ingest_incidents(curated_collapsed_structures())

        step(
            "HOT/OCHA HDX — evaluación de daños estructurales",
            _hdx_damage,
        )
        step(
            "Lista nominal — estructuras colapsadas publicadas",
            _collapsed_list,
        )

        def _localizados():
            page = 1
            while page <= 100:
                payload = fetch_localizados(page=page, limit=100)
                people = parse_localizados(payload)
                if not people:
                    break
                ingest_persons(people)
                meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
                if meta.get("totalPages") and page >= meta["totalPages"]:
                    break
                page += 1
                time.sleep(0.15)

        step("Localizados Venezuela — personas localizadas", _localizados)
        step("Venezuela Reporta — desaparecidos",
             lambda: ingest_persons(parse_reporta(fetch_reporta())))

        from app.ingestion.pipeline import recompute_corroboration

        step("Verificación cruzada (corroboración entre fuentes)", recompute_corroboration)
        if pfif:
            from app.ingestion.pfif import fetch_pfif, parse_pfif
            from app.ingestion.pipeline import ingest_persons
            step("PFIF — personas",
                 lambda: ingest_persons(parse_pfif(fetch_pfif(pfif), source_slug="pfif")))

        events = event_overview()
        directory = directory_overview()
        click.echo("Totales en base:")
        click.echo(f"  sismos: {events['total']} (en región Venezuela: {events['en_region']})")
        click.echo(f"  servicios: {directory['total']}")
        click.echo("Cifras oficiales citadas: corre 'flask load-official-figures' (ONU/OCHA).")

    @app.cli.command("export-contributions")
    @click.option("--target", default="venezuela-reporta",
                  help="Fuente a enriquecer; NO se duplica lo que ya tiene.")
    @click.option("--out", default=None, help="Ruta del JSON de salida.")
    def export_contributions_cmd(target: str, out: str | None):
        """Genera el export de personas que NOSOTROS tenemos y la fuente objetivo NO,
        para compartírselo (somos intermediarios/conectores). Dedup conservador por
        match_key; excluye menores; nunca incluye contactos privados."""
        import json
        import os

        from app.ingestion.pipeline import recompute_corroboration
        from app.models import PersonRecord

        recompute_corroboration()
        target_keys = {
            key for (key,) in db.session.query(PersonRecord.match_key)
            .filter(PersonRecord.source_slug == target, PersonRecord.match_key.isnot(None))
            .distinct()
        }
        candidates = (
            PersonRecord.query.filter(
                PersonRecord.source_slug != target,
                PersonRecord.is_minor.is_(False),
                PersonRecord.match_key.isnot(None),
                PersonRecord.match_key != "",
            ).all()
        )
        seen: set[str] = set()
        rows = []
        for person in candidates:
            if person.match_key in target_keys or person.match_key in seen:
                continue
            seen.add(person.match_key)
            rows.append({
                "full_name": person.full_name,
                "status": person.person_status,
                "last_known_location": person.last_known_location,
                "home_location": person.home_location,
                "age": person.age,
                "sex": person.sex,
                "description": person.description,
                "source_name": person.source_name,
                "source_url": person.source_url,
                "source_slug": person.source_slug,
            })
        out = out or os.path.join("data", "exports", f"contribuciones-{target}.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as handle:
            json.dump({"target": target, "count": len(rows), "records": rows},
                      handle, ensure_ascii=False, indent=2)
        click.echo(f"Export listo: {len(rows)} personas que «{target}» no tiene → {out}")
        click.echo("Compártelo con ellos por su canal; no escribimos en su base directamente.")

    @app.cli.command("import-reporta")
    def import_reporta_cmd():
        """Importa personas de venezuelareporta.org (páginas públicas server-rendered, robots-OK)."""
        from app.ingestion.pipeline import ingest_persons
        from app.ingestion.venezuelareporta import fetch_reporta, parse_reporta

        try:
            html = fetch_reporta()
        except Exception as exc:  # noqa: BLE001 — el CLI reporta el error legible
            raise click.ClickException(f"No se pudo descargar ({type(exc).__name__}: {exc}).") from exc
        people = parse_reporta(html)
        stats = ingest_persons(people)
        from app.ingestion.pipeline import recompute_corroboration

        corroborated = recompute_corroboration()
        click.echo(f"Venezuela Reporta: {stats.new} nuevos, {stats.unchanged} sin cambios.")
        minors = sum(1 for person in people if person.is_minor)
        click.echo(f"Menores detectados (excluidos del público): {minors}")
        click.echo(f"Verificación cruzada: {corroborated} personas con 2+ fuentes.")

    @app.cli.command("import-localizados")
    @click.option("--max-pages", type=int, default=200, help="Tope de páginas por seguridad.")
    @click.option("--limit", type=int, default=100, show_default=True)
    def import_localizados_cmd(max_pages: int, limit: int):
        """Importa personas LOCALIZADAS desde la API pública de Localizados Venezuela."""
        import time

        from app.ingestion.localizados import fetch_localizados, parse_localizados
        from app.ingestion.pipeline import ingest_persons

        total_new = 0
        total_minors = 0
        page = 1
        click.echo("Descargando de la API pública de Localizados Venezuela...")
        while page <= max_pages:
            try:
                payload = fetch_localizados(page=page, limit=limit)
            except Exception as exc:  # noqa: BLE001 — el CLI reporta el error legible
                raise click.ClickException(
                    f"Falló la descarga en la página {page} ({type(exc).__name__}: {exc})."
                ) from exc
            people = parse_localizados(payload)
            if not people:
                break
            stats = ingest_persons(people)
            total_new += stats.new
            total_minors += sum(1 for person in people if person.is_minor)
            meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
            total_pages = meta.get("totalPages")
            click.echo(f"  página {page}/{total_pages or '?'}: +{stats.new} nuevos")
            if total_pages and page >= total_pages:
                break
            page += 1
            time.sleep(0.2)  # cortesía con su servidor
        from app.ingestion.pipeline import recompute_corroboration

        corroborated = recompute_corroboration()
        click.echo(
            f"Listo. Personas localizadas nuevas: {total_new}. "
            f"Menores detectados (excluidos del público): {total_minors}."
        )
        click.echo(f"Verificación cruzada: {corroborated} personas con 2+ fuentes.")

    @app.cli.command("import-persons-json")
    @click.argument("source")
    @click.option("--source-slug", default="published", show_default=True)
    @click.option("--attribution", default=None, help="Atribución de la plataforma/fuente publicada.")
    def import_persons_json_cmd(source: str, source_slug: str, attribution: str | None):
        """Importa personas desde una exportación JSON (URL o archivo). Vía limpia, con atribución."""
        from app.ingestion.pfif import fetch_pfif, parse_persons_json
        from app.ingestion.pipeline import ingest_persons

        if source.startswith(("http://", "https://")):
            try:
                text = fetch_pfif(source)  # descarga de texto genérica (reutilizada)
            except Exception as exc:  # noqa: BLE001 — el CLI reporta el error legible
                raise click.ClickException(
                    f"No se pudo descargar ({type(exc).__name__}: {exc})."
                ) from exc
        else:
            with open(source, encoding="utf-8") as handle:
                text = handle.read()

        people = parse_persons_json(text, source_slug=source_slug, attribution=attribution)
        stats = ingest_persons(people)
        click.echo("Resultado del import JSON de personas:")
        for key, value in stats.as_dict().items():
            click.echo(f"  {key}: {value}")
        minors = sum(1 for person in people if person.is_minor)
        click.echo(f"Menores detectados (excluidos del público por protección): {minors}")

    @app.cli.command("import-pets-json")
    @click.argument("source")
    @click.option("--source-slug", default="pets", show_default=True)
    @click.option("--attribution", default=None, help="Atribución de la fuente verificada de mascotas.")
    def import_pets_json_cmd(source: str, source_slug: str, attribution: str | None):
        """Importa mascotas desaparecidas desde un export JSON de una FUENTE VERIFICADA (URL o archivo)."""
        from app.ingestion.pets import parse_pets_json
        from app.ingestion.pfif import fetch_pfif
        from app.ingestion.pipeline import ingest_pets

        if source.startswith(("http://", "https://")):
            try:
                text = fetch_pfif(source)  # descarga de texto genérica (reutilizada)
            except Exception as exc:  # noqa: BLE001 — el CLI reporta el error legible
                raise click.ClickException(
                    f"No se pudo descargar ({type(exc).__name__}: {exc})."
                ) from exc
        else:
            with open(source, encoding="utf-8") as handle:
                text = handle.read()

        pets = parse_pets_json(text, source_slug=source_slug, attribution=attribution)
        stats = ingest_pets(pets)
        click.echo("Resultado del import JSON de mascotas:")
        for key, value in stats.as_dict().items():
            click.echo(f"  {key}: {value}")

    @app.cli.command("import-recognitions-json")
    @click.argument("source")
    @click.option("--source-slug", default="recognitions", show_default=True)
    @click.option("--attribution", default=None, help="Atribución de la fuente oficial.")
    def import_recognitions_json_cmd(source: str, source_slug: str, attribution: str | None):
        """Importa reconocimientos (unidades + perros) desde un export JSON de una FUENTE OFICIAL."""
        from app.ingestion.pfif import fetch_pfif
        from app.ingestion.pipeline import ingest_recognitions
        from app.ingestion.recognitions import parse_recognitions_json

        if source.startswith(("http://", "https://")):
            try:
                text = fetch_pfif(source)
            except Exception as exc:  # noqa: BLE001 — el CLI reporta el error legible
                raise click.ClickException(
                    f"No se pudo descargar ({type(exc).__name__}: {exc})."
                ) from exc
        else:
            with open(source, encoding="utf-8") as handle:
                text = handle.read()

        recognitions = parse_recognitions_json(text, source_slug=source_slug, attribution=attribution)
        stats = ingest_recognitions(recognitions)
        click.echo("Resultado del import JSON de reconocimientos:")
        for key, value in stats.as_dict().items():
            click.echo(f"  {key}: {value}")

    @app.cli.command("import-pfif")
    @click.argument("source")
    @click.option("--source-slug", default="pfif", show_default=True)
    @click.option("--attribution", default=None, help="Atribución de la fuente publicada.")
    def import_pfif_cmd(source: str, source_slug: str, attribution: str | None):
        """Importa personas desde un documento PFIF (URL o archivo) para reunificación."""
        from app.ingestion.pfif import fetch_pfif, parse_pfif
        from app.ingestion.pipeline import ingest_persons

        if source.startswith(("http://", "https://")):
            click.echo(f"Descargando PFIF de {source}...")
            try:
                xml_text = fetch_pfif(source)
            except Exception as exc:  # noqa: BLE001 — el CLI reporta el error legible
                raise click.ClickException(
                    f"No se pudo descargar ({type(exc).__name__}: {exc})."
                ) from exc
        else:
            with open(source, encoding="utf-8") as handle:
                xml_text = handle.read()

        people = parse_pfif(xml_text, source_slug=source_slug, attribution=attribution)
        stats = ingest_persons(people)
        click.echo("Resultado del import PFIF:")
        for key, value in stats.as_dict().items():
            click.echo(f"  {key}: {value}")
        minors = sum(1 for person in people if person.is_minor)
        click.echo(f"Personas con edad de menor (excluidas del público por protección): {minors}")

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
            "Permissions-Policy", "camera=(), microphone=(), geolocation=(self), payment=()"
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "style-src 'self' https://cdn.jsdelivr.net https://unpkg.com https://fonts.googleapis.com; "
            "style-src-attr 'unsafe-inline'; "
            "script-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
            # Las imágenes pueden venir de teselas de mapa y de fotos (mascotas/reconocimientos)
            # enviadas como enlace https; son inertes (no ejecutan código) y se cargan con
            # referrerpolicy=no-referrer. Se permite cualquier imagen https, nunca http.
            "img-src 'self' data: https:; "
            "connect-src 'self'; font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
            "object-src 'none'; frame-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        if request.blueprint in {"admin", "auth"}:
            response.headers["Cache-Control"] = "no-store, private"
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
