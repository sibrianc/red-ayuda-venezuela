"""SEO y compartibilidad: URLs canónicas, alternativas de idioma, datos
estructurados (JSON-LD) y propagación automática a buscadores vía IndexNow.

Las URLs absolutas se construyen sobre ``SITE_URL`` (config) cuando está fijado,
con *fallback* al host de la petición. Así los canónicos/Open Graph apuntan
siempre al dominio público, no al host interno del proxy.
"""

from __future__ import annotations

import json
import logging
import ssl
import urllib.request
from urllib.parse import urlencode

from flask import current_app, request, url_for

from app.i18n import DEFAULT_LOCALE, LANGUAGES, current_locale

logger = logging.getLogger(__name__)

# Locale de Open Graph por idioma del sitio (audiencia principal: Venezuela).
_OG_LOCALES = {"es": "es_VE", "en": "en_US"}
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"


def canonical_base() -> str:
    """Base absoluta del sitio sin barra final (``https://redayudave.org``).

    Usa ``SITE_URL`` si está configurado; si no, el host de la petición actual.
    """
    base = (current_app.config.get("SITE_URL") or "").rstrip("/")
    if base:
        return base
    return request.host_url.rstrip("/") if request else ""


def absolute_url(path: str) -> str:
    """Convierte una ruta relativa en absoluta sobre la base canónica."""
    if path.startswith(("http://", "https://")):
        return path
    return f"{canonical_base()}{path}"


def canonical_url() -> str:
    """Canónica de la página actual: base + path, SIN query (consolida duplicados)."""
    return f"{canonical_base()}{request.path}"


def alternate_links() -> list[dict]:
    """Enlaces hreflang por idioma + ``x-default`` (mismo path con ``?lang=``)."""
    base = canonical_base()
    path = request.path
    links = [
        {"hreflang": code, "href": f"{base}{path}?{urlencode({'lang': code})}"}
        for code in LANGUAGES
    ]
    links.append({"hreflang": "x-default", "href": f"{base}{path}"})
    return links


def og_locale() -> str:
    return _OG_LOCALES.get(current_locale(), _OG_LOCALES[DEFAULT_LOCALE])


def og_locale_alternates() -> list[str]:
    return [v for k, v in _OG_LOCALES.items() if k != current_locale()]


def og_image_url() -> str:
    return absolute_url(url_for("static", filename="icons/og-image.png"))


def jsonld() -> str:
    """JSON-LD Organization + WebSite (con SearchAction para la caja de búsqueda)."""
    base = canonical_base()
    name = current_app.config.get("APP_NAME", "Red de Ayuda Venezuela")
    home = f"{base}/"
    graph = [
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": name,
            "url": home,
            "logo": absolute_url(url_for("static", filename="icons/apple-touch-icon.png")),
            "description": (
                "Panorama humanitario público del terremoto de Venezuela: mapa de "
                "servicios, edificios y daños, personas y coordinación de rescate."
            ),
        },
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": name,
            "url": home,
            "inLanguage": list(LANGUAGES.keys()),
            "potentialAction": {
                "@type": "SearchAction",
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": f"{base}/directorio/personas?q={{search_term_string}}",
                },
                "query-input": "required name=search_term_string",
            },
        },
    ]
    return json.dumps(graph, ensure_ascii=False)


# --- Propagación automática a buscadores (IndexNow: Bing, Yandex, Seznam…) ----

def _indexnow_payload(urls: list[str]):
    key = (current_app.config.get("INDEXNOW_KEY") or "").strip()
    base = (current_app.config.get("SITE_URL") or "").rstrip("/")
    if not key or not base or not urls:
        return None
    host = base.split("://", 1)[-1].split("/", 1)[0]
    return {
        "host": host,
        "key": key,
        "keyLocation": f"{base}/.well-known/indexnow/{key}.txt",
        "urlList": list(dict.fromkeys(urls)),  # dedupe preservando orden
    }


def submit_to_indexnow(urls: list[str]) -> bool:
    """Avisa a IndexNow (Bing/Yandex) de URLs nuevas o actualizadas.

    *Best-effort*: no lanza excepciones y es no-op si falta ``INDEXNOW_KEY`` o
    ``SITE_URL``. Usa urllib + certifi como el resto de la ingesta.
    """
    payload = _indexnow_payload(urls)
    if payload is None:
        return False
    try:
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        context = ssl.create_default_context()
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        INDEXNOW_ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8, context=context) as resp:
            ok = 200 <= resp.status < 300
            logger.info("IndexNow: %s URLs enviadas, HTTP %s", len(payload["urlList"]), resp.status)
            return ok
    except Exception as exc:  # noqa: BLE001 — propagación es best-effort
        logger.warning("IndexNow falló (se ignora): %s", exc)
        return False


def public_hub_urls() -> list[str]:
    """URLs absolutas de los hubs públicos a anunciar cuando cambia el contenido."""
    base = (current_app.config.get("SITE_URL") or "").rstrip("/")
    if not base:
        return []
    paths = [
        "/",
        "/directorio",
        "/directorio/personas",
        "/directorio/incidentes",
        "/directorio/servicios",
        "/directorio/zonas",
        "/directorio/mascotas",
        "/coordinacion",
        "/sitemap.xml",
    ]
    return [f"{base}{p}" for p in paths]


def init_app(app) -> None:
    """Expone helpers a las plantillas y registra el comando CLI de IndexNow."""

    @app.context_processor
    def _inject_seo():
        return {
            "canonical_url": canonical_url,
            "alternate_links": alternate_links,
            "og_image_url": og_image_url,
            "og_locale": og_locale,
            "og_locale_alternates": og_locale_alternates,
            "seo_jsonld": jsonld,
            "site_url": app.config.get("SITE_URL", ""),
            "google_site_verification": app.config.get("GOOGLE_SITE_VERIFICATION", ""),
            "bing_site_verification": app.config.get("BING_SITE_VERIFICATION", ""),
        }

    @app.cli.command("indexnow-submit")
    def indexnow_submit():  # pragma: no cover - utilidad de línea de comandos
        """Anuncia los hubs públicos a IndexNow (Bing/Yandex)."""
        urls = public_hub_urls()
        if not urls:
            print("IndexNow no configurado (faltan SITE_URL o INDEXNOW_KEY).")
            return
        ok = submit_to_indexnow(urls)
        print(f"IndexNow: {'enviado' if ok else 'no enviado'} ({len(urls)} URLs).")
