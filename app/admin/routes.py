import csv
import io
import secrets
from datetime import timedelta

from flask import Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.admin import bp
from app.admin.forms import AbuseReviewForm, InviteUserForm, ReviewForm
from app.constants import (
    AbuseStatus,
    Priority,
    ReportStatus,
    ReportType,
    UserRole,
    VerificationStatus,
)
from app.extensions import db
from app.models import (
    AbuseReport,
    AdminNote,
    AuditLog,
    DuplicateCandidate,
    REPORT_MODELS,
    ReportStatusHistory,
    User,
    utcnow,
)
from app.services.auth import record_audit, roles_required
from app.services.automation import (
    missing_required_information,
    suggest_priority,
    suggest_resource_matches,
)
from app.services.operational import coordination_overview
from app.services.reporting import (
    all_items,
    data_freshness,
    get_report,
    parse_report_type,
    public_items,
    report_title,
)


@bp.get("")
@roles_required(UserRole.ADMIN, UserRole.REVIEWER)
def dashboard():
    status = request.args.get("status", "pending")
    if status == "all":
        status = None
    elif status not in {item.value for item in ReportStatus}:
        status = ReportStatus.PENDING.value
    items = all_items(status)
    counts = {
        state.value: sum(
            model.query.filter_by(status=state).count() for model in REPORT_MODELS.values()
        )
        for state in ReportStatus
    }
    abuse_count = AbuseReport.query.filter_by(status=AbuseStatus.PENDING).count()
    return render_template(
        "admin/dashboard.html", items=items, status=status, counts=counts, abuse_count=abuse_count
    )


@bp.get("/operacion")
@roles_required(UserRole.ADMIN, UserRole.REVIEWER)
def operations():
    """Resumen operativo 4W: necesidades ↔ recursos, brechas, prioridades, frescura."""
    overview = coordination_overview()
    needs = []
    for item in public_items({"type": ReportType.HELP_REQUEST.value}):
        matches = suggest_resource_matches(item.report)
        needs.append({"report": item.report, "matches": matches[:3], "has_match": bool(matches)})
    gaps = [n for n in needs if not n["has_match"]]
    resources = public_items({"type": ReportType.RESOURCE_OFFER.value})
    return render_template(
        "admin/operations.html",
        needs=needs,
        gaps=gaps,
        resource_total=len(resources),
        freshness=data_freshness(),
        **overview,
    )


@bp.route("/reportes/<report_type>/<int:report_id>", methods=["GET", "POST"])
@roles_required(UserRole.ADMIN, UserRole.REVIEWER)
def review_report(report_type: str, report_id: int):
    try:
        parsed_type = parse_report_type(report_type)
        report = get_report(parsed_type, report_id)
    except LookupError:
        abort(404)

    form = ReviewForm()
    if request.method == "GET":
        form.status.data = report.status.value
        form.verification_status.data = report.verification_status.value
        form.priority.data = report.priority.value
        form.is_public.data = report.is_public
        form.description_public.data = report.description_public

    if form.validate_on_submit():
        old_status = report.status
        new_status = ReportStatus(form.status.data)
        report.status = new_status
        report.verification_status = VerificationStatus(form.verification_status.data)
        report.priority = Priority(form.priority.data)
        report.description_public = form.description_public.data.strip()
        report.is_public = bool(form.is_public.data and new_status is ReportStatus.APPROVED)

        if old_status is not new_status:
            db.session.add(
                ReportStatusHistory(
                    report_type=parsed_type,
                    report_id=report.id,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=current_user.id,
                    reason=(form.reason.data or "").strip() or None,
                )
            )
        if form.note.data and form.note.data.strip():
            db.session.add(
                AdminNote(
                    report_type=parsed_type,
                    report_id=report.id,
                    user_id=current_user.id,
                    note=form.note.data.strip(),
                )
            )
        db.session.commit()
        record_audit("report_reviewed", detail=f"{parsed_type.value}:{report.public_id}->{new_status.value}")
        flash("Revisión guardada.", "success")
        return redirect(
            url_for("admin.review_report", report_type=parsed_type.value, report_id=report.id)
        )

    notes = AdminNote.query.filter_by(report_type=parsed_type, report_id=report.id).order_by(
        AdminNote.created_at.desc()
    )
    history = ReportStatusHistory.query.filter_by(
        report_type=parsed_type, report_id=report.id
    ).order_by(ReportStatusHistory.created_at.desc())
    duplicates = DuplicateCandidate.query.filter_by(
        report_type=parsed_type, report_id=report.id
    ).order_by(DuplicateCandidate.score.desc())
    suggested_priority, priority_reasons = suggest_priority(parsed_type, report)
    resource_matches = (
        suggest_resource_matches(report) if parsed_type is ReportType.HELP_REQUEST else []
    )
    return render_template(
        "admin/review.html",
        report=report,
        report_type=parsed_type,
        title=report_title(parsed_type, report),
        form=form,
        notes=notes,
        history=history,
        duplicates=duplicates,
        suggested_priority=suggested_priority,
        priority_reasons=priority_reasons,
        missing_information=missing_required_information(parsed_type, report),
        resource_matches=resource_matches,
    )


@bp.get("/abuso")
@roles_required(UserRole.ADMIN, UserRole.REVIEWER)
def abuse_queue():
    reports = AbuseReport.query.order_by(AbuseReport.created_at.desc()).all()
    return render_template("admin/abuse_queue.html", reports=reports)


@bp.route("/abuso/<int:abuse_id>", methods=["GET", "POST"])
@roles_required(UserRole.ADMIN, UserRole.REVIEWER)
def review_abuse(abuse_id: int):
    abuse = db.get_or_404(AbuseReport, abuse_id)
    form = AbuseReviewForm()
    if request.method == "GET":
        form.status.data = abuse.status.value
    if form.validate_on_submit():
        abuse.status = AbuseStatus(form.status.data)
        abuse.reviewed_by = current_user.id
        db.session.commit()
        flash("Reporte de abuso actualizado.", "success")
        return redirect(url_for("admin.abuse_queue"))
    try:
        report = get_report(abuse.report_type, abuse.report_id)
    except LookupError:
        report = None
    return render_template("admin/abuse_review.html", abuse=abuse, report=report, form=form)


def csv_safe(value) -> str:
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


@bp.get("/exportar/<report_type>.csv")
@roles_required(UserRole.ADMIN)
def export_csv(report_type: str):
    try:
        parsed_type = parse_report_type(report_type)
    except LookupError:
        abort(404)
    scope = request.args.get("scope", "public")
    if scope not in {"public", "internal"}:
        abort(400)
    model = REPORT_MODELS[parsed_type]
    query = model.query
    if scope == "public":
        query = query.filter_by(status=ReportStatus.APPROVED, is_public=True)

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    headers = [
        "public_id",
        "type",
        "title",
        "status",
        "priority",
        "verification",
        "location_general",
        "description_public",
        "created_at_utc",
        "updated_at_utc",
    ]
    if scope == "internal":
        headers.extend(
            [
                "is_public",
                "exact_address_private",
                "description_private",
                "reporter_name_private",
                "reporter_contact_private",
            ]
        )
    writer.writerow(headers)
    for report in query.order_by(model.created_at.desc()).all():
        row = [
            report.public_id,
            parsed_type.value,
            report_title(parsed_type, report),
            report.status.value,
            report.priority.value,
            report.verification_status.value,
            report.location_text,
            report.description_public,
            report.created_at.isoformat(),
            report.updated_at.isoformat(),
        ]
        if scope == "internal":
            row.extend(
                [
                    report.is_public,
                    report.exact_address_private,
                    report.description_private,
                    report.reporter_name_private,
                    report.reporter_contact_private,
                ]
            )
        writer.writerow([csv_safe(value) for value in row])

    response = Response(output.getvalue(), mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{parsed_type.value}-{scope}.csv"'
    )
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["X-Data-Classification"] = "sensitive" if scope == "internal" else "public"
    record_audit("export_csv", detail=f"{parsed_type.value}/{scope}")
    return response


@bp.route("/usuarios", methods=["GET", "POST"])
@roles_required(UserRole.ADMIN)
def users():
    form = InviteUserForm()
    invite_link = None
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash("Ya existe una cuenta con ese correo.", "warning")
        else:
            token = secrets.token_urlsafe(32)
            user = User(
                name=form.name.data.strip(),
                email=email,
                role=UserRole(form.role.data),
                is_active=True,
                invite_token=token,
                invite_expires_at=utcnow() + timedelta(hours=72),
            )
            db.session.add(user)
            db.session.commit()
            record_audit("user_invited", detail=f"{email} ({form.role.data})")
            invite_link = url_for("auth.accept_invite", token=token, _external=True)
            flash("Invitación creada. Copia el enlace y compártelo de forma segura (expira en 72 h).", "success")
    people = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", form=form, people=people, invite_link=invite_link)


@bp.post("/usuarios/<int:user_id>/estado")
@roles_required(UserRole.ADMIN)
def toggle_user(user_id: int):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("No puedes desactivar tu propia cuenta.", "warning")
    else:
        user.is_active = not user.is_active
        db.session.commit()
        record_audit("user_active_toggled", detail=f"{user.email}={user.is_active}")
    return redirect(url_for("admin.users"))


@bp.get("/auditoria")
@roles_required(UserRole.ADMIN)
def audit():
    entries = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    actors = {u.id: u.email for u in User.query.all()}
    return render_template("admin/audit.html", entries=entries, actors=actors)
