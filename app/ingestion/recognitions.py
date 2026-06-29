"""Parser de reconocimientos (unidades de rescate + perros rescatistas) desde una FUENTE
OFICIAL (export JSON), con atribución.

Protección de datos: los humanos se reconocen SOLO a nivel de **unidad/organización**
(sin nombres ni datos personales de individuos). Los **perros** sí con nombre. NUNCA se
inventan datos. La foto se acepta sólo como enlace https a una imagen.

Claves JSON aceptadas (lista o {"recognitions": [...]}), ES/EN:
  name/nombre (obligatorio), kind/tipo (responder_unit|rescue_dog; "perro"/"dog" → perro),
  org/organizacion/pais, role/rol, description/descripcion, photo_url/foto,
  source_name, source_url/url, source_date, id/external_id.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime

_PHOTO_RE = re.compile(r"^https://\S+\.(?:jpe?g|png|webp|gif)(?:\?\S*)?$", re.IGNORECASE)
_DOG_HINTS = {"rescue_dog", "perro", "dog", "canino", "k9", "k-9"}


@dataclass(frozen=True)
class ParsedRecognition:
    source_slug: str
    external_id: str
    content_hash: str
    kind: str
    name: str
    org: str | None
    role: str | None
    description: str | None
    photo_url: str | None
    source_name: str | None
    source_url: str | None
    source_date: datetime | None
    attribution: str | None


def _clean(value):
    value = (str(value).strip() if value is not None else "")
    return value or None


def _kind(value) -> str:
    return "rescue_dog" if str(value or "").strip().lower() in _DOG_HINTS else "responder_unit"


def _valid_photo(value):
    value = _clean(value)
    return value if value and _PHOTO_RE.match(value) else None


def _datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_recognitions_json(text: str, *, source_slug: str, attribution: str | None = None) -> list[ParsedRecognition]:
    data = json.loads(text)
    rows = data.get("recognitions", []) if isinstance(data, dict) else data
    out: list[ParsedRecognition] = []
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
        out.append(
            ParsedRecognition(
                source_slug=source_slug,
                external_id=external_id,
                content_hash=content_hash,
                kind=_kind(row.get("kind") or row.get("tipo")),
                name=name,
                org=_clean(row.get("org") or row.get("organizacion") or row.get("pais")),
                role=_clean(row.get("role") or row.get("rol")),
                description=_clean(row.get("description") or row.get("descripcion")),
                photo_url=_valid_photo(row.get("photo_url") or row.get("foto")),
                source_name=_clean(row.get("source_name")) or attribution,
                source_url=_clean(row.get("source_url") or row.get("url")),
                source_date=_datetime(row.get("source_date")),
                attribution=attribution,
            )
        )
    return out
