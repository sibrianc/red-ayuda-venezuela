from flask import Blueprint

bp = Blueprint("auth", __name__, url_prefix="/cuenta")

from app.auth import routes  # noqa: E402,F401
