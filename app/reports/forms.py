from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class BaseReportForm(FlaskForm):
    location_text = StringField(
        "¿En qué zona ocurre?", validators=[DataRequired(), Length(max=160)]
    )
    exact_address_private = StringField(
        "Referencia o dirección para el equipo (privada y opcional)",
        validators=[Optional(), Length(max=240)],
    )
    latitude = DecimalField(
        "Latitud aproximada (opcional)", validators=[Optional(), NumberRange(min=-90, max=90)]
    )
    longitude = DecimalField(
        "Longitud aproximada (opcional)", validators=[Optional(), NumberRange(min=-180, max=180)]
    )
    description_public = TextAreaField(
        "Cuéntanos qué ocurre y qué se necesita",
        validators=[DataRequired(), Length(min=10, max=2000)],
    )
    description_private = TextAreaField(
        "Información adicional solo para el equipo", validators=[Optional(), Length(max=3000)]
    )
    reporter_name_private = StringField(
        "Tu nombre", validators=[DataRequired(), Length(max=120)]
    )
    reporter_contact_private = StringField(
        "Teléfono o correo donde podamos contactarte",
        validators=[DataRequired(), Length(max=160)],
    )
    privacy_consent = BooleanField(
        "Entiendo que el reporte será revisado y que no debo incluir datos sensibles en la descripción pública.",
        validators=[DataRequired()],
    )
    website = StringField("Dejar vacío", validators=[Optional(), Length(max=0)])
    submit = SubmitField("Enviar reporte de forma segura")


class MissingPersonForm(BaseReportForm):
    first_name = StringField("Nombre", validators=[DataRequired(), Length(max=100)])
    last_name = StringField("Apellido", validators=[DataRequired(), Length(max=100)])
    age = IntegerField("Edad aproximada", validators=[Optional(), NumberRange(min=0, max=120)])
    gender = SelectField(
        "Género (opcional)",
        choices=[("", "Prefiero no indicar"), ("female", "Femenino"), ("male", "Masculino"), ("other", "Otro")],
        validators=[Optional()],
    )
    last_contact_date = DateField("Fecha aproximada del último contacto", validators=[Optional()])
    relationship_to_person_private = StringField(
        "Relación con la persona (privado)", validators=[Optional(), Length(max=100)]
    )
    medical_information_private = TextAreaField(
        "Información médica necesaria para revisión (privada)",
        validators=[Optional(), Length(max=1000)],
    )
    involves_minor = BooleanField("La persona es menor de edad")


class HelpRequestForm(BaseReportForm):
    title = StringField("Título breve", validators=[DataRequired(), Length(max=160)])
    request_type = SelectField(
        "Necesidad principal",
        choices=[
            ("medical", "Atención médica o medicamentos"),
            ("water", "Agua"),
            ("food", "Alimentos"),
            ("shelter", "Refugio"),
            ("transport", "Transporte"),
            ("rescue", "Rescate"),
            ("other", "Otra"),
        ],
        validators=[DataRequired()],
    )
    people_affected = IntegerField(
        "Personas afectadas", default=1, validators=[DataRequired(), NumberRange(min=1, max=10000)]
    )
    vulnerable_people_present = BooleanField("Hay menores, adultos mayores o personas con discapacidad")
    medical_need = BooleanField("Necesidad médica")
    water_need = BooleanField("Necesidad de agua")
    food_need = BooleanField("Necesidad de alimentos")
    shelter_need = BooleanField("Necesidad de refugio")
    transport_need = BooleanField("Necesidad de transporte")
    medical_information_private = TextAreaField(
        "Detalles médicos (privados)", validators=[Optional(), Length(max=1000)]
    )


class ResourceOfferForm(BaseReportForm):
    title = StringField("Título breve", validators=[DataRequired(), Length(max=160)])
    resource_type = SelectField(
        "Tipo de recurso",
        choices=[
            ("medical", "Atención médica o medicamentos"),
            ("water", "Agua"),
            ("food", "Alimentos"),
            ("shelter", "Refugio"),
            ("transport", "Transporte"),
            ("volunteers", "Voluntariado"),
            ("other", "Otro"),
        ],
        validators=[DataRequired()],
    )
    capacity = StringField("Cantidad o capacidad", validators=[Optional(), Length(max=120)])
    availability = StringField("Disponibilidad", validators=[Optional(), Length(max=120)])


class LocationReportForm(BaseReportForm):
    title = StringField("Título breve", validators=[DataRequired(), Length(max=160)])
    damage_level = SelectField(
        "Nivel aparente de daño",
        choices=[
            ("unknown", "No determinado"),
            ("low", "Bajo"),
            ("medium", "Medio"),
            ("high", "Alto"),
            ("critical", "Crítico"),
        ],
        validators=[DataRequired()],
    )
    needs_water = BooleanField("Necesita agua")
    needs_food = BooleanField("Necesita alimentos")
    needs_medical = BooleanField("Necesita atención médica")
    needs_shelter = BooleanField("Necesita refugio")
    needs_transport = BooleanField("Necesita transporte")


class CommunicationSignalForm(FlaskForm):
    zone_label = StringField(
        "¿Qué zona está sin comunicación?", validators=[DataRequired(), Length(max=160)]
    )
    latitude = DecimalField(
        "Latitud aproximada (opcional)", validators=[Optional(), NumberRange(min=-90, max=90)]
    )
    longitude = DecimalField(
        "Longitud aproximada (opcional)", validators=[Optional(), NumberRange(min=-180, max=180)]
    )
    public_note = TextAreaField(
        "¿Qué se sabe? (sin nombres ni datos personales)",
        validators=[Optional(), Length(max=1000)],
    )
    reporter_contact_private = StringField(
        "Tu contacto (privado y opcional, por si necesitamos corroborar)",
        validators=[Optional(), Length(max=160)],
    )
    privacy_consent = BooleanField(
        "Entiendo que es un reporte sin verificar y que no debo incluir datos personales públicos.",
        validators=[DataRequired()],
    )
    website = StringField("Dejar vacío", validators=[Optional(), Length(max=0)])
    submit = SubmitField("Reportar zona sin comunicación")


class AbuseForm(FlaskForm):
    reason = SelectField(
        "Motivo",
        choices=[
            ("false_information", "Información posiblemente falsa"),
            ("privacy", "Expone información sensible"),
            ("fraud", "Posible fraude o estafa"),
            ("resolved", "El caso ya fue resuelto"),
            ("other", "Otro"),
        ],
        validators=[DataRequired()],
    )
    details = TextAreaField("Detalles", validators=[Optional(), Length(max=1000)])
    contact = StringField("Contacto opcional (privado)", validators=[Optional(), Length(max=160)])
    website = StringField("Dejar vacío", validators=[Optional(), Length(max=0)])
    submit = SubmitField("Enviar reporte de abuso")
