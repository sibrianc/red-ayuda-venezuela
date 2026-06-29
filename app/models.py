from datetime import date, datetime, timezone
from uuid import uuid4

from flask_login import UserMixin
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.constants import (
    AbuseStatus,
    DataClassification,
    DataSourceAccess,
    DataSourceKind,
    DataSourceStatus,
    Priority,
    ReportStatus,
    ReportType,
    SourceChannel,
    UserRole,
    VerificationStatus,
)
from app.extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def enum_column(enum_class, default):
    return mapped_column(
        Enum(
            enum_class,
            values_callable=lambda values: [item.value for item in values],
            native_enum=False,
            validate_strings=True,
        ),
        default=default,
        nullable=False,
        index=True,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ReportMixin(TimestampMixin):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4()), index=True
    )
    status: Mapped[ReportStatus] = enum_column(ReportStatus, ReportStatus.PENDING)
    verification_status: Mapped[VerificationStatus] = enum_column(
        VerificationStatus, VerificationStatus.UNVERIFIED
    )
    priority: Mapped[Priority] = enum_column(Priority, Priority.MEDIUM)
    source_channel: Mapped[SourceChannel] = enum_column(SourceChannel, SourceChannel.WEB)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    location_text: Mapped[str] = mapped_column(String(160), nullable=False)
    exact_address_private: Mapped[str | None] = mapped_column(String(240))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    location_precision: Mapped[str] = mapped_column(String(30), default="approximate", nullable=False)
    description_public: Mapped[str] = mapped_column(Text, nullable=False)
    description_private: Mapped[str | None] = mapped_column(Text)
    reporter_name_private: Mapped[str] = mapped_column(String(120), nullable=False)
    reporter_contact_private: Mapped[str] = mapped_column(String(160), nullable=False)


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = enum_column(UserRole, UserRole.REVIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    notes: Mapped[list["AdminNote"]] = relationship(back_populates="author")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class DataSource(TimestampMixin, db.Model):
    """Registro interno de una fuente; no almacena payloads ni credenciales."""

    __tablename__ = "data_sources"
    __table_args__ = (
        CheckConstraint(
            "frequency_minutes IS NULL OR frequency_minutes >= 1",
            name="ck_data_sources_frequency_positive",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(160), nullable=False)
    homepage_url: Mapped[str] = mapped_column(String(500), nullable=False)
    documentation_url: Mapped[str | None] = mapped_column(String(500))
    source_kind: Mapped[DataSourceKind] = enum_column(
        DataSourceKind, DataSourceKind.HUMANITARIAN
    )
    access_method: Mapped[DataSourceAccess] = enum_column(
        DataSourceAccess, DataSourceAccess.PUBLIC_DOCUMENT
    )
    authorization_status: Mapped[DataSourceStatus] = enum_column(
        DataSourceStatus, DataSourceStatus.PROPOSED
    )
    license_or_permission: Mapped[str | None] = mapped_column(Text)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    categories: Mapped[str] = mapped_column(Text, nullable=False)
    contains_personal_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    maximum_data_class: Mapped[DataClassification] = enum_column(
        DataClassification, DataClassification.PUBLIC_AGGREGATE
    )
    frequency_minutes: Mapped[int | None] = mapped_column(Integer)
    rate_limit_notes: Mapped[str | None] = mapped_column(String(500))
    retention_policy: Mapped[str] = mapped_column(Text, nullable=False)
    attribution: Mapped[str | None] = mapped_column(Text)
    schema_version: Mapped[str | None] = mapped_column(String(80))
    secret_env_var: Mapped[str | None] = mapped_column(String(120))
    internal_owner: Mapped[str] = mapped_column(String(160), nullable=False)
    authorization_notes: Mapped[str | None] = mapped_column(Text)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourceRecord(TimestampMixin, db.Model):
    """Copia inmutable y trazable de un ítem de una fuente externa.

    Es la capa de procedencia: guarda el payload original sin normalizar para
    auditoría. No es el producto público. La idempotencia se apoya en
    (source_slug, external_id) y en content_hash para detectar cambios.
    """

    __tablename__ = "source_records"
    __table_args__ = (
        UniqueConstraint("source_slug", "external_id", name="uq_source_records_origin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_slug: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    detail_url: Mapped[str | None] = mapped_column(String(500))
    schema_version: Mapped[str | None] = mapped_column(String(80))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)


class IngestedEvent(TimestampMixin, db.Model):
    """Evento autoritativo normalizado, limpio y deduplicado (objeto canónico Event).

    Realiza el objeto `Event` del modelo de datos para fuentes públicas como USGS.
    Almacena el hecho ya saneado y filtrable. La exposición pública es un paso
    aparte con su propia puerta; por defecto NO se publica automáticamente.
    """

    __tablename__ = "ingested_events"
    __table_args__ = (
        UniqueConstraint("source_slug", "external_id", name="uq_ingested_events_origin"),
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="ck_ingested_events_latitude_range",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_ingested_events_longitude_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4()), index=True
    )
    source_slug: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, default="earthquake", index=True)
    hazard_code: Mapped[str | None] = mapped_column(String(8), index=True)
    title: Mapped[str | None] = mapped_column(String(240))
    magnitude: Mapped[float | None] = mapped_column(Float, index=True)
    severity_value: Mapped[float | None] = mapped_column(Float)
    severity_text: Mapped[str | None] = mapped_column(String(240))
    country: Mapped[str | None] = mapped_column(String(120), index=True)
    place: Mapped[str | None] = mapped_column(String(240))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    depth_km: Mapped[float | None] = mapped_column(Float)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    alert_level: Mapped[str | None] = mapped_column(String(20), index=True)
    tsunami: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    felt_reports: Mapped[int | None] = mapped_column(Integer)
    significance: Mapped[int | None] = mapped_column(Integer, index=True)
    in_region: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    detail_url: Mapped[str | None] = mapped_column(String(500))
    attribution: Mapped[str | None] = mapped_column(String(240))


class DirectoryEntry(TimestampMixin, db.Model):
    """Servicio u organización del directorio público (objeto canónico DirectoryEntry).

    Hospitales, refugios, clínicas, estaciones de bomberos, puntos de agua, etc.
    Son instalaciones PÚBLICAS: nombre, dirección y contacto son información pública
    (a diferencia de los reportes de personas). Inspirado en OCHA 5W y EDXL-HAVE.
    """

    __tablename__ = "directory_entries"
    __table_args__ = (
        UniqueConstraint("source_slug", "external_id", name="uq_directory_entries_origin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4()), index=True
    )
    source_slug: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    address_public: Mapped[str | None] = mapped_column(String(300))
    phone_public: Mapped[str | None] = mapped_column(String(120))
    operator: Mapped[str | None] = mapped_column(String(200))
    emergency: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    capacity_text: Mapped[str | None] = mapped_column(String(120))
    service_status: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False, index=True)
    in_region: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(String(500))
    attribution: Mapped[str | None] = mapped_column(String(240))


class PersonRecord(TimestampMixin, db.Model):
    """Persona publicada para búsqueda/reunificación (registro tipo Person Finder/PFIF).

    Agrega información YA publicada (PFIF, listas oficiales) para que familias y
    rescatistas localicen personas: nombre, edad y última ubicación. Es pública por
    su propósito (encontrar a la persona), con atribución de la fuente. Los MENORES
    se marcan y se excluyen de las vistas públicas por protección.
    """

    __tablename__ = "person_records"
    __table_args__ = (
        UniqueConstraint("source_slug", "external_id", name="uq_person_records_origin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4()), index=True
    )
    source_slug: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(240), nullable=False)
    given_name: Mapped[str | None] = mapped_column(String(120))
    family_name: Mapped[str | None] = mapped_column(String(120))
    age: Mapped[int | None] = mapped_column(Integer)
    sex: Mapped[str | None] = mapped_column(String(20))
    last_known_location: Mapped[str | None] = mapped_column(String(300))
    home_location: Mapped[str | None] = mapped_column(String(300))
    person_status: Mapped[str] = mapped_column(String(20), default="missing", nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    source_name: Mapped[str | None] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_minor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    attribution: Mapped[str | None] = mapped_column(String(240))


class SituationMetric(TimestampMixin, db.Model):
    """Cifra agregada de situación (objeto canónico OperationalFact).

    Titulares de magnitud: desaparecidos, fallecidos, heridos, rescatados, etc.
    Siempre con fuente, fecha y estado de verificación; nunca se presenta una cifra
    de una sola fuente sin verificar como hecho confirmado.
    """

    __tablename__ = "situation_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_key: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(40))
    source_name: Mapped[str | None] = mapped_column(String(200))
    attribution: Mapped[str | None] = mapped_column(String(240))
    verification_status: Mapped[str] = mapped_column(String(20), default="reported", nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(String(500))
    as_of: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class Incident(TimestampMixin, db.Model):
    """Incidente de prioridad situacional (objeto operativo del mapa vivo).

    Representa una SITUACIÓN en un lugar: edificio colapsado, personas atrapadas,
    incendio, vía bloqueada, etc. Es información situacional y pública (el lugar),
    NO un registro de personas con nombre: los casos individuales de personas
    desaparecidas o menores siguen su flujo privado y de revisión humana.
    """

    __tablename__ = "incidents"
    __table_args__ = (
        UniqueConstraint("source_slug", "external_id", name="uq_incidents_origin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4()), index=True
    )
    source_slug: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), default="high", nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    address_public: Mapped[str | None] = mapped_column(String(300))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="reported", nullable=False, index=True)
    situation_note: Mapped[str | None] = mapped_column(String(500))
    source_name: Mapped[str | None] = mapped_column(String(160))
    attribution: Mapped[str | None] = mapped_column(String(240))
    in_region: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class CommunicationSignal(TimestampMixin, db.Model):
    """Zona sin comunicación reportada (alerta de posibles víctimas incomunicadas).

    Es situacional, no contiene datos personales públicos (solo la zona). Sirve para
    que rescatistas prioricen evaluación donde la gente no puede comunicarse. Empieza
    como `advisory` (sin verificar); una persona la corrobora o resuelve. El contacto
    de quien reporta es privado. Puede provenir de la comunidad o de señales técnicas
    de conectividad (p. ej. IODA) en una fase futura.
    """

    __tablename__ = "communication_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid4()), index=True
    )
    zone_label: Mapped[str] = mapped_column(String(160), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="advisory", nullable=False, index=True)
    public_note: Mapped[str | None] = mapped_column(Text)
    reporter_contact_private: Mapped[str | None] = mapped_column(String(160))
    source: Mapped[str] = mapped_column(String(40), default="community", nullable=False, index=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MissingPersonReport(ReportMixin, db.Model):
    __tablename__ = "missing_person_reports"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String(40))
    last_contact_date: Mapped[date | None] = mapped_column(Date)
    relationship_to_person_private: Mapped[str | None] = mapped_column(String(100))
    medical_information_private: Mapped[str | None] = mapped_column(Text)
    involves_minor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class HelpRequest(ReportMixin, db.Model):
    __tablename__ = "help_requests"

    title: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    request_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    people_affected: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    vulnerable_people_present: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    medical_need: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    water_need: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    food_need: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    shelter_need: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transport_need: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    medical_information_private: Mapped[str | None] = mapped_column(Text)


class ResourceOffer(ReportMixin, db.Model):
    __tablename__ = "resource_offers"

    title: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    capacity: Mapped[str | None] = mapped_column(String(120))
    availability: Mapped[str | None] = mapped_column(String(120))
    public_contact_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class LocationReport(ReportMixin, db.Model):
    __tablename__ = "location_reports"

    title: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    damage_level: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    needs_water: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    needs_food: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    needs_medical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    needs_shelter: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    needs_transport: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AdminNote(db.Model):
    __tablename__ = "admin_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_type: Mapped[ReportType] = enum_column(ReportType, ReportType.HELP_REQUEST)
    report_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    author: Mapped[User] = relationship(back_populates="notes")


class ReportStatusHistory(db.Model):
    __tablename__ = "report_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_type: Mapped[ReportType] = enum_column(ReportType, ReportType.HELP_REQUEST)
    report_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    old_status: Mapped[ReportStatus] = enum_column(ReportStatus, ReportStatus.PENDING)
    new_status: Mapped[ReportStatus] = enum_column(ReportStatus, ReportStatus.PENDING)
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class DuplicateCandidate(db.Model):
    __tablename__ = "duplicate_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_type: Mapped[ReportType] = enum_column(ReportType, ReportType.HELP_REQUEST)
    report_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    possible_duplicate_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AbuseReport(db.Model):
    __tablename__ = "abuse_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_type: Mapped[ReportType] = enum_column(ReportType, ReportType.HELP_REQUEST)
    report_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[str | None] = mapped_column(String(1000))
    submitted_by_contact_private: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[AbuseStatus] = enum_column(AbuseStatus, AbuseStatus.PENDING)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


REPORT_MODELS = {
    ReportType.MISSING_PERSON: MissingPersonReport,
    ReportType.HELP_REQUEST: HelpRequest,
    ReportType.RESOURCE_OFFER: ResourceOffer,
    ReportType.LOCATION_REPORT: LocationReport,
}
