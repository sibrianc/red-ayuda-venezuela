"""Pipeline genérico de ingesta: limpieza, filtros, deduplicación y persistencia.

Recibe `ParsedEvent` de cualquier conector y los guarda como `SourceRecord`
(procedencia cruda) + `IngestedEvent` (hecho normalizado). Es idempotente:
volver a correr la misma entrada no crea duplicados; solo actualiza lo que cambió.

No publica nada automáticamente: `IngestedEvent` es una capa interna saneada.
La exposición pública es un paso aparte con su propia puerta de revisión.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import func

from app.extensions import db
from app.ingestion.connectors import (
    ParsedDirectoryEntry,
    ParsedEvent,
    in_venezuela_region,
)
from app.ingestion.normalize import match_key
from app.ingestion.incidents import ParsedIncident
from app.ingestion.ioda import IODA_SOURCE, ParsedCommsZone
from app.ingestion.pets import ParsedPet
from app.ingestion.pfif import ParsedPerson
from app.ingestion.recognitions import ParsedRecognition
from app.models import (
    CommunicationSignal,
    DirectoryEntry,
    Incident,
    IngestedEvent,
    PersonRecord,
    PetRecord,
    Recognition,
    SourceRecord,
)


@dataclass
class IngestStats:
    """Resumen legible de una corrida de ingesta."""

    received: int = 0
    filtered_out: int = 0
    new: int = 0
    updated: int = 0
    unchanged: int = 0
    in_region: int = 0
    invalid: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def kept(self) -> int:
        return self.new + self.updated + self.unchanged

    def as_dict(self) -> dict:
        return {
            "recibidos": self.received,
            "descartados_por_filtro": self.filtered_out,
            "invalidos": self.invalid,
            "nuevos": self.new,
            "actualizados": self.updated,
            "sin_cambios": self.unchanged,
            "en_region_venezuela": self.in_region,
        }


def _passes_filters(
    event: ParsedEvent, *, min_magnitude, region_only, is_region, event_types, since
) -> bool:
    # Por defecto el proyecto se enfoca en EL terremoto: solo sismos, en Venezuela y
    # recientes. Cualquier otra amenaza o evento fuera de la ventana se descarta.
    if event_types is not None and event.event_type not in event_types:
        return False
    if min_magnitude is not None:
        if event.magnitude is None or event.magnitude < min_magnitude:
            return False
    if region_only and not is_region:
        return False
    if since is not None:
        if event.occurred_at is None or event.occurred_at < since:
            return False
    return True


def _apply_event_fields(target: IngestedEvent, event: ParsedEvent, is_region: bool) -> None:
    target.source_slug = event.source_slug
    target.external_id = event.external_id
    target.content_hash = event.content_hash
    target.event_type = event.event_type
    target.hazard_code = event.hazard_code
    target.title = event.title
    target.magnitude = event.magnitude
    target.severity_value = event.severity_value
    target.severity_text = event.severity_text
    target.country = event.country
    target.place = event.place
    target.latitude = event.latitude
    target.longitude = event.longitude
    target.depth_km = event.depth_km
    target.occurred_at = event.occurred_at
    target.alert_level = event.alert_level
    target.tsunami = event.tsunami
    target.felt_reports = event.felt_reports
    target.significance = event.significance
    target.in_region = is_region
    target.detail_url = event.detail_url
    target.attribution = event.attribution


def ingest_events(
    events: list[ParsedEvent],
    *,
    min_magnitude: float | None = None,
    region_only: bool = False,
    event_types: set[str] | None = None,
    since: datetime | None = None,
    commit: bool = True,
) -> IngestStats:
    """Limpia, filtra, deduplica y persiste una lista de eventos parseados.

    Filtros (todos opcionales): `event_types` (p. ej. {"earthquake"}), `min_magnitude`,
    `region_only` (recuadro de Venezuela) y `since` (descarta eventos anteriores a esa
    fecha). El CLI usa estos filtros para enfocarse en el terremoto y sus réplicas.
    """
    stats = IngestStats(received=len(events))

    # Deduplica dentro del mismo lote por (source_slug, external_id): si un feed
    # repite un id, se queda el último visto antes de tocar la base.
    deduped: dict[tuple[str, str], ParsedEvent] = {}
    for event in events:
        if not event.external_id:
            stats.invalid += 1
            continue
        deduped[(event.source_slug, event.external_id)] = event

    for (source_slug, external_id), event in deduped.items():
        is_region = in_venezuela_region(event.latitude, event.longitude)
        if not _passes_filters(
            event,
            min_magnitude=min_magnitude,
            region_only=region_only,
            is_region=is_region,
            event_types=event_types,
            since=since,
        ):
            stats.filtered_out += 1
            continue

        record = (
            db.session.query(SourceRecord)
            .filter_by(source_slug=source_slug, external_id=external_id)
            .one_or_none()
        )
        ingested = (
            db.session.query(IngestedEvent)
            .filter_by(source_slug=source_slug, external_id=external_id)
            .one_or_none()
        )

        if record is not None and record.content_hash == event.content_hash and ingested is not None:
            stats.unchanged += 1
            if is_region:
                stats.in_region += 1
            continue

        if record is None:
            record = SourceRecord(source_slug=source_slug, external_id=external_id)
            db.session.add(record)
        record.content_hash = event.content_hash
        record.detail_url = event.detail_url
        record.schema_version = event.schema_version
        record.raw_payload = event.raw_payload

        if ingested is None:
            ingested = IngestedEvent()
            db.session.add(ingested)
            stats.new += 1
        else:
            stats.updated += 1
        _apply_event_fields(ingested, event, is_region)

        if is_region:
            stats.in_region += 1

    if commit:
        db.session.commit()
    return stats


def event_overview() -> dict:
    """Conteos agregados para ver el volumen real ingerido (no es vista pública)."""
    total = db.session.query(func.count(IngestedEvent.id)).scalar() or 0
    in_region = (
        db.session.query(func.count(IngestedEvent.id))
        .filter(IngestedEvent.in_region.is_(True))
        .scalar()
        or 0
    )
    by_band: dict[str, int] = {}
    for label, low, high in (
        ("<2.5", -100, 2.5),
        ("2.5–3.9", 2.5, 4.0),
        ("4.0–4.9", 4.0, 5.0),
        ("5.0–5.9", 5.0, 6.0),
        ("6.0+", 6.0, 100),
    ):
        count = (
            db.session.query(func.count(IngestedEvent.id))
            .filter(
                IngestedEvent.magnitude.isnot(None),
                IngestedEvent.magnitude >= low,
                IngestedEvent.magnitude < high,
            )
            .scalar()
            or 0
        )
        by_band[label] = count
    by_type = {
        event_type: count
        for event_type, count in (
            db.session.query(IngestedEvent.event_type, func.count(IngestedEvent.id))
            .group_by(IngestedEvent.event_type)
            .order_by(func.count(IngestedEvent.id).desc())
            .all()
        )
    }
    latest = (
        db.session.query(func.max(IngestedEvent.occurred_at)).scalar()
    )
    return {
        "total": total,
        "en_region": in_region,
        "por_tipo": by_type,
        "por_magnitud": by_band,
        "evento_mas_reciente": latest,
    }


def _apply_directory_fields(target: DirectoryEntry, entry: ParsedDirectoryEntry, is_region: bool) -> None:
    target.source_slug = entry.source_slug
    target.external_id = entry.external_id
    target.content_hash = entry.content_hash
    target.category = entry.category
    target.name = entry.name
    target.latitude = entry.latitude
    target.longitude = entry.longitude
    target.address_public = entry.address_public
    target.phone_public = entry.phone_public
    target.operator = entry.operator
    target.emergency = entry.emergency
    target.in_region = is_region
    target.source_url = entry.source_url
    target.attribution = entry.attribution


def ingest_directory(
    entries: list[ParsedDirectoryEntry], *, region_only: bool = False, commit: bool = True
) -> IngestStats:
    """Limpia, deduplica y persiste entradas de directorio (idempotente)."""
    stats = IngestStats(received=len(entries))

    deduped: dict[tuple[str, str], ParsedDirectoryEntry] = {}
    for entry in entries:
        if not entry.external_id:
            stats.invalid += 1
            continue
        deduped[(entry.source_slug, entry.external_id)] = entry

    for (source_slug, external_id), entry in deduped.items():
        is_region = in_venezuela_region(entry.latitude, entry.longitude)
        if region_only and not is_region:
            stats.filtered_out += 1
            continue

        existing = (
            db.session.query(DirectoryEntry)
            .filter_by(source_slug=source_slug, external_id=external_id)
            .one_or_none()
        )
        if existing is not None and existing.content_hash == entry.content_hash:
            stats.unchanged += 1
            if is_region:
                stats.in_region += 1
            continue

        if existing is None:
            existing = DirectoryEntry(source_slug=source_slug, external_id=external_id)
            db.session.add(existing)
            stats.new += 1
        else:
            stats.updated += 1
        _apply_directory_fields(existing, entry, is_region)
        if is_region:
            stats.in_region += 1

    if commit:
        db.session.commit()
    return stats


def _apply_incident_fields(target: Incident, incident: ParsedIncident) -> None:
    target.source_slug = incident.source_slug
    target.external_id = incident.external_id
    target.content_hash = incident.content_hash
    target.category = incident.category
    target.severity = incident.severity
    target.label = incident.label
    target.address_public = incident.address_public
    target.latitude = incident.latitude
    target.longitude = incident.longitude
    target.status = incident.status
    target.verification_status = incident.verification_status
    target.situation_note = incident.situation_note
    target.source_name = incident.source_name
    target.source_url = incident.source_url
    target.source_date = incident.source_date
    target.attribution = incident.attribution
    target.confidence = incident.confidence
    target.location_precision = incident.location_precision
    target.area_radius_m = incident.area_radius_m
    target.people_trapped_status = incident.people_trapped_status
    target.people_trapped_count = incident.people_trapped_count
    target.in_region = bool(
        incident.latitude is not None
        and incident.longitude is not None
        and in_venezuela_region(incident.latitude, incident.longitude)
    )
    target.occurred_at = incident.source_date


def ingest_incidents(incidents: list[ParsedIncident], *, commit: bool = True) -> IngestStats:
    """Persiste incidentes trazables, idempotentes por fuente e identificador."""
    stats = IngestStats(received=len(incidents))
    deduped: dict[tuple[str, str], ParsedIncident] = {}
    for incident in incidents:
        if not incident.external_id:
            stats.invalid += 1
            continue
        deduped[(incident.source_slug, incident.external_id)] = incident

    for (source_slug, external_id), incident in deduped.items():
        existing = (
            db.session.query(Incident)
            .filter_by(source_slug=source_slug, external_id=external_id)
            .one_or_none()
        )
        if existing is not None and existing.content_hash == incident.content_hash:
            stats.unchanged += 1
            if existing.in_region:
                stats.in_region += 1
            continue
        if existing is None:
            existing = Incident(source_slug=source_slug, external_id=external_id)
            db.session.add(existing)
            stats.new += 1
        else:
            stats.updated += 1
        _apply_incident_fields(existing, incident)
        if existing.in_region:
            stats.in_region += 1

    if commit:
        db.session.commit()
    return stats


def _apply_person_fields(target: PersonRecord, person: ParsedPerson) -> None:
    target.content_hash = person.content_hash
    target.full_name = person.full_name
    target.given_name = person.given_name
    target.family_name = person.family_name
    target.age = person.age
    target.sex = person.sex
    target.last_known_location = person.last_known_location
    target.home_location = person.home_location
    target.person_status = person.person_status
    target.description = person.description
    target.source_name = person.source_name
    target.source_url = person.source_url
    target.source_date = person.source_date
    target.is_minor = person.is_minor
    target.attribution = person.attribution
    target.match_key = match_key(person.full_name) or None


def ingest_persons(people: list[ParsedPerson], *, commit: bool = True) -> IngestStats:
    """Limpia, deduplica y persiste personas PFIF (idempotente por origen)."""
    stats = IngestStats(received=len(people))

    deduped: dict[tuple[str, str], ParsedPerson] = {}
    for person in people:
        if not person.external_id:
            stats.invalid += 1
            continue
        deduped[(person.source_slug, person.external_id)] = person

    for (source_slug, external_id), person in deduped.items():
        existing = (
            db.session.query(PersonRecord)
            .filter_by(source_slug=source_slug, external_id=external_id)
            .one_or_none()
        )
        if existing is not None and existing.content_hash == person.content_hash:
            stats.unchanged += 1
            continue
        if existing is None:
            existing = PersonRecord(source_slug=source_slug, external_id=external_id)
            db.session.add(existing)
            stats.new += 1
        else:
            stats.updated += 1
        _apply_person_fields(existing, person)

    if commit:
        db.session.commit()
    return stats


def _apply_pet_fields(target: PetRecord, pet: ParsedPet) -> None:
    target.content_hash = pet.content_hash
    target.name = pet.name
    target.species = pet.species
    target.breed = pet.breed
    target.color = pet.color
    target.last_seen_location = pet.last_seen_location
    target.last_seen_date = pet.last_seen_date
    target.photo_url = pet.photo_url
    target.description = pet.description
    target.source_name = pet.source_name
    target.source_url = pet.source_url
    target.source_date = pet.source_date
    target.attribution = pet.attribution


def ingest_pets(pets: list[ParsedPet], *, commit: bool = True) -> IngestStats:
    """Limpia, deduplica y persiste mascotas de fuentes verificadas (idempotente por origen)."""
    stats = IngestStats(received=len(pets))

    deduped: dict[tuple[str, str], ParsedPet] = {}
    for pet in pets:
        if not pet.external_id:
            stats.invalid += 1
            continue
        deduped[(pet.source_slug, pet.external_id)] = pet

    for (source_slug, external_id), pet in deduped.items():
        existing = (
            db.session.query(PetRecord)
            .filter_by(source_slug=source_slug, external_id=external_id)
            .one_or_none()
        )
        if existing is not None and existing.content_hash == pet.content_hash:
            stats.unchanged += 1
            continue
        if existing is None:
            existing = PetRecord(source_slug=source_slug, external_id=external_id)
            db.session.add(existing)
            stats.new += 1
        else:
            stats.updated += 1
        _apply_pet_fields(existing, pet)

    if commit:
        db.session.commit()
    return stats


def _apply_recognition_fields(target: Recognition, rec: ParsedRecognition) -> None:
    target.content_hash = rec.content_hash
    target.kind = rec.kind
    target.name = rec.name
    target.org = rec.org
    target.country = rec.country
    target.role = rec.role
    target.description = rec.description
    target.photo_url = rec.photo_url
    target.source_name = rec.source_name
    target.source_url = rec.source_url
    target.source_date = rec.source_date
    target.attribution = rec.attribution


def ingest_recognitions(recognitions: list[ParsedRecognition], *, commit: bool = True) -> IngestStats:
    """Limpia, deduplica y persiste reconocimientos de fuentes oficiales (idempotente por origen)."""
    stats = IngestStats(received=len(recognitions))

    deduped: dict[tuple[str, str], ParsedRecognition] = {}
    for rec in recognitions:
        if not rec.external_id:
            stats.invalid += 1
            continue
        deduped[(rec.source_slug, rec.external_id)] = rec

    for (source_slug, external_id), rec in deduped.items():
        existing = (
            db.session.query(Recognition)
            .filter_by(source_slug=source_slug, external_id=external_id)
            .one_or_none()
        )
        if existing is not None and existing.content_hash == rec.content_hash:
            stats.unchanged += 1
            continue
        if existing is None:
            existing = Recognition(source_slug=source_slug, external_id=external_id)
            db.session.add(existing)
            stats.new += 1
        else:
            stats.updated += 1
        _apply_recognition_fields(existing, rec)

    if commit:
        db.session.commit()
    return stats


def recompute_corroboration() -> int:
    """Recalcula la verificación cruzada: corroboration = nº de FUENTES distintas que
    comparten cada match_key. Una persona reportada por 2+ plataformas sube de confianza.
    Devuelve cuántas claves quedaron corroboradas (>= 2 fuentes)."""
    db.session.query(PersonRecord).update({PersonRecord.corroboration: 1}, synchronize_session=False)
    rows = (
        db.session.query(
            PersonRecord.match_key, func.count(func.distinct(PersonRecord.source_slug))
        )
        .filter(PersonRecord.match_key.isnot(None), PersonRecord.match_key != "")
        .group_by(PersonRecord.match_key)
        .having(func.count(func.distinct(PersonRecord.source_slug)) > 1)
        .all()
    )
    for key, sources in rows:
        db.session.query(PersonRecord).filter(PersonRecord.match_key == key).update(
            {PersonRecord.corroboration: sources}, synchronize_session=False
        )
    db.session.commit()
    return len(rows)


def directory_overview() -> dict:
    """Conteos del directorio por categoría (para ver el volumen real)."""
    total = db.session.query(func.count(DirectoryEntry.id)).scalar() or 0
    by_category = {
        category: count
        for category, count in (
            db.session.query(DirectoryEntry.category, func.count(DirectoryEntry.id))
            .group_by(DirectoryEntry.category)
            .order_by(func.count(DirectoryEntry.id).desc())
            .all()
        )
    }
    return {"total": total, "por_categoria": by_category}


def ingest_comms_zones(zones: list[ParsedCommsZone], *, commit: bool = True) -> IngestStats:
    """Upsert idempotente de "zonas sin comunicación" desde señales técnicas (IODA).

    Deduplica por (source, zone_label). Las regiones IODA que ya no aparecen como activas
    se marcan 'resolved' para que dejen de mostrarse: auto-limpieza en cada corrida (apta
    para el cron de 2 h, sin acumular zonas viejas).
    """
    stats = IngestStats(received=len(zones))

    deduped: dict[str, ParsedCommsZone] = {}
    for zone in zones:
        if not zone.zone_label:
            stats.invalid += 1
            continue
        deduped[zone.zone_label] = zone

    active_labels = set(deduped)
    for label, zone in deduped.items():
        existing = (
            db.session.query(CommunicationSignal)
            .filter_by(source=IODA_SOURCE, zone_label=label)
            .one_or_none()
        )
        if existing is None:
            existing = CommunicationSignal(source=IODA_SOURCE, zone_label=label)
            db.session.add(existing)
            stats.new += 1
        else:
            stats.updated += 1
        existing.status = "advisory"
        existing.latitude = zone.latitude
        existing.longitude = zone.longitude
        existing.public_note = zone.public_note
        existing.reported_at = datetime.now(timezone.utc)
        stats.in_region += 1

    # Auto-limpieza: regiones IODA previas que ya no están activas -> resolved.
    previous = (
        db.session.query(CommunicationSignal)
        .filter(
            CommunicationSignal.source == IODA_SOURCE,
            CommunicationSignal.status != "resolved",
        )
        .all()
    )
    for signal in previous:
        if signal.zone_label not in active_labels:
            signal.status = "resolved"

    if commit:
        db.session.commit()
    return stats
