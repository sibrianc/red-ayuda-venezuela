from app.constants import DataSourceStatus
from app.models import DataSource


class SourceAuthorizationError(PermissionError):
    """La política de la fuente no permite la operación solicitada."""


def require_staging_authorization(source: DataSource) -> None:
    """Impide probar una fuente antes de documentar permiso y controles mínimos."""
    if source.authorization_status not in {
        DataSourceStatus.STAGING,
        DataSourceStatus.ACTIVE,
    }:
        raise SourceAuthorizationError(
            f"La fuente {source.slug!r} no está autorizada para staging."
        )
    if (
        not source.license_or_permission
        or not source.last_reviewed_at
        or not source.authorized_at
    ):
        raise SourceAuthorizationError(
            f"La fuente {source.slug!r} no tiene permiso, autorización y revisión vigentes."
        )


def require_active_authorization(source: DataSource) -> None:
    """Impide ejecutar en producción fuentes suspendidas o solo aprobadas para staging."""
    if source.authorization_status != DataSourceStatus.ACTIVE:
        raise SourceAuthorizationError(f"La fuente {source.slug!r} no está activa.")
    require_staging_authorization(source)
