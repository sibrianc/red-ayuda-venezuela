from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, SubmitField, TextAreaField
from wtforms.validators import Length, Optional

from app.constants import (
    PRIORITY_LABELS,
    STATUS_LABELS,
    VERIFICATION_LABELS,
    Priority,
    ReportStatus,
    VerificationStatus,
)


class ReviewForm(FlaskForm):
    status = SelectField(
        "Estado",
        choices=[(item.value, STATUS_LABELS[item]) for item in ReportStatus],
    )
    verification_status = SelectField(
        "Verificación",
        choices=[(item.value, VERIFICATION_LABELS[item]) for item in VerificationStatus],
    )
    priority = SelectField(
        "Prioridad", choices=[(item.value, PRIORITY_LABELS[item]) for item in Priority]
    )
    is_public = BooleanField("Publicar si el estado es aprobado")
    description_public = TextAreaField(
        "Descripción pública revisada", validators=[Length(min=10, max=2000)]
    )
    reason = TextAreaField("Razón del cambio", validators=[Optional(), Length(max=500)])
    note = TextAreaField("Nueva nota interna", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Guardar revisión")


class AbuseReviewForm(FlaskForm):
    status = SelectField(
        "Estado",
        choices=[
            ("pending", "Pendiente"),
            ("reviewed", "Revisado"),
            ("dismissed", "Descartado"),
            ("action_taken", "Acción tomada"),
        ],
    )
    submit = SubmitField("Actualizar")
