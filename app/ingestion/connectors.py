"""Conectores de fuentes públicas.

Cada conector conoce el esquema de SU fuente y devuelve eventos ya mapeados al
objeto canónico (ParsedEvent). El *fetch* de red se mantiene separado del
*parseo* para que las pruebas corran sobre fixtures sin tocar Internet.

Usa la librería estándar (urllib + json) y `certifi` para las CA de SSL.
"""

from __future__ import annotations

import hashlib
import json
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

USER_AGENT = "RedAyudaVE/ingesta (proyecto humanitario; contacto pendiente)"


def _ssl_context() -> ssl.SSLContext:
    """Contexto SSL con el bundle de CA de certifi.

    Evita el error `CERTIFICATE_VERIFY_FAILED` en entornos cuyo Python no encuentra
    las CA del sistema (típico en macOS). Si certifi no está, usa el contexto por defecto.
    """
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001 — fallback al contexto por defecto
        return ssl.create_default_context()

# Recuadro aproximado de Venezuela (incluye costa y zonas fronterizas) para marcar
# qué eventos caen en la región de interés sin descartar el resto.
VENEZUELA_BBOX = {
    "lat_min": 0.0,
    "lat_max": 13.0,
    "lon_min": -74.5,
    "lon_max": -59.0,
}

# Feeds GeoJSON públicos de USGS (dominio público; atribuir a U.S. Geological Survey).
USGS_FEEDS = {
    "hour_all": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
    "day_all": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    "week_all": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson",
    "month_2.5": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_month.geojson",
    "month_4.5": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_month.geojson",
    "month_all": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson",
}

USGS_SOURCE_SLUG = "usgs-earthquake-geojson"
USGS_ATTRIBUTION = "U.S. Geological Survey"


@dataclass(frozen=True)
class ParsedEvent:
    """Un evento de una fuente, ya mapeado a campos canónicos, listo para limpiar."""

    source_slug: str
    external_id: str
    content_hash: str
    raw_payload: str
    detail_url: str | None
    schema_version: str | None
    event_type: str
    title: str | None
    magnitude: float | None
    place: str | None
    latitude: float | None
    longitude: float | None
    depth_km: float | None
    occurred_at: datetime | None
    alert_level: str | None
    tsunami: bool
    felt_reports: int | None
    significance: int | None
    attribution: str | None
    # Campos genéricos multi-amenaza (los llena cada conector según su fuente).
    hazard_code: str | None = None
    severity_value: float | None = None
    severity_text: str | None = None
    country: str | None = None


def in_venezuela_region(latitude: float | None, longitude: float | None) -> bool:
    if latitude is None or longitude is None:
        return False
    return (
        VENEZUELA_BBOX["lat_min"] <= latitude <= VENEZUELA_BBOX["lat_max"]
        and VENEZUELA_BBOX["lon_min"] <= longitude <= VENEZUELA_BBOX["lon_max"]
    )


def _content_hash(raw: dict) -> str:
    payload = json.dumps(raw, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _coerce_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _epoch_ms_to_utc(value) -> datetime | None:
    ms = _coerce_int(value)
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def fetch_usgs(feed: str = "month_2.5", *, timeout: int = 30) -> dict:
    """Descarga un feed GeoJSON de USGS. Requiere red; no se llama en pruebas."""
    url = USGS_FEEDS.get(feed, feed)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    context = _ssl_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return json.load(response)


def parse_usgs_geojson(payload: dict) -> list[ParsedEvent]:
    """Convierte un FeatureCollection de USGS en eventos canónicos.

    Función pura: tolera claves faltantes y descarta features sin id o geometría
    válida. No toca la base ni la red.
    """
    schema_version = (payload.get("metadata") or {}).get("api") or "USGS GeoJSON v1.0"
    events: list[ParsedEvent] = []
    for feature in payload.get("features", []) or []:
        if not isinstance(feature, dict):
            continue
        external_id = feature.get("id")
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if not external_id or len(coordinates) < 2:
            continue
        longitude = _coerce_float(coordinates[0])
        latitude = _coerce_float(coordinates[1])
        depth_km = _coerce_float(coordinates[2]) if len(coordinates) >= 3 else None
        if latitude is None or longitude is None:
            continue
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            continue

        props = feature.get("properties") or {}
        events.append(
            ParsedEvent(
                source_slug=USGS_SOURCE_SLUG,
                external_id=str(external_id),
                content_hash=_content_hash(feature),
                raw_payload=json.dumps(feature, sort_keys=True, separators=(",", ":")),
                detail_url=props.get("url"),
                schema_version=schema_version,
                event_type=(props.get("type") or "earthquake").strip().lower(),
                title=props.get("title"),
                magnitude=_coerce_float(props.get("mag")),
                place=props.get("place"),
                latitude=latitude,
                longitude=longitude,
                depth_km=depth_km,
                occurred_at=_epoch_ms_to_utc(props.get("time")),
                alert_level=(props.get("alert") or None),
                tsunami=bool(props.get("tsunami")),
                felt_reports=_coerce_int(props.get("felt")),
                significance=_coerce_int(props.get("sig")),
                attribution=USGS_ATTRIBUTION,
                hazard_code="EQ",
                severity_value=_coerce_float(props.get("mag")),
                severity_text=props.get("title"),
                country=None,
            )
        )
    return events


# --- GDACS (UN / European Commission) -------------------------------------
#
# Feeds públicos multi-amenaza. Esquema verificado contra el endpoint en vivo:
# FeatureCollection con properties: eventtype (EQ/FL/TC/VO/WF/DR), eventid,
# alertlevel, name, fromdate (ISO sin tz, UTC), country, severitydata{...}, url.

GDACS_SOURCE_SLUG = "gdacs-public-feeds"
GDACS_ATTRIBUTION = "GDACS — United Nations / European Commission"

GDACS_FEEDS = {
    "map": "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP",
    "search": "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH",
}

GDACS_HAZARD_TYPES = {
    "EQ": "earthquake",
    "TC": "cyclone",
    "FL": "flood",
    "VO": "volcano",
    "WF": "wildfire",
    "DR": "drought",
}


def _iso_to_utc(value) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _geometry_point(geometry: dict) -> tuple[float | None, float | None]:
    """Devuelve (lon, lat) de un Point, o el centroide simple de un Polygon."""
    coordinates = (geometry or {}).get("coordinates")
    geom_type = (geometry or {}).get("type")
    if not coordinates:
        return None, None
    if geom_type == "Point":
        lon = _coerce_float(coordinates[0]) if len(coordinates) >= 1 else None
        lat = _coerce_float(coordinates[1]) if len(coordinates) >= 2 else None
        return lon, lat
    # Polygon / MultiPolygon: promedio del primer anillo como punto aproximado.
    ring = coordinates
    while ring and isinstance(ring[0], list) and ring and isinstance(ring[0][0], list):
        ring = ring[0]
    if ring and isinstance(ring[0], list):
        lons = [_coerce_float(p[0]) for p in ring if len(p) >= 2]
        lats = [_coerce_float(p[1]) for p in ring if len(p) >= 2]
        lons = [v for v in lons if v is not None]
        lats = [v for v in lats if v is not None]
        if lons and lats:
            return sum(lons) / len(lons), sum(lats) / len(lats)
    return None, None


def _gdacs_detail_url(url_field) -> str | None:
    if isinstance(url_field, dict):
        return url_field.get("report") or url_field.get("details") or url_field.get("geometry")
    if isinstance(url_field, str):
        return url_field
    return None


def fetch_gdacs(feed: str = "map", *, timeout: int = 30) -> dict:
    """Descarga un feed GeoJSON de GDACS. Requiere red; no se llama en pruebas."""
    url = GDACS_FEEDS.get(feed, feed)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    context = _ssl_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return json.load(response)


def parse_gdacs_geojson(payload: dict) -> list[ParsedEvent]:
    """Convierte un FeatureCollection de GDACS en eventos canónicos multi-amenaza."""
    events: list[ParsedEvent] = []
    for feature in payload.get("features", []) or []:
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties") or {}
        event_id = props.get("eventid")
        hazard_code = (props.get("eventtype") or "").strip().upper()
        if not event_id or not hazard_code:
            continue
        longitude, latitude = _geometry_point(feature.get("geometry") or {})
        if latitude is not None and not (-90 <= latitude <= 90):
            latitude = None
        if longitude is not None and not (-180 <= longitude <= 180):
            longitude = None

        severity = props.get("severitydata") or {}
        severity_value = _coerce_float(severity.get("severity"))
        magnitude = severity_value if hazard_code == "EQ" else None
        alert_level = (props.get("alertlevel") or "").strip().lower() or None

        events.append(
            ParsedEvent(
                source_slug=GDACS_SOURCE_SLUG,
                external_id=f"{hazard_code}{event_id}",
                content_hash=_content_hash(feature),
                raw_payload=json.dumps(feature, sort_keys=True, separators=(",", ":")),
                detail_url=_gdacs_detail_url(props.get("url")),
                schema_version="GDACS geteventlist GeoJSON",
                event_type=GDACS_HAZARD_TYPES.get(hazard_code, hazard_code.lower()),
                title=props.get("name") or props.get("description"),
                magnitude=magnitude,
                place=props.get("country"),
                latitude=latitude,
                longitude=longitude,
                depth_km=None,
                occurred_at=_iso_to_utc(props.get("fromdate")),
                alert_level=alert_level,
                tsunami=False,
                felt_reports=None,
                significance=None,
                attribution=GDACS_ATTRIBUTION,
                hazard_code=hazard_code,
                severity_value=severity_value,
                severity_text=severity.get("severitytext"),
                country=props.get("country"),
            )
        )
    return events


# --- OpenStreetMap (Overpass API) -----------------------------------------
#
# Directorio de servicios públicos (hospitales, refugios, clínicas, bomberos,
# puntos de agua). Datos abiertos bajo ODbL; atribuir a OpenStreetMap.
# Esquema verificado contra el endpoint: elements[] con type/id, lat/lon (nodos)
# o center{lat,lon} (vías/relaciones), y tags{amenity, name, addr:*, phone, ...}.

OSM_SOURCE_SLUG = "osm-overpass"
OSM_ATTRIBUTION = "© OpenStreetMap contributors"
OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"

# Etiquetas OSM que nos interesan, mapeadas a categorías propias.
OSM_AMENITY_TO_CATEGORY = {
    "hospital": "hospital",
    "clinic": "clinic",
    "doctors": "clinic",
    "pharmacy": "pharmacy",
    "fire_station": "fire_station",
    "police": "police",
    "shelter": "shelter",
    "social_facility": "shelter",
    "community_centre": "community_center",
    "drinking_water": "water_point",
}
EMERGENCY_CATEGORIES = {"hospital", "clinic", "fire_station", "police"}
CATEGORY_DEFAULT_LABEL = {
    "hospital": "Hospital",
    "clinic": "Clínica / consultorio",
    "pharmacy": "Farmacia",
    "fire_station": "Estación de bomberos",
    "police": "Policía",
    "shelter": "Refugio",
    "community_center": "Centro comunitario",
    "water_point": "Punto de agua",
    "other": "Servicio",
}


@dataclass(frozen=True)
class ParsedDirectoryEntry:
    """Una entrada de directorio mapeada a campos canónicos, lista para guardar."""

    source_slug: str
    external_id: str
    content_hash: str
    raw_payload: str
    category: str
    name: str
    latitude: float | None
    longitude: float | None
    address_public: str | None
    phone_public: str | None
    operator: str | None
    emergency: bool
    source_url: str | None
    attribution: str | None


def build_overpass_query(bbox: dict | None = None) -> str:
    """Consulta Overpass QL para servicios clave dentro del recuadro de Venezuela."""
    box = bbox or VENEZUELA_BBOX
    # Overpass usa el orden (sur, oeste, norte, este).
    area = f'({box["lat_min"]},{box["lon_min"]},{box["lat_max"]},{box["lon_max"]})'
    selectors = [f'nwr["amenity"="{value}"]{area};' for value in (
        "hospital", "clinic", "doctors", "pharmacy", "fire_station",
        "police", "shelter", "social_facility", "community_centre", "drinking_water",
    )]
    selectors.append(f'nwr["healthcare"="hospital"]{area};')
    selectors.append(f'nwr["emergency"="yes"]{area};')
    return "[out:json][timeout:90];(" + "".join(selectors) + ");out center tags;"


def fetch_overpass(query: str | None = None, *, timeout: int = 120) -> dict:
    """Descarga datos de Overpass (POST). Requiere red; no se llama en pruebas."""
    body = urllib.parse.urlencode({"data": query or build_overpass_query()}).encode("utf-8")
    request = urllib.request.Request(
        OVERPASS_ENDPOINT, data=body, headers={"User-Agent": USER_AGENT}
    )
    context = _ssl_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return json.load(response)


def _osm_category(tags: dict) -> str:
    if tags.get("healthcare") == "hospital":
        return "hospital"
    amenity = tags.get("amenity")
    if amenity in OSM_AMENITY_TO_CATEGORY:
        return OSM_AMENITY_TO_CATEGORY[amenity]
    if tags.get("emergency") == "yes":
        return "shelter"
    return "other"


def _osm_address(tags: dict) -> str | None:
    parts = [
        " ".join(p for p in (tags.get("addr:street"), tags.get("addr:housenumber")) if p),
        tags.get("addr:city"),
    ]
    address = ", ".join(p for p in parts if p)
    return address or None


def parse_overpass(payload: dict) -> list[ParsedDirectoryEntry]:
    """Convierte una respuesta Overpass en entradas de directorio canónicas."""
    entries: list[ParsedDirectoryEntry] = []
    for element in payload.get("elements", []) or []:
        if not isinstance(element, dict):
            continue
        osm_type = element.get("type")
        osm_id = element.get("id")
        if not osm_type or osm_id is None:
            continue
        latitude = _coerce_float(element.get("lat"))
        longitude = _coerce_float(element.get("lon"))
        if latitude is None or longitude is None:
            center = element.get("center") or {}
            latitude = _coerce_float(center.get("lat"))
            longitude = _coerce_float(center.get("lon"))
        if latitude is None or longitude is None:
            continue

        tags = element.get("tags") or {}
        category = _osm_category(tags)
        name = tags.get("name") or CATEGORY_DEFAULT_LABEL.get(category, "Servicio")
        entries.append(
            ParsedDirectoryEntry(
                source_slug=OSM_SOURCE_SLUG,
                external_id=f"{osm_type}/{osm_id}",
                content_hash=_content_hash(element),
                raw_payload=json.dumps(element, sort_keys=True, separators=(",", ":")),
                category=category,
                name=name[:240],
                latitude=latitude,
                longitude=longitude,
                address_public=_osm_address(tags),
                phone_public=(tags.get("phone") or tags.get("contact:phone")),
                operator=tags.get("operator"),
                emergency=(tags.get("emergency") == "yes" or category in EMERGENCY_CATEGORIES),
                source_url=f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
                attribution=OSM_ATTRIBUTION,
            )
        )
    return entries
