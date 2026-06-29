import math

from flask import abort, flash, redirect, render_template, request, url_for

from app.constants import Priority, ReportStatus, ReportType, SourceChannel
from app.extensions import db
from app.i18n import translate as _
from app.models import (
    AbuseReport,
    CommunicationSignal,
    HelpRequest,
    LocationReport,
    LostPetReport,
    MissingPersonReport,
    ResourceOffer,
)
from app.reports import bp
from app.reports.forms import (
    AbuseForm,
    CommunicationSignalForm,
    HelpRequestForm,
    LocationReportForm,
    LostPetForm,
    MissingPersonForm,
    ResourceOfferForm,
)
from app.services.automation import find_duplicate_candidates, suggest_priority
from app.services.forwarding import forward_report_to_institutions
from app.services.intake import evaluate_intake
from app.services.reporting import (
    get_report_by_public_id,
    parse_report_type,
    public_items,
    report_title,
)


FORM_CONFIG = {
    ReportType.MISSING_PERSON: (MissingPersonForm, MissingPersonReport, "Persona sin contacto"),
    ReportType.HELP_REQUEST: (HelpRequestForm, HelpRequest, "Solicitud de ayuda"),
    ReportType.RESOURCE_OFFER: (ResourceOfferForm, ResourceOffer, "Oferta de recurso"),
    ReportType.LOCATION_REPORT: (LocationReportForm, LocationReport, "Reporte de zona afectada"),
    ReportType.LOST_PET: (LostPetForm, LostPetReport, "Mascota desaparecida"),
}


def common_values(form):
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


def save_report(report_type: ReportType, report):
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


@bp.route("/sin-comunicacion", methods=["GET", "POST"])
def communication_signal():
    form = CommunicationSignalForm()
    if form.validate_on_submit():
        signal = CommunicationSignal(
            zone_label=form.zone_label.data.strip(),
            latitude=float(form.latitude.data) if form.latitude.data is not None else None,
            longitude=float(form.longitude.data) if form.longitude.data is not None else None,
            public_note=(form.public_note.data or "").strip() or None,
            reporter_contact_private=(form.reporter_contact_private.data or "").strip() or None,
            status="advisory",
            source="community",
        )
        db.session.add(signal)
        db.session.commit()
        flash(
            _("Gracias. Tu reporte de zona sin comunicación fue recibido como alerta sin verificar."),
            "success",
        )
        return redirect(url_for("public.directory_zones"))
    return render_template(
        "reports/communication.html", form=form, title=_("Reportar zona sin comunicación")
    )


@bp.route("/persona", methods=["GET", "POST"])
def missing_person():
    form = MissingPersonForm()
    if form.validate_on_submit():
        report = MissingPersonReport(
            **common_values(form),
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            age=form.age.data,
            gender=form.gender.data or None,
            last_contact_date=form.last_contact_date.data,
            relationship_to_person_private=(form.relationship_to_person_private.data or "").strip() or None,
            medical_information_private=(form.medical_information_private.data or "").strip() or None,
            involves_minor=form.involves_minor.data,
        )
        return save_report(ReportType.MISSING_PERSON, report)
    return render_template(
        "reports/form.html",
        form=form,
        title=_("Reportar persona sin contacto"),
        report_type=ReportType.MISSING_PERSON,
    )


@bp.route("/ayuda", methods=["GET", "POST"])
def help_request():
    form = HelpRequestForm()
    if form.validate_on_submit():
        report = HelpRequest(
            **common_values(form),
            title=form.title.data.strip(),
            request_type=form.request_type.data,
            people_affected=form.people_affected.data,
            vulnerable_people_present=form.vulnerable_people_present.data,
            medical_need=form.medical_need.data,
            water_need=form.water_need.data,
            food_need=form.food_need.data,
            shelter_need=form.shelter_need.data,
            transport_need=form.transport_need.data,
            medical_information_private=(form.medical_information_private.data or "").strip() or None,
        )
        return save_report(ReportType.HELP_REQUEST, report)
    return render_template(
        "reports/form.html",
        form=form,
        title=_("Solicitar ayuda"),
        report_type=ReportType.HELP_REQUEST,
    )


@bp.route("/recurso", methods=["GET", "POST"])
def resource_offer():
    form = ResourceOfferForm()
    if form.validate_on_submit():
        report = ResourceOffer(
            **common_values(form),
            title=form.title.data.strip(),
            resource_type=form.resource_type.data,
            capacity=(form.capacity.data or "").strip() or None,
            availability=(form.availability.data or "").strip() or None,
            public_contact_allowed=False,
        )
        return save_report(ReportType.RESOURCE_OFFER, report)
    return render_template(
        "reports/form.html",
        form=form,
        title=_("Ofrecer ayuda o recursos"),
        report_type=ReportType.RESOURCE_OFFER,
    )


@bp.route("/zona", methods=["GET", "POST"])
def location_report():
    form = LocationReportForm()
    if form.validate_on_submit():
        report = LocationReport(
            **common_values(form),
            title=form.title.data.strip(),
            damage_level=form.damage_level.data,
            needs_water=form.needs_water.data,
            needs_food=form.needs_food.data,
            needs_medical=form.needs_medical.data,
            needs_shelter=form.needs_shelter.data,
            needs_transport=form.needs_transport.data,
        )
        return save_report(ReportType.LOCATION_REPORT, report)
    return render_template(
        "reports/form.html",
        form=form,
        title=_("Reportar una zona afectada"),
        report_type=ReportType.LOCATION_REPORT,
    )


@bp.route("/mascota", methods=["GET", "POST"])
def lost_pet():
    form = LostPetForm()
    if form.validate_on_submit():
        report = LostPetReport(
            **common_values(form),
            title=form.title.data.strip(),
            species=form.species.data,
            breed=(form.breed.data or "").strip() or None,
            color=(form.color.data or "").strip() or None,
            last_seen_date=form.last_seen_date.data,
            photo_url=(form.photo_url.data or "").strip() or None,
        )
        return save_report(ReportType.LOST_PET, report)
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


@bp.route("/<report_type>/<public_id>/abuso", methods=["GET", "POST"])
def report_abuse(report_type: str, public_id: str):
    try:
        parsed_type = parse_report_type(report_type)
        report = get_report_by_public_id(parsed_type, public_id)
    except LookupError:
        abort(404)
    if report.status is not ReportStatus.APPROVED or not report.is_public:
        abort(404)
    form = AbuseForm()
    if form.validate_on_submit():
        abuse = AbuseReport(
            report_type=parsed_type,
            report_id=report.id,
            reason=form.reason.data,
            details=(form.details.data or "").strip() or None,
            submitted_by_contact_private=(form.contact.data or "").strip() or None,
        )
        db.session.add(abuse)
        db.session.commit()
        flash("Gracias. El reporte fue enviado para revisión.", "success")
        return redirect(url_for("reports.detail", report_type=report_type, public_id=public_id))
    return render_template("reports/abuse.html", form=form, report=report, report_type=parsed_type)
