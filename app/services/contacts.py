"""Red de contacto verificada: instituciones oficiales y colectivos de búsqueda.

Solo canales reales y públicos. No se inventan números ni dominios: cuando no hay
un teléfono o sitio oficial estable y confirmado, se enlaza a una búsqueda del canal
oficial (misma convención que OFFICIAL_REGISTRIES). Las unidades de rescate concretas
se agregan aquí a medida que se verifican con su fuente.
"""


def _search(query: str) -> str:
    from urllib.parse import quote

    return "https://www.google.com/search?q=" + quote(query)


EMERGENCY_GROUPS = [
    {
        "id": "inmediata",
        "title": "Emergencia inmediata",
        "intro": "Si hay vidas en riesgo AHORA, llama. Esta plataforma no es un servicio oficial de emergencia.",
        "items": [
            {
                "name": "Emergencias 9-1-1",
                "role": "Sistema integrado de emergencias (bomberos, policía y ambulancia) en todo el país.",
                "phone": "911",
                "phone_tel": "911",
                "url": None,
                "source": "Número nacional de emergencias de Venezuela",
            },
            {
                "name": "Línea 0800-RESCATE",
                "role": "Línea oficial para reportar personas y situaciones por el terremoto.",
                "phone": "0800-7372282",
                "phone_tel": "08007372282",
                "url": None,
                "source": "Línea oficial difundida por el Estado (VenApp)",
            },
            {
                "name": "VenApp",
                "role": "Aplicación oficial del Estado para reportar emergencias y solicitar ayuda.",
                "phone": None,
                "url": _search("VenApp descargar app oficial Venezuela"),
                "source": "Canal oficial del Estado",
            },
        ],
    },
    {
        "id": "rescate",
        "title": "Rescate y gestión de desastres",
        "intro": "Instituciones que coordinan búsqueda, rescate, albergues y monitoreo.",
        "items": [
            {
                "name": "Protección Civil (PCAD)",
                "role": "Dirección Nacional de Protección Civil y Administración de Desastres: rescate y albergues.",
                "phone": "911",
                "phone_tel": "911",
                "url": _search("Protección Civil Venezuela PCAD oficial"),
                "source": "Institución oficial; contacto inmediato vía 9-1-1",
            },
            {
                "name": "Cuerpo de Bomberos",
                "role": "Rescate, incendios y atención de emergencias. Disponible a través del 9-1-1.",
                "phone": "911",
                "phone_tel": "911",
                "url": None,
                "source": "Servicio oficial; contacto vía 9-1-1",
            },
            {
                "name": "FUNVISIS",
                "role": "Monitoreo sísmico oficial: magnitudes, réplicas y recomendaciones de seguridad.",
                "phone": None,
                "url": _search("FUNVISIS sismos Venezuela sitio oficial"),
                "source": "Fundación Venezolana de Investigaciones Sismológicas",
            },
        ],
    },
    {
        "id": "familiares",
        "title": "Buscar y reportar familiares",
        "intro": "Registros y colectivos donde buscar o registrar a una persona.",
        "items": [
            {
                "name": "Desaparecidos Terremoto Venezuela",
                "role": "Registro ciudadano de desaparecidos y localizados por el terremoto.",
                "phone": None,
                "url": _search("Desaparecidos Terremoto Venezuela"),
                "source": "Colectivo de búsqueda ciudadana",
            },
            {
                "name": "Venezuela Te Busca",
                "role": "Registrar y buscar personas: nombre, edad, foto y última ubicación.",
                "phone": None,
                "url": _search('"Venezuela Te Busca" desaparecidos'),
                "source": "Colectivo de búsqueda ciudadana",
            },
            {
                "name": "Cruz Roja — Restablecimiento del Contacto entre Familiares",
                "role": "Búsqueda internacional de familiares (Family Links / CICR).",
                "phone": None,
                "url": "https://familylinks.icrc.org/online-tracing",
                "source": "Comité Internacional de la Cruz Roja",
            },
        ],
    },
    {
        "id": "salud",
        "title": "Salud y apoyo humanitario",
        "intro": "Atención prehospitalaria y apoyo a damnificados.",
        "items": [
            {
                "name": "Cruz Roja Venezolana",
                "role": "Atención prehospitalaria, primeros auxilios y apoyo humanitario.",
                "phone": None,
                "url": _search("Cruz Roja Venezolana sitio oficial"),
                "source": "Sociedad nacional de la Cruz Roja",
            },
        ],
    },
]


def emergency_groups() -> list[dict]:
    return EMERGENCY_GROUPS
