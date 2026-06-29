"""i18n ligero y sin dependencias (ES por defecto, EN como traducción).

El idioma fuente es **español**: las claves del catálogo SON el texto en español, así
que cualquier cadena aún sin traducir cae de forma natural al español (despliegue
gradual). El idioma se resuelve por `?lang=` (que fija una cookie), luego la cookie, y
si no, el idioma por defecto. No requiere compilar catálogos ni dependencias externas.
"""

from urllib.parse import urlencode

from flask import g, request

DEFAULT_LOCALE = "es"
LANGUAGES = {"es": "Español", "en": "English"}

# Catálogo de traducción al inglés. La CLAVE es el texto en español (idioma fuente).
TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # --- base / navegación ---
        "Saltar al contenido": "Skip to content",
        "Esta plataforma no es un servicio oficial de emergencia. Si hay peligro inmediato, busca ayuda local disponible.":
            "This platform is not an official emergency service. If there is immediate danger, seek available local help.",
        "Situación": "Situation",
        "Información": "Information",
        "Mapa": "Map",
        "Directorio": "Directory",
        "Coordinación": "Coordination",
        "Emergencia": "Emergency",
        "Modo sol": "Sunlight mode",
        "Modo ligero": "Light data mode",
        "Cambiar entre modo oscuro y modo para luz solar": "Switch between dark mode and sunlight mode",
        "Crear reporte": "Create report",
        "Administración": "Administration",
        "Salir": "Sign out",
        "Acceso interno": "Internal access",
        "Idioma": "Language",
        "Información humanitaria revisada por personas. Ausencia de reportes no significa ausencia de daño.":
            "Humanitarian information reviewed by people. Absence of reports does not mean absence of harm.",
        "Reportes revisados": "Reviewed reports",
        "Mapa operativo": "Operational map",
        "Privacidad y uso responsable": "Privacy and responsible use",
        # --- home: hero ---
        "Panorama humanitario público": "Public humanitarian overview",
        "Ayuda coordinada para Venezuela": "Coordinated help for Venezuela",
        "Consulta y reporta personas sin contacto, solicitudes de ayuda, recursos y zonas afectadas. Cada dato público conserva fuente, frescura y límites de privacidad claros.":
            "Search and report people out of contact, help requests, resources and affected areas. Every public record keeps its source, freshness and clear privacy limits.",
        "Buscar personas →": "Search people →",
        "Emergencia · 911": "Emergency · 911",
        "Directorio de incidentes y servicios": "Directory of incidents and services",
        "Reportar un familiar": "Report a relative",
        "Ver el mapa vivo": "View the live map",
        "Registros visibles": "Visible records",
        "Atención prioritaria": "Priority attention",
        "Personas sin contacto": "People out of contact",
        "Zonas representadas": "Areas represented",
        "No es un servicio oficial de emergencia. La ausencia de registros no significa ausencia de daño.":
            "This is not an official emergency service. The absence of records does not mean absence of harm.",
        # --- home: acciones ---
        "Reportar": "Report",
        "¿Qué quieres reportar?": "What do you want to report?",
        "Persona sin contacto": "Person out of contact",
        "Reporta a alguien con quien tu familia perdió comunicación.": "Report someone your family lost contact with.",
        "Solicitar ayuda": "Request help",
        "Pide agua, atención médica, alimentos, refugio o transporte.": "Ask for water, medical care, food, shelter or transport.",
        "Ofrecer recurso": "Offer a resource",
        "Comparte albergue, transporte, víveres, equipos o tu tiempo.": "Share shelter, transport, supplies, equipment or your time.",
        "Reportar una zona": "Report an area",
        "Informa daños, edificios colapsados o zonas de peligro.": "Report damage, collapsed buildings or danger zones.",
        "Zona sin comunicación": "Area without communication",
        "Alerta de posibles víctimas incomunicadas en un sector.": "Alert of possible cut-off victims in a sector.",
        "Mascota desaparecida": "Lost pet",
        "Reporta una mascota perdida tras el sismo.": "Report a pet lost after the earthquake.",
        "Comenzar →": "Start →",
        # --- home: cómo funciona / privacidad ---
        "Cómo funciona": "How it works",
        "Tres pasos, con verificación automática": "Three steps, with automatic verification",
        "Envías tu reporte": "You send your report",
        "Completas un formulario simple. Tus datos de contacto quedan privados desde el inicio.":
            "You fill in a simple form. Your contact details stay private from the start.",
        "Limpieza y verificación automática": "Automatic cleaning and verification",
        "El sistema limpia y valida cada reporte al instante, sin esperar a nadie. Lo que no pasa los controles se resguarda en cola, no se pierde.":
            "The system cleans and validates each report instantly, without waiting for anyone. Whatever fails the checks is held in a queue, not lost.",
        "Publicación segura": "Safe publication",
        "Solo aparece lo apto, sin direcciones exactas ni contactos visibles. Los menores nunca se publican.":
            "Only suitable content appears, with no exact addresses or visible contacts. Minors are never published.",
        "Tu privacidad, protegida": "Your privacy, protected",
        "Los contactos, direcciones exactas y notas médicas nunca son públicos.":
            "Contacts, exact addresses and medical notes are never public.",
        "Los reportes que involucran a un menor nunca se publican de forma automática.":
            "Reports involving a minor are never published automatically.",
        "Lo que no pasa la verificación automática se resguarda para revisión; nada se descarta.":
            "Whatever fails automatic verification is held for review; nothing is discarded.",
        "No es un servicio oficial de emergencia. Ante peligro inmediato, marca el 9-1-1.":
            "This is not an official emergency service. In immediate danger, call 9-1-1.",
        # --- home: recientes / CTA ---
        "Actualizaciones": "Updates",
        "Información pública reciente": "Recent public information",
        "Sin registros publicados": "No published records",
        "La estructura está lista; no mostramos datos no verificados.":
            "The structure is ready; we do not show unverified data.",
        "Cuando exista información apta aparecerá aquí, con fuente, fecha y ubicación segura.":
            "When suitable information exists it will appear here, with source, date and safe location.",
        "Consultar todo el listado →": "See the full list →",
        "Cada reporte ayuda a coordinar mejor la respuesta": "Every report helps coordinate the response better",
        "Explora el directorio y el mapa, busca a un familiar o registra un reporte en minutos.":
            "Explore the directory and map, search for a relative or file a report in minutes.",
        "Ver directorio": "View directory",
        "Contactos · 911": "Contacts · 911",
        # --- directorio: chrome compartido (buscador + navegación) ---
        "Buscar persona, edificio, dirección o servicio…": "Search person, building, address or service…",
        "Buscar": "Search",
        "Limpiar": "Clear",
        "Secciones del directorio": "Directory sections",
        "Resumen": "Overview",
        "Personas": "People",
        "Edificios e incidentes": "Buildings and incidents",
        "Servicios": "Services",
        "Zonas sin comunicación": "Areas without communication",
        "Mascotas": "Pets",
        # --- directorio: hub ---
        "Directorio · Reunificación familiar": "Directory · Family reunification",
        "Directorio del terremoto": "Earthquake directory",
        "Elige una sección: personas, edificios e incidentes, servicios o zonas sin comunicación. Cada una con su propia página y buscador.":
            "Choose a section: people, buildings and incidents, services or areas without communication. Each with its own page and search.",
        "Cifras reportadas por fuentes oficiales y en verificación; no son un conteo confirmado.":
            "Figures reported by official sources and under verification; they are not a confirmed count.",
        "Secciones": "Sections",
        "Explora por categoría": "Browse by category",
        "Desaparecidas, localizadas y fallecidas. Busca o reporta a un familiar.":
            "Missing, located and deceased. Search or report a relative.",
        "Colapsos y evaluación estructural, con fuente.": "Collapses and structural assessment, with source.",
        "Hospitales, refugios, agua, farmacias, combustible y víveres.":
            "Hospitals, shelters, water, pharmacies, fuel and supplies.",
        "Alertas de posibles víctimas incomunicadas.": "Alerts of possible cut-off victims.",
        "Mascotas desaparecidas": "Lost pets",
        "Mascotas perdidas (comunidad + fuentes verificadas).": "Lost pets (community + verified sources).",
        "registros · Abrir →": "records · Open →",
        "Registros oficiales de búsqueda y reunificación": "Official search and reunification registries",
        "Por protección, los reportes de menores no aparecen públicamente: se gestionan de forma privada y prioritaria.":
            "For protection, reports involving minors do not appear publicly: they are handled privately and as a priority.",
        # --- contactos ---
        "Red de contacto verificada": "Verified contact network",
        "Contactos de emergencia e instituciones": "Emergency contacts and institutions",
        "Llama o escribe a canales oficiales y colectivos de búsqueda verificados. Esta plataforma no es un servicio oficial de emergencia: ante peligro inmediato, marca el 9-1-1.":
            "Call or message official channels and verified search collectives. This platform is not an official emergency service: in immediate danger, call 9-1-1.",
        "Llamar al 9-1-1": "Call 9-1-1",
        "Buscar a un familiar": "Search for a relative",
        "Los números y enlaces pueden cambiar durante la emergencia; confírmalos localmente. ¿Tienes el contacto verificado de una unidad de rescate o institución que llegó?":
            "Numbers and links may change during the emergency; confirm them locally. Do you have the verified contact of a rescue unit or institution that arrived?",
        "Háznoslo saber": "Let us know",
        "para sumarlo con su fuente.": "to add it with its source.",
        # --- coordinación ---
        "Red de coordinación": "Coordination network",
        "Centro de coordinación": "Coordination center",
        "Buscar en el directorio": "Search the directory",
        "Reportar mascota": "Report a pet",
        "Un solo lugar que conecta a familias, rescatistas y a quienes ofrecen recursos. Las familias reportan y buscan; los equipos ven dónde se necesita ayuda; los recursos se enlazan con las necesidades.":
            "A single place connecting families, rescuers and those offering resources. Families report and search; teams see where help is needed; resources are matched with needs.",
    },
}


def current_locale() -> str:
    return getattr(g, "locale", DEFAULT_LOCALE)


def translate(text: str, **kwargs) -> str:
    locale = current_locale()
    if locale != DEFAULT_LOCALE:
        text = TRANSLATIONS.get(locale, {}).get(text, text)
    return text.format(**kwargs) if kwargs else text


def set_lang_link(lang: str) -> str:
    """URL de la página actual cambiando sólo el idioma (preserva el resto de la query)."""
    args = {key: value for key, value in request.args.items(multi=False)}
    args["lang"] = lang if lang in LANGUAGES else DEFAULT_LOCALE
    return f"{request.path}?{urlencode(args)}"


def init_app(app) -> None:
    @app.before_request
    def _select_locale():
        requested = request.args.get("lang")
        if requested in LANGUAGES:
            g.locale = requested
            g.persist_locale = requested
        else:
            cookie = request.cookies.get("lang")
            g.locale = cookie if cookie in LANGUAGES else DEFAULT_LOCALE

    @app.after_request
    def _persist_locale(response):
        lang = getattr(g, "persist_locale", None)
        if lang:
            response.set_cookie("lang", lang, max_age=31_536_000, samesite="Lax")
        return response

    app.jinja_env.globals["_"] = translate
    app.jinja_env.globals["t"] = translate

    @app.context_processor
    def _inject_i18n():
        return {
            "current_locale": current_locale(),
            "LANGUAGES": LANGUAGES,
            "set_lang_link": set_lang_link,
        }
