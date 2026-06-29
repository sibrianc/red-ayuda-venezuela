from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    VOLUNTEER = "volunteer"
    VIEWER = "viewer"


class ReportType(StrEnum):
    MISSING_PERSON = "missing_person"
    HELP_REQUEST = "help_request"
    RESOURCE_OFFER = "resource_offer"
    LOCATION_REPORT = "location_report"
    LOST_PET = "lost_pet"


class ReportStatus(StrEnum):
    PENDING = "pending"
    NEEDS_VERIFICATION = "needs_verification"
    APPROVED = "approved"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    FAMILY = "family"
    VOLUNTEER = "volunteer"
    ORGANIZATION = "organization"
    CONTRADICTORY = "contradictory"
    NEEDS_INFORMATION = "needs_information"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SourceChannel(StrEnum):
    WEB = "web"
    VOLUNTEER = "volunteer"
    PHONE = "phone"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    PAPER = "paper"
    SOCIAL = "social"
    ORGANIZATION = "organization"
    OTHER = "other"


class DataSourceKind(StrEnum):
    AUTHORITATIVE = "authoritative"
    HUMANITARIAN = "humanitarian"
    PARTNER = "partner"
    RESEARCH = "research"
    COMMUNITY = "community"
    REFERRAL = "referral"


class DataSourceAccess(StrEnum):
    API = "api"
    FEED = "feed"
    PUBLIC_DOCUMENT = "public_document"
    PARTNER_EXPORT = "partner_export"
    MANUAL_IMPORT = "manual_import"
    REFERRAL_ONLY = "referral_only"


class DataSourceStatus(StrEnum):
    PROPOSED = "proposed"
    EVALUATING = "evaluating"
    STAGING = "authorized_staging"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class DataClassification(StrEnum):
    PUBLIC_AGGREGATE = "P0"
    PUBLIC_SANITIZED = "P1"
    RESTRICTED_OPERATIONAL = "R1"
    SENSITIVE_PERSONAL = "R2"
    SYSTEM_SECRET = "S1"


class AbuseStatus(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    ACTION_TAKEN = "action_taken"


REPORT_TYPE_LABELS = {
    ReportType.MISSING_PERSON: "Persona sin contacto",
    ReportType.HELP_REQUEST: "Solicitud de ayuda",
    ReportType.RESOURCE_OFFER: "Oferta de recurso",
    ReportType.LOCATION_REPORT: "Zona afectada",
    ReportType.LOST_PET: "Mascota desaparecida",
}

SPECIES_LABELS = {
    "dog": "Perro",
    "cat": "Gato",
    "bird": "Ave",
    "other": "Otra",
}

STATUS_LABELS = {
    ReportStatus.PENDING: "Pendiente",
    ReportStatus.NEEDS_VERIFICATION: "Necesita verificación",
    ReportStatus.APPROVED: "Aprobado",
    ReportStatus.REJECTED: "Rechazado",
    ReportStatus.DUPLICATE: "Duplicado",
    ReportStatus.IN_PROGRESS: "En seguimiento",
    ReportStatus.RESOLVED: "Resuelto",
    ReportStatus.ARCHIVED: "Archivado",
}

PRIORITY_LABELS = {
    Priority.LOW: "Baja",
    Priority.MEDIUM: "Media",
    Priority.HIGH: "Alta",
    Priority.CRITICAL: "Crítica",
}

VERIFICATION_LABELS = {
    VerificationStatus.UNVERIFIED: "No verificado",
    VerificationStatus.FAMILY: "Verificado por familiar",
    VerificationStatus.VOLUNTEER: "Verificado por voluntario",
    VerificationStatus.ORGANIZATION: "Verificado por organización",
    VerificationStatus.CONTRADICTORY: "Información contradictoria",
    VerificationStatus.NEEDS_INFORMATION: "Necesita más datos",
}
