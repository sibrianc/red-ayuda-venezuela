"""Importador PFIF (People Finder Interchange Format).

PFIF es el estándar abierto para datos de personas desaparecidas/localizadas
(Google Person Finder, Cruz Roja, medios). Permite AGREGAR información ya
publicada para reunificación familiar.

El parseo es agnóstico al namespace (por nombre local de etiqueta), así soporta
PFIF 1.1–1.4: nombre como `full_name`, o `given_name`/`family_name` (1.4), o
`first_name`/`last_name` (≤1.3). El estado de la persona viene de las notas
(`status`: information_sought, believed_alive, believed_missing, believed_dead…).

Sin dependencias nuevas: librería estándar (xml.etree + urllib). Úsese con feeds
de confianza; el contenido se mantiene privado hasta su proyección pública, y los
menores se excluyen de las vistas públicas.
"""

from __future__ import annotations

import hashlib
import json
import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone

USER_AGENT = "RedAyudaVE/pfif-import (proyecto humanitario)"

STATUS_MAP = {
    "believed_dead": "deceased",
    "believed_alive": "found",
    "is_note_author": "found",
    "believed_missing": "missing",
    "information_sought": "missing",
}


@dataclass(frozen=True)
class ParsedPerson:
    source_slug: str
    external_id: str
    content_hash: str
    full_name: str
    given_name: str | None
    family_name: str | None
    age: int | None
    sex: str | None
    last_known_location: str | None
    home_location: str | None
    person_status: str
    description: str | None
    source_name: str | None
    source_url: str | None
    source_date: datetime | None
    is_minor: bool
    attribution: str | None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_age(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(value.strip()[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _status_from_notes(person_notes: list[dict]) -> str:
    dated = [
        (note.get("source_date") or note.get("entry_date") or "", note.get("status"))
        for note in person_notes
        if note.get("status")
    ]
    if not dated:
        return "missing"
    dated.sort()  # las fechas ISO ordenan cronológicamente; la última es la más reciente
    return STATUS_MAP.get(str(dated[-1][1]).casefold(), "missing")


def _home_location(fields: dict) -> str | None:
    parts = [fields.get(key) for key in ("home_city", "home_state", "home_country")]
    joined = ", ".join(part for part in parts if part)
    return joined or None


def fetch_pfif(url: str, *, timeout: int = 30) -> str:
    """Descarga un documento PFIF. Requiere red; no se llama en pruebas."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    context = _ssl_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_pfif(xml_text: str, *, source_slug: str = "pfif", attribution: str | None = None) -> list[ParsedPerson]:
    """Convierte un documento PFIF en personas canónicas (función pura, sin red)."""
    root = ET.fromstring(xml_text)  # feeds de confianza
    persons: dict[str, dict] = {}
    notes: dict[str, list[dict]] = {}

    for element in root:
        name = _local(element.tag)
        if name == "person":
            fields: dict[str, str] = {}
            person_notes: list[dict] = []
            for child in element:
                cname = _local(child.tag)
                if cname == "note":
                    person_notes.append({_local(g.tag): (g.text or "").strip() for g in child})
                else:
                    fields[cname] = (child.text or "").strip()
            pid = fields.get("person_record_id")
            if not pid:
                continue
            persons[pid] = fields
            if person_notes:
                notes.setdefault(pid, []).extend(person_notes)
        elif name == "note":
            note_fields = {_local(g.tag): (g.text or "").strip() for g in element}
            pid = note_fields.get("person_record_id")
            if pid:
                notes.setdefault(pid, []).append(note_fields)

    people: list[ParsedPerson] = []
    for pid, fields in persons.items():
        given = fields.get("given_name") or fields.get("first_name") or None
        family = fields.get("family_name") or fields.get("last_name") or None
        full_name = fields.get("full_name") or " ".join(p for p in (given, family) if p).strip()
        if not full_name:
            continue
        age = _parse_age(fields.get("age"))
        person_notes = notes.get(pid, [])
        people.append(
            ParsedPerson(
                source_slug=source_slug,
                external_id=pid,
                content_hash=hashlib.sha256(
                    json.dumps(
                        {"fields": fields, "notes": person_notes},
                        sort_keys=True,
                        default=str,
                    ).encode("utf-8")
                ).hexdigest(),
                full_name=full_name[:240],
                given_name=given,
                family_name=family,
                age=age,
                sex=fields.get("sex") or None,
                last_known_location=fields.get("last_known_location") or None,
                home_location=_home_location(fields),
                person_status=_status_from_notes(person_notes),
                description=fields.get("description") or fields.get("other") or None,
                source_name=fields.get("source_name") or None,
                source_url=fields.get("source_url") or None,
                source_date=_parse_dt(fields.get("source_date")),
                is_minor=age is not None and age < 18,
                attribution=attribution,
            )
        )
    return people
