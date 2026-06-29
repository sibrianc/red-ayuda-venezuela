"""Proyecciones públicas de los datos recopilados (eventos sísmicos y directorio).

Estos datos provienen de fuentes públicas autoritativas (USGS, GDACS) y abiertas
(OpenStreetMap). No contienen datos personales; se exponen con su atribución. La
publicación de reportes de personas sigue su propia puerta de revisión humana.
"""

import random

from sqlalchemy import or_

from app.constants import ReportStatus
from app.models import (
    CommunicationSignal,
    DirectoryEntry,
    IngestedEvent,
    Incident,
    MissingPersonReport,
    PersonRecord,
    SituationMetric,
)

# Registros oficiales de búsqueda y reunificación (referencia, no ingestión privada).
# Registros REALES de búsqueda y reunificación de este evento (referencia, no ingestión
# privada). Los nombres viven en estas plataformas; aquí solo enlazamos para que familias
# y rescatistas lleguen a ellas. A las plataformas ciudadanas se enlaza por búsqueda
# (evita fijar una URL no verificada que pueda cambiar o suplantarse).
OFFICIAL_REGISTRIES = [
    {"name": "Desaparecidos Terremoto Venezuela",
     "detail": "Registro ciudadano de desaparecidos y localizados (~50.000 reportados)",
     "url": "https://www.google.com/search?q=Desaparecidos+Terremoto+Venezuela"},
    {"name": "Venezuela Te Busca",
     "detail": "Registrar y buscar personas: nombre, edad, foto, última ubicación",
     "url": "https://www.google.com/search?q=%22Venezuela+Te+Busca%22+desaparecidos"},
    {"name": "CIVIS Venezuela",
     "detail": "Búsqueda de personas desaparecidas y recursos",
     "url": "https://www.google.com/search?q=CIVIS+Venezuela+desaparecidos+terremoto"},
    {"name": "Cruz Roja — Restoring Family Links",
     "detail": "Búsqueda internacional de familiares",
     "url": "https://familylinks.icrc.org/online-tracing"},
    {"name": "Gobierno — VenApp / 0800-RESCATE",
     "detail": "Línea oficial para reportar: 0800-7372282",
     "url": "https://www.google.com/search?q=VenApp+0800+RESCATE+terremoto+Venezuela"},
]

SITUATION_HEADLINE = [
    ("missing", "Desaparecidos"),
    ("dead", "Fallecidos"),
    ("injured", "Heridos"),
    ("rescued", "Rescatados"),
    ("responders", "Rescatistas int."),
    ("search_dogs", "Perros de rescate"),
    ("displaced", "Desplazados"),
    ("sheltered", "En refugios"),
]

INCIDENT_LABELS = {
    "collapsed_structure": "Edificio colapsado",
    "trapped_persons": "Personas atrapadas",
    "buried_persons": "Personas sepultadas",
    "missing_zone": "Zona con desaparecidos",
    "fire": "Incendio",
    "medical": "Emergencia médica",
    "blocked_road": "Vía bloqueada",
    "no_comms": "Zona sin comunicación",
    "other": "Incidente",
}

SEVERITY_WEIGHT = {"critical": 1.0, "high": 0.7, "medium": 0.45, "low": 0.25}

# Intensidad de zona afectada (modelo para el mapa de calor), posicionada en las
# zonas REALES más golpeadas del terremoto del 24 jun 2026 y ponderada por su
# severidad relativa: La Guaira fue la más devastada (~1.400 edificios), luego
# Caracas, y la región del epicentro en Yaracuy (San Felipe / Yumare). Esto NO son
# incidentes individuales; es una capa de intensidad agregada, separada del directorio.
AFFECTED_ZONES = [
    ("La Guaira", 10.600, -66.930, 1.00, 90, 0.045),
    ("Caracas", 10.490, -66.880, 0.92, 95, 0.060),
    ("San Felipe (epicentro)", 10.340, -68.740, 0.82, 60, 0.060),
    ("Yumare (epicentro)", 10.620, -68.690, 0.78, 40, 0.050),
    ("Maracay", 10.250, -67.600, 0.62, 45, 0.060),
    ("Valencia", 10.160, -68.000, 0.60, 45, 0.060),
    ("Los Teques", 10.340, -67.040, 0.52, 35, 0.050),
]


def _build_affected_intensity() -> list[list[float]]:
    rng = random.Random(7)  # determinista: misma intensidad en cada arranque
    points: list[list[float]] = []
    for _name, lat, lon, weight, count, spread in AFFECTED_ZONES:
        for _ in range(count):
            points.append([
                round(rng.gauss(lat, spread), 4),
                round(rng.gauss(lon, spread), 4),
                round(weight * rng.uniform(0.55, 1.0), 3),
            ])
    return points


AFFECTED_INTENSITY = _build_affected_intensity()


def affected_intensity() -> list[list[float]]:
    """Campo de intensidad [[lat, lon, peso], ...] para el mapa de calor (zonas afectadas)."""
    return AFFECTED_INTENSITY

CATEGORY_LABELS = {
    "hospital": "Hospital",
    "clinic": "Clínica",
    "pharmacy": "Farmacia",
    "fire_station": "Bomberos",
    "police": "Policía",
    "shelter": "Refugio",
    "community_center": "Centro comunitario",
    "water_point": "Punto de agua",
    "other": "Servicio",
}


def public_events(limit: int = 500) -> list[dict]:
    query = (
        IngestedEvent.query.filter(
            IngestedEvent.latitude.isnot(None),
            IngestedEvent.longitude.isnot(None),
        )
        .order_by(IngestedEvent.occurred_at.desc().nullslast())
        .limit(limit)
    )
    return [
        {
            "public_id": event.public_id,
            "event_type": event.event_type,
            "title": event.title,
            "magnitude": event.magnitude,
            "place": event.place,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "depth_km": event.depth_km,
            "alert_level": event.alert_level,
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            "attribution": event.attribution,
            "url": event.detail_url,
        }
        for event in query.all()
    ]


def public_missing_persons(q: str | None = None, limit: int = 300) -> list[dict]:
    """Personas desaparecidas publicadas para reunificación (Person Finder).

    Solo casos APROBADOS y públicos, y NUNCA menores (los menores siguen el flujo
    privado de protección). Expone nombre, edad y última ubicación para que familias
    y rescatistas puedan localizarlas; nunca contacto privado ni dirección exacta.
    """
    query = MissingPersonReport.query.filter_by(
        status=ReportStatus.APPROVED, is_public=True, involves_minor=False
    )
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(
                MissingPersonReport.first_name.ilike(term),
                MissingPersonReport.last_name.ilike(term),
                MissingPersonReport.location_text.ilike(term),
            )
        )
    query = query.order_by(MissingPersonReport.updated_at.desc()).limit(limit)
    return [
        {
            "public_id": person.public_id,
            "first_name": person.first_name,
            "last_name": person.last_name,
            "age": person.age,
            "gender": person.gender,
            "last_seen": person.location_text,
            "last_contact_date": person.last_contact_date.isoformat() if person.last_contact_date else None,
            "summary": person.description_public,
            "status": person.status.value,
        }
        for person in query.all()
    ]


def public_person_records(status: str | None = None, q: str | None = None, limit: int = 500) -> list[dict]:
    """Personas publicadas (PFIF / listas oficiales) por estado. Excluye menores."""
    query = PersonRecord.query.filter(PersonRecord.is_minor.is_(False))
    if status:
        query = query.filter(PersonRecord.person_status == status)
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(
                PersonRecord.full_name.ilike(term),
                PersonRecord.last_known_location.ilike(term),
                PersonRecord.home_location.ilike(term),
            )
        )
    query = query.order_by(PersonRecord.source_date.desc().nullslast(), PersonRecord.id.desc()).limit(limit)
    return [
        {
            "public_id": person.public_id,
            "full_name": person.full_name,
            "age": person.age,
            "sex": person.sex,
            "last_seen": person.last_known_location or person.home_location,
            "person_status": person.person_status,
            "summary": person.description,
            "source_name": person.source_name,
            "source_url": (
                person.source_url
                if person.source_url and person.source_url.startswith(("https://", "http://"))
                else None
            ),
            "source_date": person.source_date.isoformat() if person.source_date else None,
            "attribution": person.attribution,
        }
        for person in query.all()
    ]


def public_comms_zones(q: str | None = None, limit: int = 200) -> list[dict]:
    """Zonas sin comunicación reportadas (alertas). Nunca expone el contacto privado."""
    query = CommunicationSignal.query.filter(CommunicationSignal.status != "resolved")
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(
                CommunicationSignal.zone_label.ilike(term),
                CommunicationSignal.public_note.ilike(term),
            )
        )
    query = query.order_by(CommunicationSignal.reported_at.desc()).limit(limit)
    return [
        {
            "public_id": signal.public_id,
            "zone_label": signal.zone_label,
            "status": signal.status,
            "public_note": signal.public_note,
            "source": signal.source,
            "latitude": signal.latitude,
            "longitude": signal.longitude,
            "reported_at": signal.reported_at.isoformat() if signal.reported_at else None,
        }
        for signal in query.all()
    ]


def count_person_records(status: str | None = None, q: str | None = None) -> int:
    """Total real de personas publicadas por estado (excluye menores), para conteos."""
    query = PersonRecord.query.filter(PersonRecord.is_minor.is_(False))
    if status:
        query = query.filter(PersonRecord.person_status == status)
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(
                PersonRecord.full_name.ilike(term),
                PersonRecord.last_known_location.ilike(term),
                PersonRecord.home_location.ilike(term),
            )
        )
    return query.count()


def count_directory(q: str | None = None) -> int:
    """Total real de servicios (para el conteo del directorio, no limitado por display)."""
    query = DirectoryEntry.query.filter(
        DirectoryEntry.latitude.isnot(None), DirectoryEntry.longitude.isnot(None)
    )
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(DirectoryEntry.name.ilike(term), DirectoryEntry.address_public.ilike(term))
        )
    return query.count()


def public_situation() -> list[dict]:
    """Cifras titulares de magnitud: última por métrica, con fuente y verificación."""
    latest: dict[str, SituationMetric] = {}
    rows = (
        SituationMetric.query
        .order_by(SituationMetric.as_of.desc().nullslast(), SituationMetric.id.desc())
        .all()
    )
    for row in rows:
        latest.setdefault(row.metric_key, row)
    headline = []
    for key, label in SITUATION_HEADLINE:
        metric = latest.get(key)
        if metric is None:
            continue
        headline.append({
            "key": key,
            "label": label,
            "value": metric.value,
            "source_name": metric.source_name,
            "attribution": metric.attribution,
            "verification_status": metric.verification_status,
            "note": metric.note,
            "as_of": metric.as_of.isoformat() if metric.as_of else None,
        })
    return headline


def public_incidents(q: str | None = None, limit: int = 5000) -> list[dict]:
    severity_order = sa_case_severity()
    query = Incident.query.filter(
        Incident.latitude.isnot(None),
        Incident.longitude.isnot(None),
    )
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(
                Incident.label.ilike(term),
                Incident.address_public.ilike(term),
                Incident.situation_note.ilike(term),
            )
        )
    query = query.order_by(severity_order, Incident.occurred_at.desc().nullslast()).limit(limit)
    return [
        {
            "public_id": incident.public_id,
            "category": incident.category,
            "category_label": INCIDENT_LABELS.get(incident.category, "Incidente"),
            "severity": incident.severity,
            "weight": SEVERITY_WEIGHT.get(incident.severity, 0.5),
            "label": incident.label,
            "latitude": incident.latitude,
            "longitude": incident.longitude,
            "address": incident.address_public,
            "status": incident.status,
            "situation_note": incident.situation_note,
            "source_name": incident.source_name,
            "attribution": incident.attribution,
            "occurred_at": incident.occurred_at.isoformat() if incident.occurred_at else None,
        }
        for incident in query.all()
    ]


def sa_case_severity():
    """Ordena por severidad (crítica primero) de forma portable."""
    from sqlalchemy import case

    return case(
        {"critical": 0, "high": 1, "medium": 2, "low": 3},
        value=Incident.severity,
        else_=4,
    )


def public_directory(q: str | None = None, limit: int = 3000) -> list[dict]:
    query = DirectoryEntry.query.filter(
        DirectoryEntry.latitude.isnot(None),
        DirectoryEntry.longitude.isnot(None),
    )
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(
                DirectoryEntry.name.ilike(term),
                DirectoryEntry.address_public.ilike(term),
            )
        )
    query = query.order_by(DirectoryEntry.emergency.desc()).limit(limit)
    return [
        {
            "public_id": entry.public_id,
            "category": entry.category,
            "category_label": CATEGORY_LABELS.get(entry.category, "Servicio"),
            "name": entry.name,
            "latitude": entry.latitude,
            "longitude": entry.longitude,
            "address": entry.address_public,
            "phone": entry.phone_public,
            "operator": entry.operator,
            "emergency": entry.emergency,
            "attribution": entry.attribution,
            "url": entry.source_url,
        }
        for entry in query.all()
    ]
