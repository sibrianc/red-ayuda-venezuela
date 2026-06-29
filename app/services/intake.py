"""Compuerta de ingreso automática para reportes ciudadanos.

Permite operar SIN revisión humana sin dejar a nadie fuera: cada reporte pasa
por una limpieza y verificación automática. Si está limpio y completo se publica
de inmediato (proyección pública, nunca datos privados). Si algo no pasa los
controles (datos incompletos, posible spam, posible duplicado o involucra a un
menor) NO se descarta: se resguarda en cola para cuando una persona se sume al
proyecto. La revisión humana sigue disponible activando AUTO_PUBLISH=off.
"""

import re
from dataclasses import dataclass, field

from flask import current_app

from app.constants import ReportStatus, ReportType
from app.services.automation import find_duplicate_candidates, missing_required_information

MIN_PUBLIC_DESCRIPTION = 12  # caracteres mínimos tras limpiar
DUPLICATE_AUTO_HOLD = 0.9  # solo retiene duplicados de muy alta confianza

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MULTISPACE = re.compile(r"[ \t]{2,}")
_REPEAT_SPAM = re.compile(r"(.)\1{9,}")
_SPAM_PATTERNS = [
    re.compile(r"https?://", re.I),
    re.compile(r"\bwww\.", re.I),
    re.compile(r"\b(viagra|casino|crypto|bitcoin|forex|porn|sexo|loan|prestamo express)\b", re.I),
]

# Campos de texto de cara al público que se limpian automáticamente.
_PUBLIC_TEXT_FIELDS = (
    "title",
    "description_public",
    "location_text",
    "first_name",
    "last_name",
    "capacity",
    "availability",
    "public_note",
)


@dataclass
class IntakeDecision:
    status: ReportStatus
    is_public: bool
    held_for_review: bool
    reasons: list[str] = field(default_factory=list)


def clean_text(value: str | None) -> str | None:
    """Quita caracteres de control y colapsa espacios; nunca altera el sentido."""
    if not value:
        return value
    value = _CONTROL_CHARS.sub("", value)
    value = _MULTISPACE.sub(" ", value).strip()
    return value or None


def sanitize_report(report) -> None:
    """Limpieza automática de los campos públicos del reporte (in place)."""
    for field_name in _PUBLIC_TEXT_FIELDS:
        if hasattr(report, field_name):
            setattr(report, field_name, clean_text(getattr(report, field_name)))


def _looks_like_spam(report) -> bool:
    text = " ".join(
        filter(
            None,
            [
                getattr(report, "title", None),
                getattr(report, "description_public", None),
                getattr(report, "location_text", None),
            ],
        )
    )
    if _REPEAT_SPAM.search(text):
        return True
    return any(pattern.search(text) for pattern in _SPAM_PATTERNS)


def evaluate_intake(report_type: ReportType, report) -> IntakeDecision:
    """Limpia y decide si el reporte se publica solo o se resguarda para revisión."""
    sanitize_report(report)

    if not current_app.config.get("AUTO_PUBLISH", True):
        return IntakeDecision(
            ReportStatus.PENDING,
            False,
            True,
            ["Revisión humana activada (AUTO_PUBLISH=off): el reporte espera aprobación."],
        )

    # Los menores nunca se publican automáticamente (módulo de protección).
    if report_type is ReportType.MISSING_PERSON and getattr(report, "involves_minor", False):
        return IntakeDecision(
            ReportStatus.NEEDS_VERIFICATION,
            False,
            True,
            ["Involucra a un menor: se resguarda y nunca se publica de forma automática."],
        )

    missing = missing_required_information(report_type, report)
    if missing:
        return IntakeDecision(
            ReportStatus.NEEDS_VERIFICATION,
            False,
            True,
            ["Faltan datos para publicar: " + ", ".join(missing) + "."],
        )

    if len(report.description_public or "") < MIN_PUBLIC_DESCRIPTION:
        return IntakeDecision(
            ReportStatus.NEEDS_VERIFICATION,
            False,
            True,
            ["Descripción demasiado breve para publicar automáticamente."],
        )

    if _looks_like_spam(report):
        return IntakeDecision(
            ReportStatus.NEEDS_VERIFICATION,
            False,
            True,
            ["Posible spam o enlace no verificado: se resguarda para revisión."],
        )

    if find_duplicate_candidates(report_type, report, threshold=DUPLICATE_AUTO_HOLD):
        return IntakeDecision(
            ReportStatus.DUPLICATE,
            False,
            True,
            ["Coincide casi por completo con un reporte existente: se resguarda como posible duplicado."],
        )

    return IntakeDecision(
        ReportStatus.APPROVED,
        True,
        False,
        ["Publicado automáticamente tras limpieza y verificación básica (sin datos privados)."],
    )
