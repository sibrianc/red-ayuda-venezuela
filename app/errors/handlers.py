from flask import render_template

from app.errors import bp


@bp.app_errorhandler(400)
def bad_request(error):
    return render_template("errors/error.html", code=400, message="La solicitud no es válida."), 400


@bp.app_errorhandler(403)
def forbidden(error):
    return render_template("errors/error.html", code=403, message="No tienes permiso para esta acción."), 403


@bp.app_errorhandler(404)
def not_found(error):
    return render_template("errors/error.html", code=404, message="No encontramos esa página."), 404


@bp.app_errorhandler(413)
def too_large(error):
    return render_template("errors/error.html", code=413, message="La solicitud supera el límite permitido."), 413


@bp.app_errorhandler(500)
def server_error(error):
    return render_template("errors/error.html", code=500, message="Ocurrió un error interno."), 500
