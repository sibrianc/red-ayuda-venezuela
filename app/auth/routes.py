import io
from datetime import datetime, timezone
from urllib.parse import urlparse

import qrcode
import qrcode.image.svg
from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import bp
from app.auth.forms import LoginForm, SetPasswordForm, TwoFactorForm
from app.extensions import db, limiter
from app.models import User
from app.services.auth import mfa_passed, record_audit


def _safe_next(target: str | None) -> str:
    """Solo permite redirigir a rutas internas (evita open redirect)."""
    if target and not urlparse(target).netloc and target.startswith("/"):
        return target
    return url_for("admin.dashboard")


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated and mfa_passed():
        return redirect(url_for("admin.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.is_active and user.check_password(form.password.data):
            login_user(user)
            session.pop("mfa_user_id", None)  # exige 2FA en cada inicio
            record_audit("login_password", user_id=user.id)
            return redirect(url_for("auth.two_factor", next=request.args.get("next")))
        record_audit("login_failed", detail=form.email.data.strip().lower()[:120], user_id=None)
        flash("Credenciales inválidas.", "danger")
    return render_template("auth/login.html", form=form)


@bp.route("/2fa", methods=["GET", "POST"])
@login_required
@limiter.limit("12 per minute", methods=["POST"])
def two_factor():
    """Segundo factor obligatorio: inscribe (si no tiene) o verifica el código TOTP."""
    if mfa_passed():
        return redirect(_safe_next(request.args.get("next")))
    enrolling = not current_user.totp_enabled
    if enrolling:
        current_user.ensure_totp_secret()
        db.session.commit()
    form = TwoFactorForm()
    if form.validate_on_submit():
        if current_user.verify_totp(form.code.data):
            if enrolling:
                current_user.totp_enabled = True
                db.session.commit()
                record_audit("2fa_enabled")
            session["mfa_user_id"] = current_user.id
            record_audit("2fa_verified")
            return redirect(_safe_next(request.args.get("next")))
        flash("Código inválido. Revisa tu app autenticadora.", "danger")

    qr_svg = None
    if enrolling:
        img = qrcode.make(current_user.totp_uri(), image_factory=qrcode.image.svg.SvgPathImage)
        buffer = io.BytesIO()
        img.save(buffer)
        qr_svg = buffer.getvalue().decode("utf-8")
    return render_template(
        "auth/two_factor.html",
        form=form,
        enrolling=enrolling,
        qr_svg=qr_svg,
        secret=current_user.totp_secret if enrolling else None,
    )


@bp.route("/invitacion/<token>", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def accept_invite(token: str):
    """Acepta una invitación: fija contraseña y fuerza la inscripción de 2FA."""
    user = User.query.filter_by(invite_token=token).first()
    expired = True
    if user is not None and user.invite_expires_at is not None:
        exp = user.invite_expires_at
        if exp.tzinfo is None:  # SQLite devuelve datetimes sin zona
            exp = exp.replace(tzinfo=timezone.utc)
        expired = exp < datetime.now(timezone.utc)
    if user is None or expired:
        flash("La invitación no es válida o expiró. Pide una nueva al administrador.", "danger")
        return redirect(url_for("auth.login"))
    form = SetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.invite_token = None
        user.invite_expires_at = None
        user.is_active = True
        db.session.commit()
        login_user(user)
        session.pop("mfa_user_id", None)
        record_audit("invite_accepted", user_id=user.id)
        flash("Cuenta activada. Ahora configura tu segundo factor (2FA).", "success")
        return redirect(url_for("auth.two_factor"))
    return render_template("auth/accept_invite.html", form=form, invited=user)


@bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        record_audit("logout")
        logout_user()
    session.pop("mfa_user_id", None)
    return redirect(url_for("public.home"))
