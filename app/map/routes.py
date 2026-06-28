from flask import jsonify, render_template, url_for

from app.map import bp
from app.services.reporting import public_items, public_report_dict


@bp.get("")
def index():
    return render_template("map/index.html")


@bp.get("/data")
def data():
    reports = []
    for item in public_items():
        if item.report.latitude is None or item.report.longitude is None:
            continue
        record = public_report_dict(item.report_type, item.report)
        record["url"] = url_for(
            "reports.detail",
            report_type=item.report_type.value,
            public_id=item.report.public_id,
        )
        reports.append(record)
    response = jsonify({"reports": reports})
    response.headers["Cache-Control"] = "public, max-age=60"
    return response
