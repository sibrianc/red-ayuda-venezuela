from functools import wraps

from flask import redirect, request, session, url_for
from flask_login import current_user, login_required

from app.extensions import db


def mfa_passed() -> bool:
    """True si el segundo factor (TOTP) se verificó en esta sesión para este usuario."""
    return bool(current_user.is_authenticated) and session.get("mfa_user_id") == current_user.id


def roles_required(*roles):
    """Exige sesión iniciada, segundo factor (2FA) verificado y rol autorizado."""

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if not mfa_passed():
                return redirect(url_for("auth.two_factor", next=request.path))
            if current_user.role not in roles:
                from flask import abort

                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def record_audit(action: str, detail: str | None = None, *, user_id: int | None = None) -> None:
    """Registra una acción sensible en la bitácora de auditoría (best-effort)."""
    from app.models import AuditLog

    if user_id is None and current_user.is_authenticated:
        user_id = current_user.id
    entry = AuditLog(
        user_id=user_id,
        action=action,
        detail=(detail or None),
        ip=(request.headers.get("X-Forwarded-For", request.remote_addr) or "")[:64] or None,
    )
    db.session.add(entry)
    db.session.commit()
