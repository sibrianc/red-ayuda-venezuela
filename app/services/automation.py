import re
import unicodedata
from difflib import SequenceMatcher

from app.constants import Priority, ReportType
from app.models import DuplicateCandidate, HelpRequest, REPORT_MODELS, ResourceOffer


CRITICAL_TERMS = {
    "atrapado",
    "atrapada",
    "hemorragia",
    "inconsciente",
    "derrumbe",
    "oxigeno",
    "peligro inmediato",
}
HIGH_TERMS = {"herido", "herida", "nino", "nina", "adulto mayor", "discapacidad", "medicamento"}


def normalize(value: str | None) -> str:
    value = value or ""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", value.lower())).strip()


def suggest_priority(report_type: ReportType, report) -> tuple[Priority, list[str]]:
    text = normalize(
        " ".join(
            filter(
                None,
                [
                    getattr(report, "title", None),
                    getattr(report, "description_public", None),
                    getattr(report, "description_private", None),
                ],
            )
        )
    )
    reasons: list[str] = []
    if any(term in text for term in CRITICAL_TERMS):
        reasons.append("Contiene un indicador explícito de riesgo inmediato.")
        return Priority.CRITICAL, reasons
    if getattr(report, "medical_need", False):
        reasons.append("La solicitud indica necesidad médica.")
    if getattr(report, "vulnerable_people_present", False) or getattr(report, "involves_minor", False):
        reasons.append("Incluye personas vulnerables.")
    if any(term in text for term in HIGH_TERMS):
        reasons.append("Contiene un indicador de vulnerabilidad o lesión.")
    if reasons:
        return Priority.HIGH, reasons
    if report_type is ReportType.RESOURCE_OFFER:
        return Priority.LOW, ["Las ofertas se ordenan después de necesidades activas."]
    return Priority.MEDIUM, ["No se detectaron indicadores estructurados de prioridad alta."]


def find_duplicate_candidates(report_type: ReportType, report, threshold: float = 0.72):
    model = REPORT_MODELS[report_type]
    current_title = normalize(
        f"{getattr(report, 'first_name', '')} {getattr(report, 'last_name', '')} "
        f"{getattr(report, 'title', '')}"
    )
    current_location = normalize(report.location_text)
    candidates = []
    for other in model.query.filter(model.id != report.id).all():
        other_title = normalize(
            f"{getattr(other, 'first_name', '')} {getattr(other, 'last_name', '')} "
            f"{getattr(other, 'title', '')}"
        )
        title_score = SequenceMatcher(None, current_title, other_title).ratio()
        location_score = SequenceMatcher(None, current_location, normalize(other.location_text)).ratio()
        score = round((title_score * 0.7) + (location_score * 0.3), 3)
        if score >= threshold:
            candidates.append(
                DuplicateCandidate(
                    report_type=report_type,
                    report_id=report.id,
                    possible_duplicate_id=other.id,
                    score=score,
                    reason="Coincidencia de título/nombre y zona; requiere revisión humana.",
                )
            )
    return candidates


def suggest_resource_matches(help_request: HelpRequest) -> list[dict]:
    matches = []
    for resource in ResourceOffer.query.filter_by(is_public=True).all():
        type_score = SequenceMatcher(
            None, normalize(help_request.request_type), normalize(resource.resource_type)
        ).ratio()
        zone_score = SequenceMatcher(
            None, normalize(help_request.location_text), normalize(resource.location_text)
        ).ratio()
        score = round((type_score * 0.65) + (zone_score * 0.35), 3)
        if score >= 0.55:
            matches.append(
                {
                    "resource": resource,
                    "score": score,
                    "reason": "Coincidencia estructurada de tipo de recurso y zona.",
                }
            )
    return sorted(matches, key=lambda item: item["score"], reverse=True)[:10]


def missing_required_information(report_type: ReportType, report) -> list[str]:
    missing = []
    for field, label in (
        ("location_text", "zona general"),
        ("description_public", "descripción pública"),
        ("reporter_contact_private", "contacto privado"),
    ):
        if not getattr(report, field, None):
            missing.append(label)
    if report_type is ReportType.MISSING_PERSON and not report.last_contact_date:
        missing.append("fecha aproximada del último contacto")
    return missing
