from datetime import date, datetime, timezone
from uuid import uuid4

from flask_login import UserMixin
from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.constants import (
    AbuseStatus,
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
