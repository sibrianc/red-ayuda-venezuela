from flask import Blueprint

bp = Blueprint("map", __name__, url_prefix="/mapa")

from app.map import routes  # noqa: E402,F401
