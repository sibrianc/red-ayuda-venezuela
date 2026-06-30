import math

from flask import abort, render_template, request

from app.constants import ReportStatus
from app.reports import bp
from app.services.reporting import (
    get_report_by_public_id,
    parse_report_type,
    public_items,
    report_title,
)

# Sitio agregador: ya no se capturan reportes ciudadanos por formulario. El reporte de
# personas desaparecidas se hace en el registro ciudadano canónico
# (desaparecidosterremotovenezuela.com). Aquí solo agregamos y presentamos información de
# fuentes verificadas. Quedan únicamente las vistas de SOLO LECTURA (listado y detalle).


@bp.get("")
def index():
    filters = {
        "q": request.args.get("q", "").strip(),
        "zone": request.args.get("zone", "").strip(),
        "type": request.args.get("type", "").strip(),
        "priority": request.args.get("priority", "").strip(),
    }
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 20
    items = public_items(filters)
    total_pages = max(math.ceil(len(items) / per_page), 1)
    page = min(page, total_pages)
    start = (page - 1) * per_page
    return render_template(
        "reports/index.html",
        items=items[start : start + per_page],
        filters=filters,
        page=page,
        total_pages=total_pages,
    )


@bp.get("/<report_type>/<public_id>")
def detail(report_type: str, public_id: str):
    try:
        parsed_type = parse_report_type(report_type)
        report = get_report_by_public_id(parsed_type, public_id)
    except LookupError:
        abort(404)
    if report.status is not ReportStatus.APPROVED or not report.is_public:
        abort(404)
    return render_template(
        "reports/detail.html",
        report=report,
        report_type=parsed_type,
        title=report_title(parsed_type, report),
    )
