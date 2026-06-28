from flask import render_template

from app.public import bp
from app.services.reporting import public_items, public_summary


@bp.get("/")
def home():
    items = public_items()
    return render_template(
        "public/home.html",
        summary=public_summary(items),
        recent_items=items[:4],
    )


@bp.get("/privacidad")
def privacy():
    return render_template("public/privacy.html")
