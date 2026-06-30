from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class LoginForm(FlaskForm):
    email = StringField("Correo", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Contraseña", validators=[DataRequired(), Length(max=255)])
    submit = SubmitField("Iniciar sesión")


class TwoFactorForm(FlaskForm):
    code = StringField(
        "Código de 6 dígitos", validators=[DataRequired(), Length(min=6, max=10)]
    )
    submit = SubmitField("Verificar")


class SetPasswordForm(FlaskForm):
    password = PasswordField(
        "Nueva contraseña (mínimo 12 caracteres)",
        validators=[DataRequired(), Length(min=12, max=255)],
    )
    confirm = PasswordField(
        "Repite la contraseña",
        validators=[DataRequired(), EqualTo("password", message="Las contraseñas no coinciden.")],
    )
    submit = SubmitField("Activar mi cuenta")
