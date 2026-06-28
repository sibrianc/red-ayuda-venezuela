from dataclasses import dataclass

from sqlalchemy import or_

from app.constants import ReportStatus, ReportType
from app.extensions import db
from app.models import REPORT_MODELS


@dataclass(frozen=True)
class ReportItem:
    report_type: ReportType
    report: object


def parse_report_type(value: str) -> ReportType:
    try:
        return ReportType(value)
    except ValueError as exc:
        raise LookupError("Tipo de reporte desconocido") from exc


def get_report(report_type: ReportType, report_id: int):
    model = REPORT_MODELS[report_type]
    report = db.session.get(model, report_id)
    if report is None:
        raise LookupError("Reporte no encontrado")
    return report


def get_report_by_public_id(report_type: ReportType, public_id: str):
    report = REPORT_MODELS[report_type].query.filter_by(public_id=public_id).first()
    if report is None:
        raise LookupError("Reporte no encontrado")
    return report


def report_title(report_type: ReportType, report) -> str:
    if report_type is ReportType.MISSING_PERSON:
        return f"{report.first_name} {report.last_name}".strip()
    return report.title


def public_report_dict(report_type: ReportType, report) -> dict:
    # La base conserva coordenadas más precisas para operación autorizada. La
    # proyección pública siempre reduce la precisión (~1 km) antes de serializar.
    public_latitude = round(report.latitude, 2) if report.latitude is not None else None
    public_longitude = round(report.longitude, 2) if report.longitude is not None else None
    return {
        "public_id": report.public_id,
        "type": report_type.value,
        "title": report_title(report_type, report),
        "summary": report.description_public,
        "status": report.status.value,
        "priority": report.priority.value,
        "verification": report.verification_status.value,
        "location": {
            "label": report.location_text,
            "latitude": public_latitude,
            "longitude": public_longitude,
            "precision": "approximate",
        },
        "updated_at": report.updated_at.isoformat(),
    }


def public_items(filters: dict | None = None) -> list[ReportItem]:
    filters = filters or {}
    items: list[ReportItem] = []
    requested_type = filters.get("type")
    for report_type, model in REPORT_MODELS.items():
        if requested_type and requested_type != report_type.value:
            continue
        query = model.query.filter_by(status=ReportStatus.APPROVED, is_public=True)
        if filters.get("priority"):
            query = query.filter_by(priority=filters["priority"])
        if filters.get("zone"):
            query = query.filter(model.location_text.ilike(f"%{filters['zone']}%"))
        if filters.get("q"):
            term = f"%{filters['q']}%"
            columns = [model.description_public, model.location_text]
            if hasattr(model, "title"):
                columns.append(model.title)
            if report_type is ReportType.MISSING_PERSON:
                columns.extend([model.first_name, model.last_name])
            query = query.filter(or_(*[column.ilike(term) for column in columns]))
        items.extend(ReportItem(report_type, report) for report in query.all())
    return sorted(items, key=lambda item: item.report.updated_at, reverse=True)


def all_items(status: str | None = None) -> list[ReportItem]:
    items: list[ReportItem] = []
    for report_type, model in REPORT_MODELS.items():
        query = model.query
        if status:
            query = query.filter_by(status=status)
        items.extend(ReportItem(report_type, report) for report in query.all())
    return sorted(items, key=lambda item: item.report.updated_at, reverse=True)
