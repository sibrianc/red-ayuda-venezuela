from flask import render_template

from app.public import bp


@bp.get("/")
def home():
    return render_template("public/home.html")


@bp.get("/privacidad")
def privacy():
    return render_template("public/privacy.html")
