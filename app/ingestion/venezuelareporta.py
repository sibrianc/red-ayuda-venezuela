"""Conector a venezuelareporta.org (desaparecidos/localizados).

`venezuelareporta.org` **server-renderiza** las fichas de personas en sus páginas
públicas, y su `robots.txt` permite `/` (solo prohíbe `/api/` y `/admin`). Por eso
parseamos sus páginas públicas (NO su API) — vía limpia y permitida por su política,
para reunificación. Atribución a la fuente; menores excluidos de las vistas públicas.

Nota: el HTML inicial trae el primer lote (~150 fichas). Más allá cargan por `/api/`
(prohibido por su robots), así que solo se toma lo server-rendered y permitido.
"""

from __future__ import annotations

import hashlib
import re
import urllib.request

from app.ingestion.connectors import _ssl_context
from app.ingestion.localizados import _looks_minor
from app.ingestion.pfif import ParsedPerson

BASE = "https://venezuelareporta.org"
SOURCE_SLUG = "venezuela-reporta"
ATTRIBUTION = "Venezuela Reporta (reporte ciudadano, no verificado)"
USER_AGENT = "RedAyudaVE/reunificacion (humanitario; uso=busqueda/reunificacion)"

# Estado por la clase del chip (bg-<estado>-soft) o por texto.
STATUS_MAP = {
    "buscando": "missing",
    "desaparecido": "missing",
    "desaparecida": "missing",
    "salvo": "found",
    "encontrado": "found",
    "encontrada": "found",
    "localizado": "found",
    "localizada": "found",
    "fallecido": "deceased",
    "fallecida": "deceased",
}
GENERIC_LOCATIONS = {"reportado aquí", "reportado aqui", ""}


def fetch_reporta(timeout: int = 30) -> str:
    """Descarga la página pública (server-rendered). Requiere red; no se llama en pruebas."""
    request = urllib.request.Request(BASE + "/", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        return response.read().decode("utf-8", "replace")


def parse_reporta(html: str) -> list[ParsedPerson]:
    """Extrae las fichas server-rendered (función pura, sin red)."""
    people: list[ParsedPerson] = []
    for card in re.split(r'<a class="card', html)[1:]:
        ref = re.search(r'href="/reporte/([a-f0-9\-]{8,})"', card)
        if not ref:
            continue
        uuid = ref.group(1)
        name_match = re.search(r'alt="Foto de ([^"]+)"', card) or re.search(r"<h3[^>]*>([^<]+)</h3>", card)
        if not name_match:
            continue
        name = re.sub(r"\s+", " ", name_match.group(1)).strip()
        if not name:
            continue
        chip = re.search(r"chip bg-([a-z]+)-soft", card)
        status = STATUS_MAP.get(chip.group(1) if chip else "", "missing")
        loc_match = re.search(r"<p[^>]*>([^<]+)</p>", card)
        location = loc_match.group(1).strip() if loc_match else None
        if location and location.lower() in GENERIC_LOCATIONS:
            location = None
        people.append(
            ParsedPerson(
                source_slug=SOURCE_SLUG,
                external_id=uuid,
                content_hash=hashlib.sha256(f"{uuid}{name}{status}".encode("utf-8")).hexdigest(),
                full_name=name[:240],
                given_name=None,
                family_name=None,
                age=None,
                sex=None,
                last_known_location=location,
                home_location=None,
                person_status=status,
                description=None,
                source_name="Venezuela Reporta",
                source_url=f"{BASE}/reporte/{uuid}",
                source_date=None,
                is_minor=_looks_minor(name),
                attribution=ATTRIBUTION,
            )
        )
    return people
