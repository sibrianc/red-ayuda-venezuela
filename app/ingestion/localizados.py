"""Conector a la API pública de Localizados Venezuela.

`localizadosvenezuela.com` ofrece una **API REST pública, de solo lectura y sin
autenticación** ("para integraciones") con personas YA LOCALIZADAS tras el terremoto
(en hospitales, refugios, etc.). Es la vía limpia para reunificación: si una familia
busca a alguien, puede confirmar aquí si fue localizado.

Doc/endpoints: `GET /api/v1/localizados?q=&page=&limit=` y `/api/v1/localizados/{slug}`.

Protección de menores: la API a veces marca menores en el nombre/observaciones
("(niña menor)", "bebé", "lactante"…). Se detectan por texto y se marcan `is_minor`
para EXCLUIRLOS de las vistas públicas.
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request

from app.ingestion.connectors import _ssl_context
from app.ingestion.pfif import ParsedPerson, _parse_dt

API_BASE = "https://localizadosvenezuela.com/api/v1/localizados"
SITE_BASE = "https://localizadosvenezuela.com"
SOURCE_SLUG = "localizados-venezuela"
ATTRIBUTION = "Localizados Venezuela (reporte ciudadano, no verificado)"
USER_AGENT = "RedAyudaVE/reunificacion (humanitario; uso=busqueda/reunificacion)"

MINOR_HINTS = (
    "menor", "niñ", "nino", "bebé", "bebe", "lactante", "adolescent",
    "recién nacid", "recien nacid", "infante", "bebito", "bebita",
)
DECEASED_HINTS = ("fallec", "muerto", "decease", "occiso", "cadáver", "cadaver")


def _looks_minor(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in MINOR_HINTS)


def fetch_localizados(page: int = 1, limit: int = 100, *, q: str = "", timeout: int = 30) -> dict:
    """Descarga una página de la API pública. Requiere red; no se llama en pruebas."""
    query = urllib.parse.urlencode({"q": q, "page": page, "limit": limit})
    request = urllib.request.Request(
        f"{API_BASE}?{query}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        return json.load(response)


def parse_localizados(payload: dict) -> list[ParsedPerson]:
    """Convierte una respuesta de la API en personas canónicas (función pura, sin red)."""
    items = payload.get("data") if isinstance(payload, dict) else payload
    people: list[ParsedPerson] = []
    for record in items or []:
        if not isinstance(record, dict):
            continue
        full_name = (record.get("nombreCompleto") or "").strip()
        if not full_name:
            continue
        slug = record.get("slug") or hashlib.sha256(
            json.dumps(record, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:24]
        condicion = (record.get("condicion") or "").lower()
        observaciones = record.get("observaciones") or None
        status = "deceased" if any(h in condicion for h in DECEASED_HINTS) else "found"
        fuente = record.get("fuente") or {}
        people.append(
            ParsedPerson(
                source_slug=SOURCE_SLUG,
                external_id=str(slug),
                content_hash=hashlib.sha256(
                    json.dumps(record, sort_keys=True, default=str).encode("utf-8")
                ).hexdigest(),
                full_name=full_name[:240],
                given_name=None,
                family_name=None,
                age=None,
                sex=None,
                last_known_location=record.get("direccion") or record.get("lugarNombre"),
                home_location=record.get("lugarNombre"),
                person_status=status,
                description=observaciones,
                source_name=(fuente.get("nombre") if isinstance(fuente, dict) else None) or "Localizados Venezuela",
                source_url=f"{SITE_BASE}/localizados/{slug}",
                source_date=_parse_dt(record.get("publicadoEn")),
                is_minor=_looks_minor(f"{full_name} {observaciones or ''}"),
                attribution=ATTRIBUTION,
            )
        )
    return people
