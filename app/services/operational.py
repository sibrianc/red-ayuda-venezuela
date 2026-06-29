"""Proyecciones públicas de los datos recopilados (eventos sísmicos y directorio).

Estos datos provienen de fuentes públicas autoritativas (USGS, GDACS) y abiertas
(OpenStreetMap). No contienen datos personales; se exponen con su atribución. La
publicación de reportes de personas sigue su propia puerta de revisión humana.
"""

import urllib.parse

from sqlalchemy import func, or_

from app.constants import SPECIES_LABELS, ReportStatus
from app.ingestion.normalize import normalize_name
from app.models import (
    CommunicationSignal,
    DirectoryEntry,
    IngestedEvent,
    Incident,
    LostPetReport,
    MissingPersonReport,
    PersonRecord,
    PetRecord,
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
    "destroyed_structure_candidate": "Posible estructura destruida",
    "major_damage_candidate": "Posible daño estructural mayor",
    "minor_damage_candidate": "Posible daño estructural menor",
    "other": "Incidente",
}

INCIDENT_VERIFICATION_LABELS = {
    "candidate": "Evaluación satelital · pendiente de validación",
    "reported": "Reporte publicado · pendiente de verificación",
    "corroborated": "Corroborado por fuentes públicas",
    "verified": "Verificado en terreno",
}

DAMAGE_CANDIDATE_CATEGORIES = {
    "destroyed_structure_candidate",
    "major_damage_candidate",
    "minor_damage_candidate",
}

SEVERITY_WEIGHT = {"critical": 1.0, "high": 0.7, "medium": 0.45, "low": 0.25}

# Zonas afectadas conocidas (coordenadas aproximadas) para geolocalizar la ubicación
# de TEXTO de los desaparecidos y poder pesarlas en el mapa de calor. Orden: específico
# primero (Catia La Mar antes que La Guaira), genérico al final.
ZONE_COORDS = [
    (("catia la mar",), 10.6020, -67.0260, "Catia La Mar"),
    (("caraballeda",), 10.6110, -66.8510, "Caraballeda"),
    (("tanaguarena", "tanaguar"), 10.6190, -66.8330, "Tanaguarena"),
    (("naiguata",), 10.6170, -66.7390, "Naiguatá"),
    (("maiquetia",), 10.5980, -66.9810, "Maiquetía"),
    (("macuto",), 10.6080, -66.8920, "Macuto"),
    (("petare",), 10.4760, -66.8050, "Petare"),
    (("la guaira", "guaira", "vargas", "caribe", "los cocos", "vistamar"), 10.6010, -66.9330, "La Guaira"),
    (("catia",), 10.5230, -66.9280, "Catia"),
    (("caracas",), 10.4880, -66.8790, "Caracas"),
]


def _match_zone(text: str | None):
    t = normalize_name(text)
    if not t:
        return None
    for keys, lat, lng, label in ZONE_COORDS:
        if any(k in t for k in keys):
            return (lat, lng, label)
    return None


def missing_person_hotspots() -> list[dict]:
    """Zonas con MÁS personas desaparecidas (geolocalizadas por su ubicación de texto).
    Prioriza la búsqueda y hace que el mapa de calor marque como más intensas las zonas
    con más desaparecidos."""
    rows = (
        PersonRecord.query.filter(
            PersonRecord.is_minor.is_(False),
            PersonRecord.person_status == "missing",
        )
        .with_entities(PersonRecord.last_known_location, PersonRecord.home_location)
        .all()
    )
    agg: dict[str, dict] = {}
    for last_known, home in rows:
        zone = _match_zone(last_known or home or "")
        if not zone:
            continue
        lat, lng, label = zone
        cell = agg.setdefault(label, {"label": label, "lat": lat, "lng": lng, "count": 0})
        cell["count"] += 1
    return sorted(agg.values(), key=lambda z: z["count"], reverse=True)


def affected_intensity() -> list[list[float]]:
    """Calor de zonas afectadas: registros estructurales trazables + DENSIDAD de personas
    desaparecidas (las zonas con más desaparecidos son las más intensas). Nunca inventa puntos."""
    points = []
    for incident in public_incidents(require_coordinates=True):
        confidence = incident.get("confidence")
        # Tope para que la densidad de desaparecidos pueda dominar la zona más intensa.
        weight = min(0.7, SEVERITY_WEIGHT.get(incident["severity"], 0.35))
        if confidence is not None:
            weight *= max(0.2, confidence)
        points.append([incident["latitude"], incident["longitude"], round(weight, 3)])
    hotspots = missing_person_hotspots()
    if hotspots:
        top = max(h["count"] for h in hotspots) or 1
        for h in hotspots:
            # 0.5..1.0 según el número de desaparecidos (la zona con más = máxima intensidad).
            weight = 0.5 + 0.5 * (h["count"] / top)
            points.append([h["lat"], h["lng"], round(weight, 3)])
    return points


DANGER_CATEGORIES_PUBLIC = {
    "collapsed_structure", "trapped_persons", "buried_persons", "fire", "blocked_road",
}


def coordination_overview() -> dict:
    """Datos del Centro de Coordinación que conecta familias ↔ rescatistas ↔ recursos:
    prioridades de rescate, zonas con más desaparecidos, zonas sin comunicación y conteos."""
    incidents = public_incidents()
    priorities = [
        i for i in incidents
        if i["category"] in DANGER_CATEGORIES_PUBLIC
        and i["severity"] in {"critical", "high"}
        and i.get("latitude") is not None
    ][:30]
    return {
        "missing_total": count_person_records("missing"),
        "localized_total": count_person_records("found"),
        "deceased_total": count_person_records("deceased"),
        "incident_total": len(incidents),
        "priorities": priorities,
        "hotspots": missing_person_hotspots(),
        "comms_zones": public_comms_zones(),
        "registries": OFFICIAL_REGISTRIES,
    }

CATEGORY_LABELS = {
    "hospital": "Hospital",
    "clinic": "Clínica",
    "pharmacy": "Farmacia",
    "fire_station": "Bomberos",
    "police": "Policía",
    "shelter": "Refugio",
    "community_center": "Centro comunitario",
    "water_point": "Punto de agua",
    "fuel": "Gasolinera / combustible",
    "supplies": "Mercado / víveres",
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
            "maps_url": maps_url(text=person.location_text),
            "last_contact_date": person.last_contact_date.isoformat() if person.last_contact_date else None,
            "summary": person.description_public,
            "status": person.status.value,
        }
        for person in query.all()
    ]


def maps_url(latitude=None, longitude=None, text: str | None = None) -> str | None:
    """Enlace a Google Maps: por coordenadas si las hay; si no, por texto de ubicación."""
    if latitude is not None and longitude is not None:
        return f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
    if text and text.strip():
        return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(f"{text.strip()}, Venezuela")
    return None


def safe_public_url(value: str | None) -> str | None:
    """Solo permite enlaces web explícitos en proyecciones públicas."""
    return value if value and value.startswith(("https://", "http://")) else None


def public_person_records(status: str | None = None, q: str | None = None, limit: int = 500, offset: int = 0) -> list[dict]:
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
    query = query.order_by(PersonRecord.source_date.desc().nullslast(), PersonRecord.id.desc()).offset(offset).limit(limit)
    return [
        {
            "public_id": person.public_id,
            "full_name": person.full_name,
            "age": person.age,
            "sex": person.sex,
            "last_seen": person.last_known_location or person.home_location,
            "maps_url": maps_url(text=person.last_known_location or person.home_location),
            "person_status": person.person_status,
            "summary": person.description,
            "source_name": person.source_name,
            "source_url": safe_public_url(person.source_url),
            "source_date": person.source_date.isoformat() if person.source_date else None,
            "attribution": person.attribution,
            "corroboration": person.corroboration,
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


def public_incidents(
    q: str | None = None,
    limit: int = 5000,
    *,
    require_coordinates: bool = False,
) -> list[dict]:
    """Incidentes públicos con una puerta explícita de evidencia.

    Las muestras y reportes no verificados quedan fuera. Una categoría de personas
    atrapadas requiere corroboración/validación y confirmación específica de ocupantes.
    Las predicciones satelitales solo se admiten en categorías *_candidate.
    """
    severity_order = sa_case_severity()
    operational_evidence = Incident.verification_status.in_(("corroborated", "verified"))
    published_collapse = (
        (Incident.category == "collapsed_structure")
        & (Incident.verification_status == "reported")
    )
    trapped_evidence = or_(
        ~Incident.category.in_(("trapped_persons", "buried_persons")),
        Incident.people_trapped_status == "confirmed",
    )
    satellite_candidate = (
        Incident.category.in_(DAMAGE_CANDIDATE_CATEGORIES)
        & (Incident.verification_status == "candidate")
    )
    query = Incident.query.filter(
        Incident.source_slug != "sample",
        or_(operational_evidence & trapped_evidence, published_collapse, satellite_candidate),
    )
    if require_coordinates:
        query = query.filter(Incident.latitude.isnot(None), Incident.longitude.isnot(None))
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(
                Incident.label.ilike(term),
                Incident.address_public.ilike(term),
                Incident.situation_note.ilike(term),
                Incident.source_name.ilike(term),
            )
        )
    verification_order = sa_case_incident_verification()
    query = query.order_by(
        verification_order,
        severity_order,
        Incident.source_date.desc().nullslast(),
    ).limit(limit)
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
            "maps_url": maps_url(incident.latitude, incident.longitude, incident.address_public),
            "status": incident.status,
            "verification_status": incident.verification_status,
            "verification_label": INCIDENT_VERIFICATION_LABELS.get(
                incident.verification_status, "Pendiente de verificación"
            ),
            "situation_note": incident.situation_note,
            "source_name": incident.source_name,
            "source_url": safe_public_url(incident.source_url),
            "source_date": incident.source_date.isoformat() if incident.source_date else None,
            "attribution": incident.attribution,
            "confidence": incident.confidence,
            "location_precision": incident.location_precision,
            "area_radius_m": incident.area_radius_m,
            "people_trapped_status": incident.people_trapped_status,
            "people_trapped_count": incident.people_trapped_count,
            "is_damage_candidate": incident.category in DAMAGE_CANDIDATE_CATEGORIES,
            "is_verified_danger": (
                incident.category not in DAMAGE_CANDIDATE_CATEGORIES
                and incident.verification_status in {"corroborated", "verified"}
            ),
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


def sa_case_incident_verification():
    """Ordena evidencia verificada/corroborada antes de predicciones candidatas."""
    from sqlalchemy import case

    return case(
        {"verified": 0, "corroborated": 1, "candidate": 2},
        value=Incident.verification_status,
        else_=3,
    )


def directory_category_counts(q: str | None = None) -> dict:
    """Conteo REAL de servicios por categoría (para filtros del directorio)."""
    query = DirectoryEntry.query.filter(
        DirectoryEntry.latitude.isnot(None),
        DirectoryEntry.longitude.isnot(None),
    )
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(DirectoryEntry.name.ilike(term), DirectoryEntry.address_public.ilike(term))
        )
    rows = query.with_entities(DirectoryEntry.category, func.count(DirectoryEntry.id)).group_by(
        DirectoryEntry.category
    ).all()
    return {category: count for category, count in rows}


def public_directory(q: str | None = None, category: str | None = None, limit: int = 3000, offset: int = 0) -> list[dict]:
    query = DirectoryEntry.query.filter(
        DirectoryEntry.latitude.isnot(None),
        DirectoryEntry.longitude.isnot(None),
    )
    if category:
        query = query.filter(DirectoryEntry.category == category)
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(
                DirectoryEntry.name.ilike(term),
                DirectoryEntry.address_public.ilike(term),
            )
        )
    query = query.order_by(DirectoryEntry.emergency.desc()).offset(offset).limit(limit)
    return [
        {
            "public_id": entry.public_id,
            "category": entry.category,
            "category_label": CATEGORY_LABELS.get(entry.category, "Servicio"),
            "name": entry.name,
            "latitude": entry.latitude,
            "longitude": entry.longitude,
            "address": entry.address_public,
            "maps_url": maps_url(entry.latitude, entry.longitude, entry.address_public),
            "phone": entry.phone_public,
            "operator": entry.operator,
            "emergency": entry.emergency,
            "attribution": entry.attribution,
            "url": entry.source_url,
        }
        for entry in query.all()
    ]


# Orden de prioridad de desastre para la muestra equilibrada (críticos primero).
MAP_CATEGORY_ORDER = [
    "hospital", "shelter", "water_point", "pharmacy", "clinic",
    "fire_station", "police", "fuel", "supplies", "community_center", "other",
]


def public_directory_balanced(q: str | None = None, per_category: int = 350) -> list[dict]:
    """Muestra equilibrada por categoría (round-robin) para que el mapa y la vista 'Todos'
    muestren VARIEDAD de iconos (hospital, refugio, agua, farmacia…), no un solo tipo, con
    el total acotado para el rendimiento del mapa."""
    buckets = [public_directory(q=q, category=category, limit=per_category) for category in MAP_CATEGORY_ORDER]
    rows: list[dict] = []
    for index in range(max((len(bucket) for bucket in buckets), default=0)):
        for bucket in buckets:
            if index < len(bucket):
                rows.append(bucket[index])
    return rows


def _lost_pet_dict(p) -> dict:
    maps_url = None
    if p.latitude is not None and p.longitude is not None:
        maps_url = f"https://www.google.com/maps?q={round(p.latitude, 2)},{round(p.longitude, 2)}"
    return {
        "public_id": p.public_id,
        "title": p.title,
        "species": p.species,
        "species_label": SPECIES_LABELS.get(p.species, "Mascota"),
        "breed": p.breed,
        "color": p.color,
        "summary": p.description_public,
        "zone": p.location_text,
        "last_seen_date": p.last_seen_date.isoformat() if p.last_seen_date else None,
        "photo_url": p.photo_url,
        "maps_url": maps_url,
    }


def _lost_pets_query(q: str | None = None):
    query = LostPetReport.query.filter_by(status=ReportStatus.APPROVED, is_public=True)
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(
                LostPetReport.title.ilike(term),
                LostPetReport.location_text.ilike(term),
                LostPetReport.breed.ilike(term),
                LostPetReport.color.ilike(term),
            )
        )
    return query


def public_lost_pets(q: str | None = None, limit: int = 60, offset: int = 0) -> list[dict]:
    """Mascotas desaparecidas publicadas (proyección pública; sin datos del dueño)."""
    rows = (
        _lost_pets_query(q)
        .order_by(LostPetReport.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_lost_pet_dict(p) for p in rows]


def count_lost_pets(q: str | None = None) -> int:
    return _lost_pets_query(q).count()


def _pet_record_dict(p) -> dict:
    return {
        "public_id": p.public_id,
        "title": p.name,
        "species": p.species,
        "species_label": SPECIES_LABELS.get(p.species, "Mascota"),
        "breed": p.breed,
        "color": p.color,
        "summary": p.description,
        "zone": p.last_seen_location,
        "last_seen_date": p.last_seen_date.isoformat() if p.last_seen_date else None,
        "photo_url": p.photo_url,
        "maps_url": None,
        "source_name": p.source_name,
        "source_url": p.source_url,
        "attribution": p.attribution,
        "source_date": p.source_date.isoformat() if p.source_date else None,
    }


def _pet_records_query(q: str | None = None):
    query = PetRecord.query
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(
                PetRecord.name.ilike(term),
                PetRecord.last_seen_location.ilike(term),
                PetRecord.breed.ilike(term),
                PetRecord.color.ilike(term),
            )
        )
    return query


def public_pet_records(q: str | None = None, limit: int = 60, offset: int = 0) -> list[dict]:
    """Mascotas desaparecidas publicadas por fuentes verificadas (ingesta atribuida)."""
    rows = (
        _pet_records_query(q)
        .order_by(PetRecord.source_date.desc().nullslast(), PetRecord.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_pet_record_dict(p) for p in rows]


def count_pet_records(q: str | None = None) -> int:
    return _pet_records_query(q).count()
