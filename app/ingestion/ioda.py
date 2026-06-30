"""Conector IODA — Internet Outage Detection and Analysis (Georgia Tech).

Detecta cortes de conectividad a internet por región. Para "zonas sin comunicación"
ingerimos las regiones de Venezuela con alertas de corte recientes (posibles víctimas
incomunicadas). Datos públicos con atribución; sin datos personales.

IODA API v2: https://api.ioda.inetintel.cc.gatech.edu/v2
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

from app.ingestion.connectors import USER_AGENT, _ssl_context

IODA_API_BASE = "https://api.ioda.inetintel.cc.gatech.edu/v2"
IODA_SOURCE = "ioda"
IODA_ATTRIBUTION = "IODA · Georgia Tech (Internet Outage Detection and Analysis)"
IODA_PAGE_URL = "https://ioda.inetintel.cc.gatech.edu/country/VE"


@dataclass
class ParsedCommsZone:
    """Zona con posible corte de comunicación, derivada de señales técnicas (IODA)."""

    zone_label: str
    latitude: float | None
    longitude: float | None
    public_note: str | None
    source_url: str | None


def fetch_ioda_alerts(*, hours: int = 24, timeout: int = 30) -> dict:
    """Descarga alertas de corte de IODA para las regiones de Venezuela (últimas `hours`)."""
    until = int(datetime.now(timezone.utc).timestamp())
    since = until - hours * 3600
    params = urllib.parse.urlencode({
        "from": since,
        "until": until,
        "entityType": "region",
        "relatedTo": "country/VE",
    })
    url = f"{IODA_API_BASE}/outages/alerts?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        return json.load(response)


def _coord(attrs: dict, *keys: str) -> float | None:
    for key in keys:
        value = attrs.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return None


def parse_ioda_alerts(payload: dict) -> list[ParsedCommsZone]:
    """Convierte alertas IODA en zonas (una por región con corte; la alerta más reciente).

    Tolerante a la forma de la respuesta: `data` puede ser una lista de alertas o un
    objeto `{"alerts": [...]}`. Cada alerta trae una `entity` (region) con `name`/`code`
    y, si está disponible, coordenadas en `attrs`.
    """
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict):
        alerts = data.get("alerts") or []
    elif isinstance(data, list):
        alerts = data
    else:
        alerts = []

    by_region: dict[str, dict] = {}
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        entity = alert.get("entity") or {}
        name = (entity.get("name") or "").strip()
        code = (entity.get("code") or "").strip()
        key = code or name
        if not key or not name:
            continue
        previous = by_region.get(key)
        if previous is None or (alert.get("time") or 0) >= (previous.get("time") or 0):
            by_region[key] = alert

    zones: list[ParsedCommsZone] = []
    for alert in by_region.values():
        entity = alert.get("entity") or {}
        attrs = entity.get("attrs") or {}
        name = (entity.get("name") or "").strip()
        level = str(alert.get("level") or "").strip()
        datasource = str(alert.get("datasource") or alert.get("dataSource") or "").strip()
        note_bits = ["Posible corte de conectividad detectado por IODA"]
        if level:
            note_bits.append(f"nivel {level}")
        if datasource:
            note_bits.append(f"señal {datasource}")
        zones.append(ParsedCommsZone(
            zone_label=name[:160],
            latitude=_coord(attrs, "latitude", "lat"),
            longitude=_coord(attrs, "longitude", "lng", "lon"),
            public_note=" · ".join(note_bits),
            source_url=IODA_PAGE_URL,
        ))
    return zones
