from datetime import datetime, timezone

import pytest

from app.constants import (
    DataClassification,
    DataSourceAccess,
    DataSourceKind,
    DataSourceStatus,
)
from app.ingestion.registry import (
    SourceAuthorizationError,
    require_active_authorization,
    require_staging_authorization,
)
from app.models import DataSource


def make_source(status=DataSourceStatus.PROPOSED, **overrides):
    values = {
        "slug": "official-feed",
        "name": "Official feed",
        "owner_name": "Public agency",
        "homepage_url": "https://example.org",
        "source_kind": DataSourceKind.AUTHORITATIVE,
        "access_method": DataSourceAccess.FEED,
        "authorization_status": status,
        "license_or_permission": "Public feed terms reviewed for staging.",
        "purpose": "Event metadata",
        "categories": "event, seismic",
        "contains_personal_data": False,
        "maximum_data_class": DataClassification.PUBLIC_AGGREGATE,
        "retention_policy": "Keep snapshots for audit while the emergency is active.",
        "internal_owner": "Data lead",
        "last_reviewed_at": datetime.now(timezone.utc),
        "authorized_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return DataSource(**values)


def test_proposed_source_is_rejected_for_staging():
    with pytest.raises(SourceAuthorizationError, match="no está autorizada"):
        require_staging_authorization(make_source())


def test_staging_source_requires_permission_and_review():
    source = make_source(DataSourceStatus.STAGING, license_or_permission=None)
    with pytest.raises(SourceAuthorizationError, match="permiso, autorización y revisión"):
        require_staging_authorization(source)


def test_staging_source_requires_authorization_date():
    source = make_source(DataSourceStatus.STAGING, authorized_at=None)
    with pytest.raises(SourceAuthorizationError, match="autorización"):
        require_staging_authorization(source)


def test_staging_source_is_not_active_in_production():
    source = make_source(DataSourceStatus.STAGING)
    require_staging_authorization(source)
    with pytest.raises(SourceAuthorizationError, match="no está activa"):
        require_active_authorization(source)


def test_active_source_passes_both_authorization_gates():
    source = make_source(DataSourceStatus.ACTIVE)
    require_staging_authorization(source)
    require_active_authorization(source)


def test_registry_has_no_field_for_secret_values():
    fields = set(DataSource.__table__.columns.keys())
    assert "api_key" not in fields
    assert "token" not in fields
    assert "password" not in fields
    assert "secret_env_var" in fields
