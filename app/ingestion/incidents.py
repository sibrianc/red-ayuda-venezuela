"""Fuentes públicas para daños estructurales e incidentes verificables.

Dos clases de evidencia permanecen separadas:

* HOT fAIr / OCHA HDX: señal satelital candidata, nunca confirmación en terreno.
* Lista periodística nominal: colapso reportado/corroborado, sin inferir víctimas.

Ninguna estructura se convierte automáticamente en "personas atrapadas".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import unicodedata
import urllib.request

from app.ingestion.connectors import _ssl_context, in_venezuela_region


HDX_DATASET_URL = (
    "https://data.humdata.org/dataset/"
    "venezuela-m-7-5-earthquake-building-damage-assessment"
)
HDX_RESOURCE_URL = (
    "https://data.humdata.org/dataset/96d4c883-4e65-44fe-80b8-9ca709c91ca6/"
    "resource/58c8f34f-f1a3-4e5e-94b8-b3c123d8ad16/download/"
    "fair_damage_points.geojson"
)
COLLAPSE_LIST_URL = (
    "https://elestimulo.com/terremoto-en-venezuela/2026-06-25/"
    "la-guaira-edificios-colapsados/"
)
USER_AGENT = "RedAyudaVE/1.0 (datos-humanitarios; contacto=admin@redayudave.org)"


@dataclass(frozen=True)
class ParsedIncident:
    source_slug: str
    external_id: str
    content_hash: str
    category: str
    severity: str
    label: str
    address_public: str | None
    latitude: float | None
    longitude: float | None
    status: str
    verification_status: str
    situation_note: str | None
    source_name: str
    source_url: str
    source_date: datetime | None
    attribution: str
    confidence: float | None = None
    location_precision: str = "approximate"
    area_radius_m: int | None = None
    people_trapped_status: str = "unknown"
    people_trapped_count: int | None = None


def fetch_hdx_damage(timeout: int = 30) -> dict:
    """Descarga el GeoJSON público de HOT/OCHA HDX."""
    request = urllib.request.Request(
        HDX_RESOURCE_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json, application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        return json.load(response)


def parse_hdx_damage_geojson(payload: dict) -> list[ParsedIncident]:
    """Normaliza cada punto HOT sin elevar una predicción a hecho confirmado."""
    category_meta = {
        "destroyed": (
            "destroyed_structure_candidate",
            "high",
            "Posible estructura destruida",
        ),
        "major-damage": ("major_damage_candidate", "medium", "Posible daño estructural mayor"),
        "minor-damage": ("minor_damage_candidate", "low", "Posible daño estructural menor"),
    }
    parsed: list[ParsedIncident] = []
    for feature in payload.get("features", []) if isinstance(payload, dict) else []:
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        damage = str(properties.get("damage") or "").strip().lower()
        if geometry.get("type") != "Point" or damage not in category_meta:
            continue
        try:
            longitude, latitude = float(coordinates[0]), float(coordinates[1])
            confidence = float(properties.get("confidence"))
        except (IndexError, TypeError, ValueError):
            continue
        if not in_venezuela_region(latitude, longitude) or not 0 <= confidence <= 1:
            continue
        external_id = str(properties.get("id") or "").strip()
        if not external_id:
            external_id = hashlib.sha256(
                f"{latitude:.7f}:{longitude:.7f}:{damage}".encode("utf-8")
            ).hexdigest()[:24]
        category, severity, label = category_meta[damage]
        canonical = {
            "id": external_id,
            "damage": damage,
            "confidence": round(confidence, 4),
            "latitude": round(latitude, 7),
            "longitude": round(longitude, 7),
            "schema": "2026-06-29-v2",
        }
        parsed.append(
            ParsedIncident(
                source_slug="hot-fair-damage",
                external_id=external_id,
                content_hash=hashlib.sha256(
                    json.dumps(canonical, sort_keys=True).encode("utf-8")
                ).hexdigest(),
                category=category,
                severity=severity,
                label=f"Evaluación estructural #{external_id}",
                address_public="La Guaira · punto de evaluación satelital",
                latitude=latitude,
                longitude=longitude,
                status="active",
                verification_status="candidate",
                situation_note=(
                    "Predicción sobre imagen posterior al sismo; requiere validación en terreno. "
                    "No confirma ocupantes ni personas atrapadas."
                ),
                source_name="HOT fAIr / OCHA HDX",
                source_url=HDX_DATASET_URL,
                source_date=datetime(2026, 6, 27, tzinfo=timezone.utc),
                attribution="HOT fAIr · CC BY 4.0 · imagen Vantor WorldView-3",
                confidence=confidence,
                location_precision="satellite_point",
                area_radius_m=35,
            )
        )
    return parsed


# Lista nominal publicada por El Estímulo. Es parcial y no oficial. Se conserva tal
# cual, con sectores solo cuando la propia cobertura los identifica. No se geocodifica
# de forma inventada: sin coordenada verificable, el registro vive en el directorio.
_COLLAPSED_STRUCTURES = (
    ("Hotel Eduard’s", "Macuto"),
    ("Portofino", None),
    ("Rocapark", None),
    ("Bahía Mar", None),
    ("Rita Sol Palace", None),
    ("Residencias Mariola", "Macuto"),
    ("Residencias Maribel", None),
    ("Gran Terraza", None),
    ("Breogan", None),
    ("Residencias Caribe", None),
    ("La Trinidad", None),
    ("Rosanday", None),
    ("Costa Brava", None),
    ("Residencia Llona", None),
    ("Miramar", None),
    ("La Mar Suites", None),
    ("Oasis Beach", "Playa Grande / Catia La Mar"),
    ("Parque Caraballeda", "Caraballeda"),
    ("Coral Beach", None),
    ("Albatros", None),
    ("Los Corales", "Los Corales"),
    ("Golf Mar", None),
    ("Punta Brisas", "Playa Grande / Catia La Mar"),
    ("Punta Brava", "Playa Grande / Catia La Mar"),
    ("La Gabarra", None),
    ("Pez Vela", None),
    ("Vistamar", None),
    ("Mariana Grande", None),
    ("Mariana Mar", None),
    ("Misión Vivienda Los Cocos", "Los Cocos"),
    ("Tahiti", "Caraballeda"),
    ("Los Delfines", "Playa Grande"),
    ("Bello Horizonte", "Playa Grande"),
    ("La Llovizna", "Playa Grande"),
    ("Urbanización Misión Vivienda Hugo Chávez", "La Guaira"),
    ("Coral Bella", None),
    ("Residencias Club de Playa", "Macuto"),
    ("Las Palmas", None),
    ("Bucanero", None),
    ("La Estrella", None),
    ("Canes", "Catia La Mar"),
)


def _slug(value: str) -> str:
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    ).lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def curated_collapsed_structures() -> list[ParsedIncident]:
    """Devuelve la lista nominal publicada, sin inventar coordenadas ni víctimas."""
    records: list[ParsedIncident] = []
    source_date = datetime(2026, 6, 25, tzinfo=timezone.utc)
    for name, sector in _COLLAPSED_STRUCTURES:
        canonical = {
            "name": name,
            "sector": sector,
            "source_date": source_date.isoformat(),
            "schema": "2026-06-29-v2",
        }
        records.append(
            ParsedIncident(
                source_slug="el-estimulo-collapse-list",
                external_id=_slug(name),
                content_hash=hashlib.sha256(
                    json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")
                ).hexdigest(),
                category="collapsed_structure",
                severity="high",
                label=name,
                address_public=(
                    f"{sector}, La Guaira · ubicación exacta pendiente"
                    if sector and sector != "La Guaira"
                    else "La Guaira · ubicación exacta pendiente"
                ),
                latitude=None,
                longitude=None,
                status="reported",
                verification_status="reported",
                situation_note="Colapso total o parcial incluido en una lista periodística no oficial.",
                source_name="El Estímulo",
                source_url=COLLAPSE_LIST_URL,
                source_date=source_date,
                attribution="El Estímulo · lista parcial publicada el 25 jun 2026",
                location_precision="area",
                people_trapped_status="unknown",
            )
        )
    return records
