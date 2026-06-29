import math
from collections import Counter

from flask import render_template, request, url_for

from app.public import bp
from app.services.operational import (
    CATEGORY_LABELS,
    OFFICIAL_REGISTRIES,
    coordination_overview,
    count_directory,
    count_lost_pets,
    count_person_records,
    count_pet_records,
    directory_category_counts,
    public_comms_zones,
    public_directory,
    public_incidents,
    public_lost_pets,
    public_missing_persons,
    public_person_records,
    public_pet_records,
    public_situation,
)
from app.services.reporting import public_items, public_report_dict, public_summary


@bp.get("/")
def home():
    items = public_items()
    return render_template(
        "public/home.html",
        summary=public_summary(items),
        recent_items=items[:4],
    )


def _grouped(rows: list[dict]) -> list[dict]:
    counts = Counter(row["category"] for row in rows)
    labels = {row["category"]: row.get("category_label", row["category"]) for row in rows}
    return [
        {"category": category, "label": labels[category], "count": count}
        for category, count in counts.most_common()
    ]


PEOPLE_PAGE = 60
SERVICES_PAGE = 60
INCIDENTS_PAGE = 40
PERSON_STATES = {"missing": "Desaparecidas", "found": "Localizadas", "deceased": "Fallecidas"}


def _page_arg() -> int:
    return max(request.args.get("page", 1, type=int), 1)


def _page_count(total: int, size: int) -> int:
    return max(math.ceil(total / size), 1) if total else 1


@bp.get("/directorio")
def directory():
    """Hub del directorio: una tarjeta por sección con su conteo real; sin listas pesadas."""
    situation = public_situation()
    figures = {metric["key"]: metric for metric in situation}
    sections = [
        {"label": "Personas", "desc": "Desaparecidas, localizadas y fallecidas. Busca o reporta a un familiar.",
         "count": count_person_records("missing") + count_person_records("found") + count_person_records("deceased"),
         "url": url_for("public.directory_people"), "accent": "#2a6fd6"},
        {"label": "Edificios e incidentes", "desc": "Colapsos y evaluación estructural, con fuente.",
         "count": len(public_incidents()), "url": url_for("public.directory_incidents"), "accent": "#e5443a"},
        {"label": "Servicios", "desc": "Hospitales, refugios, agua, farmacias, combustible y víveres.",
         "count": count_directory(), "url": url_for("public.directory_services"), "accent": "#1f9d63"},
        {"label": "Zonas sin comunicación", "desc": "Alertas de posibles víctimas incomunicadas.",
         "count": len(public_comms_zones()), "url": url_for("public.directory_zones"), "accent": "#8a5cf0"},
        {"label": "Mascotas desaparecidas", "desc": "Mascotas perdidas (comunidad + fuentes verificadas).",
         "count": count_lost_pets() + count_pet_records(), "url": url_for("public.directory_pets"), "accent": "#e0a02a"},
    ]
    return render_template(
        "public/directory.html",
        sections=sections,
        situation=situation,
        figure_missing=figures.get("missing"),
        figure_dead=figures.get("dead"),
        registries=OFFICIAL_REGISTRIES,
    )


@bp.get("/directorio/personas")
def directory_people():
    q = request.args.get("q", "").strip()
    estado = request.args.get("estado", "missing").strip()
    if estado not in PERSON_STATES:
        estado = "missing"
    page = _page_arg()
    total = count_person_records(estado, q or None)
    pages = _page_count(total, PEOPLE_PAGE)
    page = min(page, pages)
    records = public_person_records(status=estado, q=q or None, limit=PEOPLE_PAGE, offset=(page - 1) * PEOPLE_PAGE)
    community = public_missing_persons(q or None) if (estado == "missing" and page == 1) else []
    situation = public_situation()
    figures = {metric["key"]: metric for metric in situation}
    tabs = [{"key": key, "label": label, "count": count_person_records(key, q or None)} for key, label in PERSON_STATES.items()]
    return render_template(
        "public/directory_people.html",
        estado=estado, estado_label=PERSON_STATES[estado], tabs=tabs,
        community=community, records=records, total=total, page=page, pages=pages,
        figure_missing=figures.get("missing"), figure_dead=figures.get("dead"),
        registries=OFFICIAL_REGISTRIES, q=q,
    )


@bp.get("/directorio/incidentes")
def directory_incidents():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    page = _page_arg()
    all_incidents = public_incidents(q=q or None)
    groups = _grouped(all_incidents)
    filtered = [i for i in all_incidents if not category or i["category"] == category]
    total = len(filtered)
    pages = _page_count(total, INCIDENTS_PAGE)
    page = min(page, pages)
    start = (page - 1) * INCIDENTS_PAGE
    return render_template(
        "public/directory_incidents.html",
        incidents=filtered[start:start + INCIDENTS_PAGE], incident_groups=groups,
        total=total, page=page, pages=pages, category=category, q=q,
    )


@bp.get("/directorio/servicios")
def directory_services():
    q = request.args.get("q", "").strip()
    scat = request.args.get("scat", "").strip()
    page = _page_arg()
    cat_counts = directory_category_counts(q or None)
    total = cat_counts.get(scat, 0) if scat else count_directory(q or None)
    pages = _page_count(total, SERVICES_PAGE)
    page = min(page, pages)
    services = public_directory(q=q or None, category=scat or None, limit=SERVICES_PAGE, offset=(page - 1) * SERVICES_PAGE)
    service_groups = [
        {"category": cat, "label": CATEGORY_LABELS.get(cat, "Servicio"), "count": count}
        for cat, count in sorted(cat_counts.items(), key=lambda kv: kv[1], reverse=True)
    ]
    return render_template(
        "public/directory_services.html",
        services=services, service_groups=service_groups, total=total,
        page=page, pages=pages, service_category=scat, q=q,
    )


@bp.get("/directorio/zonas")
def directory_zones():
    q = request.args.get("q", "").strip()
    comms = public_comms_zones(q or None)
    return render_template("public/directory_zones.html", comms=comms, comms_total=len(comms), q=q)


@bp.get("/directorio/mascotas")
def directory_pets():
    q = request.args.get("q", "").strip()
    page = _page_arg()
    # Registros de fuentes verificadas (ingesta atribuida); paginados.
    total = count_pet_records(q or None)
    pages = _page_count(total, PEOPLE_PAGE)
    page = min(page, pages)
    records = public_pet_records(q or None, limit=PEOPLE_PAGE, offset=(page - 1) * PEOPLE_PAGE)
    # Reportes ciudadanos (formulario); se muestran arriba en la primera página.
    community = public_lost_pets(q or None) if page == 1 else []
    return render_template(
        "public/directory_pets.html",
        community=community, records=records,
        total=total, community_total=count_lost_pets(q or None),
        page=page, pages=pages, q=q,
    )


@bp.get("/coordinacion")
def coordination():
    """Centro de Coordinación: conecta familias ↔ rescatistas ↔ recursos en un solo lugar."""
    overview = coordination_overview()
    needs, resources = [], []
    for item in public_items():
        record = public_report_dict(item.report_type, item.report)
        if item.report_type.value == "help_request":
            needs.append(record)
        elif item.report_type.value == "resource_offer":
            resources.append(record)
    return render_template(
        "public/coordination.html",
        needs=needs[:20],
        resources=resources[:20],
        **overview,
    )


@bp.get("/contactos")
def contacts():
    """Red de contacto verificada: 911, instituciones de rescate y colectivos de búsqueda."""
    from app.services.contacts import emergency_groups

    return render_template("public/contacts.html", groups=emergency_groups())


@bp.get("/privacidad")
def privacy():
    return render_template("public/privacy.html")
