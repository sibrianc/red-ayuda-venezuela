from collections import Counter

from flask import render_template, request

from app.public import bp
from app.services.operational import (
    CATEGORY_LABELS,
    OFFICIAL_REGISTRIES,
    coordination_overview,
    count_directory,
    count_person_records,
    directory_category_counts,
    public_comms_zones,
    public_directory,
    public_directory_balanced,
    public_incidents,
    public_missing_persons,
    public_person_records,
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


@bp.get("/directorio")
def directory():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    scat = request.args.get("scat", "").strip()

    persons = public_missing_persons(q or None)
    published_missing = public_person_records(status="missing", q=q or None)
    localized = public_person_records(status="found", q=q or None)
    deceased = public_person_records(status="deceased", q=q or None)
    all_incidents = public_incidents(q=q or None)
    incidents = [i for i in all_incidents if not category or i["category"] == category]
    services = (
        public_directory(q=q or None, category=scat)
        if scat
        else public_directory_balanced(q=q or None)
    )
    cat_counts = directory_category_counts(q or None)
    service_groups = [
        {"category": cat, "label": CATEGORY_LABELS.get(cat, "Servicio"), "count": count}
        for cat, count in sorted(cat_counts.items(), key=lambda kv: kv[1], reverse=True)
    ]
    comms = public_comms_zones(q or None)
    situation = public_situation()
    figures = {metric["key"]: metric for metric in situation}
    return render_template(
        "public/directory.html",
        situation=situation,
        figure_missing=figures.get("missing"),
        figure_dead=figures.get("dead"),
        persons=persons,
        published_missing=published_missing[:120],
        person_total=len(persons) + count_person_records("missing", q or None),
        localized=localized[:120],
        localized_total=count_person_records("found", q or None),
        deceased=deceased[:120],
        deceased_total=count_person_records("deceased", q or None),
        comms=comms,
        comms_total=len(comms),
        incidents=incidents[:80],
        incident_groups=_grouped(all_incidents),
        incident_total=len(incidents),
        services=services[:150],
        service_groups=service_groups,
        service_total=count_directory(q or None),
        service_category=scat,
        registries=OFFICIAL_REGISTRIES,
        q=q,
        category=category,
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


@bp.get("/privacidad")
def privacy():
    return render_template("public/privacy.html")
