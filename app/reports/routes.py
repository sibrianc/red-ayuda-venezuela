import math

from flask import abort, redirect, render_template, request, url_for

from app.constants import ReportStatus, ReportType, SourceChannel
from app.extensions import db, limiter
from app.i18n import translate as _
from app.models import LostPetReport
from app.reports import bp
from app.reports.forms import LostPetForm
from app.services.automation import find_duplicate_candidates, suggest_priority
from app.services.forwarding import forward_report_to_institutions
from app.services.intake import evaluate_intake
from app.services.reporting import (
    get_report_by_public_id,
    parse_report_type,
    public_items,
    report_title,
)

# Sitio agregador: el reporte de PERSONAS se delega al registro ciudadano canónico
# (desaparecidosterremotovenezuela.com) y los demás formularios ciudadanos se retiraron.
# ÚNICA excepción: MASCOTAS perdidas — no existe un registro externo de mascotas, así que
# aquí sí se reportan (la comunidad alimenta el directorio de mascotas del terremoto).


def _common_values(form):
    return {
        "location_text": form.location_text.data.strip(),
        "exact_address_private": (form.exact_address_private.data or "").strip() or None,
        "latitude": float(form.latitude.data) if form.latitude.data is not None else None,
        "longitude": float(form.longitude.data) if form.longitude.data is not None else None,
        "location_precision": "approximate",
        "description_public": form.description_public.data.strip(),
        "description_private": (form.description_private.data or "").strip() or None,
        "reporter_name_private": form.reporter_name_private.data.strip(),
        "reporter_contact_private": form.reporter_contact_private.data.strip(),
        "source_channel": SourceChannel.WEB,
        "status": ReportStatus.PENDING,
        "is_public": False,
    }


def _save_report(report_type, report):
    db.session.add(report)
    db.session.flush()
    suggested_priority, _reasons = suggest_priority(report_type, report)
    report.priority = suggested_priority
    for candidate in find_duplicate_candidates(report_type, report):
        db.session.add(candidate)
    # Compuerta automática: limpia y decide publicar o resguardar para revisión.
    decision = evaluate_intake(report_type, report)
    report.status = decision.status
    report.is_public = decision.is_public
    db.session.commit()
    if decision.is_public:
        forward_report_to_institutions(report_type, report)
    return redirect(
        url_for(
            "reports.confirmation",
            public_id=report.public_id,
            draft_key=f"rav-draft-{report_type.value}",
            published="1" if decision.is_public else "0",
        )
    )


@bp.route("/mascota", methods=["GET", "POST"])
@limiter.limit("30 per hour", methods=["POST"])
def lost_pet():
    form = LostPetForm()
    if form.validate_on_submit():
        report = LostPetReport(
            **_common_values(form),
            title=form.title.data.strip(),
            species=form.species.data,
            breed=(form.breed.data or "").strip() or None,
            color=(form.color.data or "").strip() or None,
            last_seen_date=form.last_seen_date.data,
            photo_url=(form.photo_url.data or "").strip() or None,
        )
        return _save_report(ReportType.LOST_PET, report)
    return render_template(
        "reports/form.html",
        form=form,
        title=_("Reportar mascota desaparecida"),
        report_type=ReportType.LOST_PET,
    )


@bp.get("/confirmacion/<public_id>")
def confirmation(public_id: str):
    return render_template(
        "reports/confirmation.html",
        public_id=public_id,
        draft_key=request.args.get("draft_key", ""),
    )


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
