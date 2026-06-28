from datetime import datetime, timezone

from app.constants import (
    DataClassification,
    DataSourceAccess,
    DataSourceKind,
    DataSourceStatus,
)
from app.models import DataSource


PUBLIC_STAGING_AUTHORIZED_AT = datetime(2026, 6, 28, tzinfo=timezone.utc)


PUBLIC_STAGING_SOURCE_VALUES = (
    {
        "slug": "usgs-earthquake-geojson",
        "name": "USGS Earthquake GeoJSON Feed",
        "owner_name": "U.S. Geological Survey",
        "homepage_url": "https://earthquake.usgs.gov/earthquakes/feed/",
        "documentation_url": (
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php"
        ),
        "source_kind": DataSourceKind.AUTHORITATIVE,
        "access_method": DataSourceAccess.FEED,
        "authorization_status": DataSourceStatus.STAGING,
        "license_or_permission": (
            "USGS-authored data is generally public domain; attribute the U.S. "
            "Geological Survey and preserve any item-specific notices."
        ),
        "purpose": "Public seismic event metadata and geometry.",
        "categories": "event,seismic,aftershock",
        "contains_personal_data": False,
        "maximum_data_class": DataClassification.PUBLIC_AGGREGATE,
        "frequency_minutes": 5,
        "rate_limit_notes": "Use the documented real-time feed; cache and honor feed policy.",
        "retention_policy": (
            "Retain source snapshots privately for audit during the emergency; "
            "review retention before production."
        ),
        "attribution": "U.S. Geological Survey",
        "schema_version": "GeoJSON feed v1.0",
        "secret_env_var": None,
        "internal_owner": "Independent project developer / data lead",
        "authorization_notes": (
            "Owner authorized public-source staging on 2026-06-28; no automatic "
            "publication or victim inference."
        ),
        "last_reviewed_at": PUBLIC_STAGING_AUTHORIZED_AT,
        "authorized_at": PUBLIC_STAGING_AUTHORIZED_AT,
    },
    {
        "slug": "gdacs-public-feeds",
        "name": "GDACS Public Feeds",
        "owner_name": "United Nations / European Commission GDACS",
        "homepage_url": "https://www.gdacs.org/",
        "documentation_url": "https://www.gdacs.org/feed_reference.aspx",
        "source_kind": DataSourceKind.HUMANITARIAN,
        "access_method": DataSourceAccess.FEED,
        "authorization_status": DataSourceStatus.STAGING,
        "license_or_permission": (
            "Use under GDACS terms and disclaimer; automated estimates require "
            "validation and never replace national or local authorities."
        ),
        "purpose": "Public disaster alerts, severity and event context.",
        "categories": "event,alert,seismic,impact_estimate",
        "contains_personal_data": False,
        "maximum_data_class": DataClassification.PUBLIC_AGGREGATE,
        "frequency_minutes": 10,
        "rate_limit_notes": "Feeds are documented as updating approximately every 6 minutes.",
        "retention_policy": (
            "Retain source snapshots privately for audit during the emergency; "
            "review retention before production."
        ),
        "attribution": "GDACS — United Nations / European Commission",
        "schema_version": "Public feed reference reviewed 2026-06-28",
        "secret_env_var": None,
        "internal_owner": "Independent project developer / data lead",
        "authorization_notes": (
            "Owner authorized public-source staging on 2026-06-28; show uncertainty "
            "and never present model output as a verified victim count."
        ),
        "last_reviewed_at": PUBLIC_STAGING_AUTHORIZED_AT,
        "authorized_at": PUBLIC_STAGING_AUTHORIZED_AT,
    },
)


def build_public_staging_sources() -> list[DataSource]:
    """Build unsaved registry rows; E4 owns persistence and network connectors."""
    return [DataSource(**values) for values in PUBLIC_STAGING_SOURCE_VALUES]
