from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_user, logout_user

from app.auth import bp
from app.auth.forms import LoginForm
from app.models import User


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.is_active and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("admin.dashboard"))
        flash("Credenciales inválidas.", "danger")
    return render_template("auth/login.html", form=form)


@bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for("public.home"))
