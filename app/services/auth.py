from functools import wraps

from flask import redirect, request, session, url_for
from flask_login import current_user, login_required

from app.constants import UserRole
from app.extensions import db

# Roles que pueden ver datos personales (PII) y moderar (cambiar estado/publicar).
_TRUSTED_ROLES = {UserRole.ADMIN, UserRole.REVIEWER}


def can_see_pii(user=None) -> bool:
    user = user or current_user
    return bool(user.is_authenticated) and user.role in _TRUSTED_ROLES


def can_moderate(user=None) -> bool:
    """Puede cambiar estado/verificación/prioridad y publicar reportes."""
    user = user or current_user
    return bool(user.is_authenticated) and user.role in _TRUSTED_ROLES


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
