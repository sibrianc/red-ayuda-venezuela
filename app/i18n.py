"""i18n ligero y sin dependencias (ES por defecto, EN como traducción).

El idioma fuente es **español**: las claves del catálogo SON el texto en español, así
que cualquier cadena aún sin traducir cae de forma natural al español (despliegue
gradual). El idioma se resuelve por `?lang=` (que fija una cookie), luego la cookie, y
si no, el idioma por defecto. No requiere compilar catálogos ni dependencias externas.
"""

from urllib.parse import urlencode

from flask import g, request
from markupsafe import escape

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
        "Explorar": "Explore",
        "Preferencias": "Preferences",
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
        # --- formularios: etiquetas de campo ---
        "¿En qué zona ocurre?": "In what area is it happening?",
        "Referencia o dirección para el equipo (privada y opcional)": "Reference or address for the team (private and optional)",
        "Latitud aproximada (opcional)": "Approximate latitude (optional)",
        "Longitud aproximada (opcional)": "Approximate longitude (optional)",
        "Cuéntanos qué ocurre y qué se necesita": "Tell us what is happening and what is needed",
        "Información adicional solo para el equipo": "Additional information only for the team",
        "Tu nombre (de quien hace el reporte)": "Your name (of the person filing the report)",
        "Teléfono o correo donde podamos contactarte": "Phone or email where we can reach you",
        "Entiendo que el reporte será revisado y que no debo incluir datos sensibles en la descripción pública.":
            "I understand the report will be reviewed and that I must not include sensitive data in the public description.",
        "Dejar vacío": "Leave empty",
        "Enviar reporte de forma segura": "Submit report securely",
        "Nombre de la persona desaparecida": "Name of the missing person",
        "Apellido de la persona desaparecida": "Surname of the missing person",
        "Edad aproximada de la persona": "Approximate age of the person",
        "Género de la persona (opcional)": "Person's gender (optional)",
        "Prefiero no indicar": "Prefer not to say",
        "Femenino": "Female",
        "Masculino": "Male",
        "Otro": "Other",
        "Otra": "Other",
        "Fecha aproximada del último contacto con la persona": "Approximate date of last contact with the person",
        "¿Dónde se le vio por última vez?": "Where was it last seen?",
        "Descripción de la persona (estatura, contextura, ropa, señas particulares)":
            "Description of the person (height, build, clothing, distinguishing marks)",
        "Relación con la persona (privado)": "Relationship to the person (private)",
        "Información médica necesaria para revisión (privada)": "Medical information needed for review (private)",
        "La persona es menor de edad": "The person is a minor",
        "Resumen de la necesidad": "Summary of the need",
        "Necesidad principal": "Main need",
        "Atención médica o medicamentos": "Medical care or medicines",
        "Agua": "Water",
        "Alimentos": "Food",
        "Refugio": "Shelter",
        "Transporte": "Transport",
        "Rescate": "Rescue",
        "Personas afectadas": "People affected",
        "Hay menores, adultos mayores o personas con discapacidad": "There are minors, older adults or people with disabilities",
        "Necesidad médica": "Medical need",
        "Necesidad de agua": "Water need",
        "Necesidad de alimentos": "Food need",
        "Necesidad de refugio": "Shelter need",
        "Necesidad de transporte": "Transport need",
        "Detalles médicos (privados)": "Medical details (private)",
        "Resumen del recurso que ofreces": "Summary of the resource you offer",
        "Tipo de recurso": "Resource type",
        "Voluntariado": "Volunteering",
        "Cantidad o capacidad": "Quantity or capacity",
        "Disponibilidad": "Availability",
        "Edificio o lugar afectado que quieres reportar": "Building or place affected you want to report",
        "Nivel aparente de daño": "Apparent level of damage",
        "No determinado": "Undetermined",
        "Bajo": "Low",
        "Medio": "Medium",
        "Alto": "High",
        "Crítico": "Critical",
        "Necesita agua": "Needs water",
        "Necesita alimentos": "Needs food",
        "Necesita atención médica": "Needs medical care",
        "Necesita refugio": "Needs shelter",
        "Necesita transporte": "Needs transport",
        "Nombre o identificación de la mascota": "Pet name or identification",
        "Tipo de animal": "Type of animal",
        "Perro": "Dog",
        "Gato": "Cat",
        "Ave": "Bird",
        "Raza (opcional)": "Breed (optional)",
        "Color y señas (opcional)": "Color and markings (optional)",
        "Fecha aproximada en que se perdió": "Approximate date it went missing",
        "Enlace a una foto (opcional)": "Link to a photo (optional)",
        "Pega un enlace https directo a una imagen (.jpg, .png, .webp o .gif).":
            "Paste a direct https link to an image (.jpg, .png, .webp or .gif).",
        "Descripción de la mascota (tamaño, señas, collar, comportamiento)":
            "Description of the pet (size, markings, collar, behavior)",
        "¿Qué zona está sin comunicación?": "Which area is without communication?",
        "¿Qué se sabe? (sin nombres ni datos personales)": "What is known? (no names or personal data)",
        "Tu contacto (privado y opcional, por si necesitamos corroborar)": "Your contact (private and optional, in case we need to corroborate)",
        "Entiendo que es un reporte sin verificar y que no debo incluir datos personales públicos.":
            "I understand this is an unverified report and that I must not include public personal data.",
        "Reportar zona sin comunicación": "Report area without communication",
        "Motivo": "Reason",
        "Información posiblemente falsa": "Possibly false information",
        "Expone información sensible": "Exposes sensitive information",
        "Posible fraude o estafa": "Possible fraud or scam",
        "El caso ya fue resuelto": "The case has already been resolved",
        "Detalles": "Details",
        "Contacto opcional (privado)": "Optional contact (private)",
        "Enviar reporte de abuso": "Submit abuse report",
        # --- formularios: títulos (rutas) y chrome del asistente ---
        "Reportar persona sin contacto": "Report a person out of contact",
        "Ofrecer ayuda o recursos": "Offer help or resources",
        "Reportar una zona afectada": "Report an affected area",
        "Reportar mascota desaparecida": "Report a lost pet",
        "Reporte protegido": "Protected report",
        "Inicio": "Home",
        "Te guiaremos paso a paso. Solo pedimos la información necesaria para que una persona pueda revisar el caso.":
            "We'll guide you step by step. We only ask for the information needed for a person to review the case.",
        "Privado hasta ser revisado": "Private until reviewed",
        "Tu contacto, dirección y detalles sensibles nunca aparecen en el sitio público.":
            "Your contact, address and sensitive details never appear on the public site.",
        "¿Conexión inestable?": "Unstable connection?",
        "Puedes guardar en este dispositivo únicamente los campos no sensibles.":
            "You can save only the non-sensitive fields on this device.",
        "Guardar borrador": "Save draft",
        "Borrar": "Delete",
        "Revisa la información marcada.": "Check the highlighted information.",
        "Conservamos lo que escribiste para que puedas corregirlo.": "We keep what you wrote so you can correct it.",
        "Progreso del reporte": "Report progress",
        "Situación": "Situation",
        "Ubicación": "Location",
        "Contacto": "Contact",
        "Paso 1 de 3": "Step 1 of 3",
        "Cuéntanos la situación": "Tell us the situation",
        "Empieza por lo esencial. Podrás añadir detalles antes de enviar.": "Start with the essentials. You can add details before submitting.",
        "Si no la sabes, puedes dejarla vacía.": "If you don't know it, you can leave it empty.",
        "Una fecha aproximada también ayuda.": "An approximate date also helps.",
        "Ejemplo: Agua para 20 familias en Caraballeda.": "Example: Water for 20 families in Caraballeda.",
        "Una estimación es suficiente.": "An estimate is enough.",
        "También se necesita": "Also needed",
        "Ejemplo: Excavadora con operador disponible.": "Example: Excavator with operator available.",
        "Indica unidad: litros, raciones, plazas o equipos.": "Specify unit: liters, rations, spots or equipment.",
        "Ejemplo: Disponible hoy de 8:00 a 18:00.": "Example: Available today from 8:00 to 18:00.",
        "Ejemplo: Edificios dañados en el sector central.": "Example: Damaged buildings in the central sector.",
        "Necesidades observadas": "Observed needs",
        "Nombre o cómo identificarla.": "Name or how to identify it.",
        "Enlace https directo a una imagen (.jpg, .png, .webp). Opcional.": "Direct https link to an image (.jpg, .png, .webp). Optional.",
        "Paso 2 de 3": "Step 2 of 3",
        "¿Dónde ocurre?": "Where is it happening?",
        "Escribe una zona reconocible. No necesitas conocer coordenadas.": "Enter a recognizable area. You don't need to know coordinates.",
        "Sector, comunidad, parroquia o punto de referencia general.": "Sector, community, parish or general landmark.",
        "Ubicación asistida": "Assisted location",
        "Si estás en el lugar, tu dispositivo puede añadir la ubicación. Solo el equipo autorizado recibe la precisión original.":
            "If you are on site, your device can add the location. Only the authorized team receives the original precision.",
        "Usar mi ubicación": "Use my location",
        "No se ha añadido ubicación del dispositivo.": "No device location has been added.",
        "Añadir una referencia privada para el equipo": "Add a private reference for the team",
        "No se mostrará en el mapa ni en reportes públicos.": "It will not be shown on the map or in public reports.",
        "Paso 3 de 3": "Step 3 of 3",
        "Detalles y contacto": "Details and contact",
        "Una persona revisará el reporte antes de que cualquier parte pueda publicarse.":
            "A person will review the report before any part can be published.",
        "No incluyas teléfonos, nombres completos ni direcciones exactas.": "Do not include phone numbers, full names or exact addresses.",
        "Añadir información privada para la revisión": "Add private information for the review",
        "Contacto privado": "Private contact",
        "¿Cómo podemos confirmar el reporte?": "How can we confirm the report?",
        "Estos datos solo son visibles para personal autorizado.": "These details are only visible to authorized staff.",
        "Teléfono, WhatsApp o correo.": "Phone, WhatsApp or email.",
        "Al enviar": "On submit",
        "El reporte quedará pendiente y privado hasta que una persona lo revise.":
            "The report will remain pending and private until a person reviews it.",
        "Continuar a ubicación": "Continue to location",
        "Volver": "Back",
        "Continuar a contacto": "Continue to contact",
        "Volver al inicio": "Back to home",
        "Privado": "Private",
        # --- confirmación / abuso / flashes ---
        "Reporte recibido": "Report received",
        "Gracias. Ahora comienza la revisión.": "Thank you. The review now begins.",
        "Tu referencia es": "Your reference is",
        "El reporte permanece privado hasta que una persona autorizada lo revise.":
            "The report stays private until an authorized person reviews it.",
        "Revisión comunitaria": "Community review",
        "Reportar un problema": "Report a problem",
        "El contenido no se eliminará automáticamente. Una persona autorizada revisará el aviso.":
            "Content will not be removed automatically. An authorized person will review the notice.",
        "Gracias. Tu reporte de zona sin comunicación fue recibido como alerta sin verificar.":
            "Thank you. Your report of an area without communication was received as an unverified alert.",
        # --- reportes: listado y detalle ---
        "Información pública revisada": "Reviewed public information",
        "Reportes aprobados": "Approved reports",
        "La información puede estar incompleta o cambiar. No se muestran contactos ni direcciones exactas.":
            "Information may be incomplete or change. Contacts and exact addresses are not shown.",
        "Volver a reportes": "Back to reports",
        # --- reconocimientos ---
        "Reconocimientos": "Recognition",
        "Gratitud": "Gratitude",
        "Honramos a las unidades de rescate y a los perros rescatistas que ayudaron tras el sismo. Información de fuentes oficiales, con atribución.":
            "We honor the rescue units and rescue dogs that helped after the earthquake. Information from official sources, with attribution.",
        "Por respeto a la privacidad, las personas se reconocen a nivel de unidad u organización, sin datos personales.":
            "Out of respect for privacy, people are recognized at the unit or organization level, without personal data.",
        "¿Una atribución es incorrecta?": "Is an attribution incorrect?",
        "Avísanos": "Let us know",
        "Unidades de rescate": "Rescue units",
        "Unidades y organizaciones": "Units and organizations",
        "Perros rescatistas": "Rescue dogs",
        "Perro rescatista": "Rescue dog",
        "Aún no hay unidades publicadas. Se añadirán desde fuentes oficiales.":
            "No units published yet. They will be added from official sources.",
        "Aún no hay perros publicados. Se añadirán desde fuentes oficiales.":
            "No dogs published yet. They will be added from official sources.",
        # --- directorio: subpáginas ---
        "Personas · Reunificación familiar": "People · Family reunification",
        "Buscar personas": "Search people",
        "Desaparecidas, localizadas y fallecidas — publicadas por fuentes identificadas. Menores excluidos por protección.":
            "Missing, located and deceased — published by identified sources. Minors excluded for protection.",
        "Prioridad: las personas": "Priority: people",
        "Reportar un familiar": "Report a relative",
        "Desaparecidas": "Missing",
        "Localizadas": "Located",
        "Fallecidas": "Deceased",
        "Personas desaparecidas": "Missing people",
        "Personas localizadas": "Located people",
        "Personas fallecidas": "Deceased people",
        "Incidentes y evaluación estructural": "Incidents and structural assessment",
        "Colapsos corroborados y evaluaciones satelitales pendientes. Un edificio dañado nunca implica automáticamente que haya personas atrapadas.":
            "Corroborated collapses and pending satellite assessments. A damaged building never automatically implies trapped people.",
        "Todos": "All",
        "Servicios y recursos": "Services and resources",
        "Servicios disponibles": "Available services",
        "Hospitales, refugios, agua, farmacias, combustible y víveres (OpenStreetMap). Filtra por tipo y abre cómo llegar en Google Maps.":
            "Hospitals, shelters, water, pharmacies, fuel and supplies (OpenStreetMap). Filter by type and open directions in Google Maps.",
        "Cómo llegar": "Directions",
        "Ver fuente": "View source",
        "Consultar fuente": "View source",
        "Alertas": "Alerts",
        "Posibles víctimas que no pueden pedir ayuda. Son alertas sin verificar para que los equipos prioricen evaluar la zona.":
            "Possible victims who cannot ask for help. These are unverified alerts so teams prioritize assessing the area.",
        "Reportar zona sin comunicación": "Report area without communication",
        "Mascotas desaparecidas": "Lost pets",
        "Mascotas perdidas reportadas por la comunidad tras el sismo. Los datos del dueño se mantienen privados.":
            "Lost pets reported by the community after the earthquake. The owner's data is kept private.",
        "Reportes de la comunidad y registros publicados por fuentes verificadas de rescate animal. Los datos del dueño se mantienen privados.":
            "Community reports and records published by verified animal rescue sources. The owner's data is kept private.",
        "Reportar mascota": "Report a pet",
        "Visto en": "Seen at",
        "Desde": "Since",
        "Última ubicación": "Last location",
        "Último contacto": "Last contact",
        "Localizada": "Located",
        "Registro publicado": "Published record",
        "Cifra oficial reportada:": "Official reported figure:",
        "Solo se listan nombres ya publicados por fuentes identificadas.": "Only names already published by identified sources are listed.",
        "Fuente: reporte recibido y revisado por esta plataforma": "Source: report received and reviewed by this platform",
        "años": "years old",
        "No hay personas en esta categoría.": "No people in this category.",
        "Prueba otra pestaña, consulta los registros oficiales o repórtalo con el botón de arriba.":
            "Try another tab, check the official registries or report it with the button above.",
        "No hay incidentes para los filtros actuales.": "No incidents for the current filters.",
        "No hay servicios para los filtros actuales.": "No services for the current filters.",
        "No hay zonas sin comunicación reportadas.": "No areas without communication reported.",
        "Si conoces una, repórtala con el botón de arriba.": "If you know of one, report it with the button above.",
        "No hay mascotas reportadas.": "No pets reported.",
        "Si perdiste o encontraste una, repórtala con el botón de arriba.": "If you lost or found one, report it with the button above.",
        "Fuente: reporte recibido por esta plataforma": "Source: report received by this platform",
        "Ubicación": "Location",
        "Publicado": "Published",
        "Página": "Page",
        "de": "of",
        "← Anterior": "← Previous",
        "Siguiente →": "Next →",
    },
}


def current_locale() -> str:
    return getattr(g, "locale", DEFAULT_LOCALE)


def translate(text: str, **kwargs) -> str:
    locale = current_locale()
    if locale != DEFAULT_LOCALE:
        text = TRANSLATIONS.get(locale, {}).get(text, text)
    return text.format(**kwargs) if kwargs else text


class LazyString:
    """Cadena traducible de forma diferida: se traduce al convertirse a texto, ya dentro
    del contexto de petición (sirve para etiquetas de WTForms, definidas al cargar la clase)."""

    __slots__ = ("_text",)

    def __init__(self, text: str):
        self._text = text

    def __str__(self) -> str:
        return translate(self._text)

    def __html__(self):
        return escape(translate(self._text))

    def __eq__(self, other) -> bool:
        return str(self) == str(other)

    def __hash__(self) -> int:
        return hash(self._text)

    def __bool__(self) -> bool:
        return bool(self._text)

    def __repr__(self) -> str:
        return f"LazyString({self._text!r})"


def lazy(text: str) -> LazyString:
    return LazyString(text)


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
