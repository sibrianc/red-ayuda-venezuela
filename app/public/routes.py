from collections import Counter

from flask import render_template, request

from app.public import bp
from app.services.operational import (
    OFFICIAL_REGISTRIES,
    public_comms_zones,
    public_directory,
    public_incidents,
    public_missing_persons,
    public_person_records,
    public_situation,
)
from app.services.reporting import public_items, public_summary


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

    persons = public_missing_persons(q or None)
    published_missing = public_person_records(status="missing", q=q or None)
    deceased = public_person_records(status="deceased", q=q or None)
    all_incidents = public_incidents(q=q or None)
    incidents = [i for i in all_incidents if not category or i["category"] == category]
    services = public_directory(q=q or None)
    comms = public_comms_zones(q or None)
    return render_template(
        "public/directory.html",
        situation=public_situation(),
        persons=persons,
        published_missing=published_missing,
        person_total=len(persons) + len(published_missing),
        deceased=deceased,
        deceased_total=len(deceased),
        comms=comms,
        comms_total=len(comms),
        incidents=incidents[:80],
        incident_groups=_grouped(all_incidents),
        incident_total=len(incidents),
        services=services[:80],
        service_groups=_grouped(services),
        service_total=len(services),
        registries=OFFICIAL_REGISTRIES,
        q=q,
        category=category,
    )


@bp.get("/privacidad")
def privacy():
    return render_template("public/privacy.html")
