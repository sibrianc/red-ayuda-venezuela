"""Normalización y clave de coincidencia para deduplicar/verificar personas.

Filosofía (según la advertencia del propietario: "hay gente que podría escribir mal
los nombres"): se usa una clave de coincidencia **conservadora** — normaliza
mayúsculas/minúsculas, acentos, espacios, marcadores de menor y orden de las palabras,
pero NO hace coincidencia difusa (fuzzy) de errores tipográficos. Así evitamos fusionar
por error a personas DISTINTAS. La capa fuzzy, más agresiva, quedaría para revisión humana.

`corroboration` = cuántas FUENTES independientes comparten la misma clave: si dos
plataformas reportan a la misma persona, sube la confianza ("corroborado").
"""

from __future__ import annotations

import re
import unicodedata

_MINOR_MARKERS = re.compile(r"\(\s*(?:ni[ñn][oa]s?\s*menor(?:es)?|menor(?:es)?|beb[eé]|lactante)\s*\)", re.I)


def _strip_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


def normalize_name(value: str | None) -> str:
    """Minúsculas, sin acentos, sin puntuación, sin marcadores de menor, espacios colapsados."""
    if not value:
        return ""
    text = _MINOR_MARKERS.sub(" ", value)
    text = _strip_accents(text).lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def match_key(full_name: str | None) -> str:
    """Clave conservadora de deduplicación: tokens normalizados (>1 letra) ordenados.

    Maneja "Juan Pérez" == "perez juan" == "JUAN PEREZ"; descarta iniciales sueltas.
    No tolera typos a propósito (evita merges incorrectos)."""
    tokens = [token for token in normalize_name(full_name).split() if len(token) > 1]
    return " ".join(sorted(tokens))
