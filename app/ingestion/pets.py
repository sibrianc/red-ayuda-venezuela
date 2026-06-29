"""Parser de mascotas desaparecidas desde una FUENTE verificada (export JSON).

Pensado para ingerir listas ya publicadas por grupos/registros de rescate animal
(p. ej. un export de un grupo verificado), con atribución de la fuente. NUNCA inventa
datos: si no hay una fuente real, no hay registros. La foto se acepta sólo como enlace
https a una imagen (mismo criterio que el formulario público).

Formato JSON aceptado (lista, o {"pets": [...]}). Claves ES/EN:
  name/nombre (obligatorio), species/especie, breed/raza, color,
  location/zona/last_seen, last_seen_date/fecha, photo_url/foto,
  description/descripcion, source_name, source_url/url, source_date, id/external_id.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime

_PHOTO_RE = re.compile(r"^https://\S+\.(?:jpe?g|png|webp|gif)(?:\?\S*)?$", re.IGNORECASE)
_SPECIES = {
    "perro": "dog", "dog": "dog", "can": "dog",
    "gato": "cat", "cat": "cat",
    "ave": "bird", "bird": "bird", "pajaro": "bird",
}


@dataclass(frozen=True)
class ParsedPet:
    source_slug: str
    external_id: str
    content_hash: str
    name: str
    species: str
    breed: str | None
    color: str | None
    last_seen_location: str | None
    last_seen_date: date | None
    photo_url: str | None
    description: str | None
    source_name: str | None
    source_url: str | None
    source_date: datetime | None
    attribution: str | None


def _species(value) -> str:
    return _SPECIES.get(str(value or "").strip().lower(), "other")


def _clean(value):
    value = (str(value).strip() if value is not None else "")
    return value or None


def _valid_photo(value):
    value = _clean(value)
    return value if value and _PHOTO_RE.match(value) else None


def _date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_pets_json(text: str, *, source_slug: str, attribution: str | None = None) -> list[ParsedPet]:
    data = json.loads(text)
    rows = data.get("pets", []) if isinstance(data, dict) else data
    pets: list[ParsedPet] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        name = _clean(row.get("name") or row.get("nombre"))
        if not name:
            continue
        external_id = str(row.get("id") or row.get("external_id") or f"row-{index}")
        content_hash = hashlib.sha256(
            json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        pets.append(
            ParsedPet(
                source_slug=source_slug,
                external_id=external_id,
                content_hash=content_hash,
                name=name,
                species=_species(row.get("species") or row.get("especie")),
                breed=_clean(row.get("breed") or row.get("raza")),
                color=_clean(row.get("color")),
                last_seen_location=_clean(row.get("location") or row.get("zona") or row.get("last_seen")),
                last_seen_date=_date(row.get("last_seen_date") or row.get("fecha")),
                photo_url=_valid_photo(row.get("photo_url") or row.get("foto")),
                description=_clean(row.get("description") or row.get("descripcion")),
                source_name=_clean(row.get("source_name")) or attribution,
                source_url=_clean(row.get("source_url") or row.get("url")),
                source_date=_datetime(row.get("source_date")),
                attribution=attribution,
            )
        )
    return pets
