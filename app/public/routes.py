from collections import Counter

from flask import render_template, request

from app.public import bp
from app.services.operational import (
    OFFICIAL_REGISTRIES,
    public_directory,
    public_incidents,
    public_missing_persons,
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

    all_incidents = public_incidents()
    incidents = [i for i in all_incidents if not category or i["category"] == category]
    services = public_directory()
    return render_template(
        "public/directory.html",
        situation=public_situation(),
        persons=public_missing_persons(q or None),
        incidents=incidents[:60],
        incident_groups=_grouped(all_incidents),
        incident_total=len(incidents),
        services=services[:60],
        service_groups=_grouped(services),
        registries=OFFICIAL_REGISTRIES,
        q=q,
        category=category,
    )


@bp.get("/privacidad")
def privacy():
    return render_template("public/privacy.html")
