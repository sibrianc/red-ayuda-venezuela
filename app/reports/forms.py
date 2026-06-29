import re

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
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Regexp

from app.i18n import lazy as _L


class BaseReportForm(FlaskForm):
    location_text = StringField(
        _L("¿En qué zona ocurre?"), validators=[DataRequired(), Length(max=160)]
    )
    exact_address_private = StringField(
        _L("Referencia o dirección para el equipo (privada y opcional)"),
        validators=[Optional(), Length(max=240)],
    )
    latitude = DecimalField(
        _L("Latitud aproximada (opcional)"), validators=[Optional(), NumberRange(min=-90, max=90)]
    )
    longitude = DecimalField(
        _L("Longitud aproximada (opcional)"), validators=[Optional(), NumberRange(min=-180, max=180)]
    )
    description_public = TextAreaField(
        _L("Cuéntanos qué ocurre y qué se necesita"),
        validators=[DataRequired(), Length(min=10, max=2000)],
    )
    description_private = TextAreaField(
        _L("Información adicional solo para el equipo"), validators=[Optional(), Length(max=3000)]
    )
    reporter_name_private = StringField(
        _L("Tu nombre (de quien hace el reporte)"), validators=[DataRequired(), Length(max=120)]
    )
    reporter_contact_private = StringField(
        _L("Teléfono o correo donde podamos contactarte"),
        validators=[DataRequired(), Length(max=160)],
    )
    privacy_consent = BooleanField(
        _L("Entiendo que el reporte será revisado y que no debo incluir datos sensibles en la descripción pública."),
        validators=[DataRequired()],
    )
    website = StringField(_L("Dejar vacío"), validators=[Optional(), Length(max=0)])
    submit = SubmitField(_L("Enviar reporte de forma segura"))


class MissingPersonForm(BaseReportForm):
    first_name = StringField(
        _L("Nombre de la persona desaparecida"), validators=[DataRequired(), Length(max=100)]
    )
    last_name = StringField(
        _L("Apellido de la persona desaparecida"), validators=[DataRequired(), Length(max=100)]
    )
    age = IntegerField(
        _L("Edad aproximada de la persona"), validators=[Optional(), NumberRange(min=0, max=120)]
    )
    gender = SelectField(
        _L("Género de la persona (opcional)"),
        choices=[("", _L("Prefiero no indicar")), ("female", _L("Femenino")), ("male", _L("Masculino")), ("other", _L("Otro"))],
        validators=[Optional()],
    )
    last_contact_date = DateField(
        _L("Fecha aproximada del último contacto con la persona"), validators=[Optional()]
    )
    # Etiquetas específicas para reunificación (sobrescriben las genéricas de la base).
    location_text = StringField(
        _L("¿Dónde se le vio por última vez?"), validators=[DataRequired(), Length(max=160)]
    )
    description_public = TextAreaField(
        _L("Descripción de la persona (estatura, contextura, ropa, señas particulares)"),
        validators=[DataRequired(), Length(min=10, max=2000)],
    )
    relationship_to_person_private = StringField(
        _L("Relación con la persona (privado)"), validators=[Optional(), Length(max=100)]
    )
    medical_information_private = TextAreaField(
        _L("Información médica necesaria para revisión (privada)"),
        validators=[Optional(), Length(max=1000)],
    )
    involves_minor = BooleanField(_L("La persona es menor de edad"))


class HelpRequestForm(BaseReportForm):
    title = StringField(_L("Resumen de la necesidad"), validators=[DataRequired(), Length(max=160)])
    request_type = SelectField(
        _L("Necesidad principal"),
        choices=[
            ("medical", _L("Atención médica o medicamentos")),
            ("water", _L("Agua")),
            ("food", _L("Alimentos")),
            ("shelter", _L("Refugio")),
            ("transport", _L("Transporte")),
            ("rescue", _L("Rescate")),
            ("other", _L("Otra")),
        ],
        validators=[DataRequired()],
    )
    people_affected = IntegerField(
        _L("Personas afectadas"), default=1, validators=[DataRequired(), NumberRange(min=1, max=10000)]
    )
    vulnerable_people_present = BooleanField(_L("Hay menores, adultos mayores o personas con discapacidad"))
    medical_need = BooleanField(_L("Necesidad médica"))
    water_need = BooleanField(_L("Necesidad de agua"))
    food_need = BooleanField(_L("Necesidad de alimentos"))
    shelter_need = BooleanField(_L("Necesidad de refugio"))
    transport_need = BooleanField(_L("Necesidad de transporte"))
    medical_information_private = TextAreaField(
        _L("Detalles médicos (privados)"), validators=[Optional(), Length(max=1000)]
    )


class ResourceOfferForm(BaseReportForm):
    title = StringField(_L("Resumen del recurso que ofreces"), validators=[DataRequired(), Length(max=160)])
    resource_type = SelectField(
        _L("Tipo de recurso"),
        choices=[
            ("medical", _L("Atención médica o medicamentos")),
            ("water", _L("Agua")),
            ("food", _L("Alimentos")),
            ("shelter", _L("Refugio")),
            ("transport", _L("Transporte")),
            ("volunteers", _L("Voluntariado")),
            ("other", _L("Otro")),
        ],
        validators=[DataRequired()],
    )
    capacity = StringField(_L("Cantidad o capacidad"), validators=[Optional(), Length(max=120)])
    availability = StringField(_L("Disponibilidad"), validators=[Optional(), Length(max=120)])


class LocationReportForm(BaseReportForm):
    title = StringField(
        _L("Edificio o lugar afectado que quieres reportar"), validators=[DataRequired(), Length(max=160)]
    )
    damage_level = SelectField(
        _L("Nivel aparente de daño"),
        choices=[
            ("unknown", _L("No determinado")),
            ("low", _L("Bajo")),
            ("medium", _L("Medio")),
            ("high", _L("Alto")),
            ("critical", _L("Crítico")),
        ],
        validators=[DataRequired()],
    )
    needs_water = BooleanField(_L("Necesita agua"))
    needs_food = BooleanField(_L("Necesita alimentos"))
    needs_medical = BooleanField(_L("Necesita atención médica"))
    needs_shelter = BooleanField(_L("Necesita refugio"))
    needs_transport = BooleanField(_L("Necesita transporte"))


class LostPetForm(BaseReportForm):
    title = StringField(
        _L("Nombre o identificación de la mascota"), validators=[DataRequired(), Length(max=160)]
    )
    species = SelectField(
        _L("Tipo de animal"),
        choices=[("dog", _L("Perro")), ("cat", _L("Gato")), ("bird", _L("Ave")), ("other", _L("Otra"))],
        validators=[DataRequired()],
    )
    breed = StringField(_L("Raza (opcional)"), validators=[Optional(), Length(max=80)])
    color = StringField(_L("Color y señas (opcional)"), validators=[Optional(), Length(max=80)])
    last_seen_date = DateField(_L("Fecha aproximada en que se perdió"), validators=[Optional()])
    photo_url = StringField(
        _L("Enlace a una foto (opcional)"),
        validators=[
            Optional(),
            Length(max=500),
            Regexp(
                r"^https://\S+\.(?:jpe?g|png|webp|gif)(?:\?\S*)?$",
                flags=re.IGNORECASE,
                message=_L("Pega un enlace https directo a una imagen (.jpg, .png, .webp o .gif)."),
            ),
        ],
    )
    location_text = StringField(
        _L("¿Dónde se le vio por última vez?"), validators=[DataRequired(), Length(max=160)]
    )
    description_public = TextAreaField(
        _L("Descripción de la mascota (tamaño, señas, collar, comportamiento)"),
        validators=[DataRequired(), Length(min=10, max=2000)],
    )


class CommunicationSignalForm(FlaskForm):
    zone_label = StringField(
        _L("¿Qué zona está sin comunicación?"), validators=[DataRequired(), Length(max=160)]
    )
    latitude = DecimalField(
        _L("Latitud aproximada (opcional)"), validators=[Optional(), NumberRange(min=-90, max=90)]
    )
    longitude = DecimalField(
        _L("Longitud aproximada (opcional)"), validators=[Optional(), NumberRange(min=-180, max=180)]
    )
    public_note = TextAreaField(
        _L("¿Qué se sabe? (sin nombres ni datos personales)"),
        validators=[Optional(), Length(max=1000)],
    )
    reporter_contact_private = StringField(
        _L("Tu contacto (privado y opcional, por si necesitamos corroborar)"),
        validators=[Optional(), Length(max=160)],
    )
    privacy_consent = BooleanField(
        _L("Entiendo que es un reporte sin verificar y que no debo incluir datos personales públicos."),
        validators=[DataRequired()],
    )
    website = StringField(_L("Dejar vacío"), validators=[Optional(), Length(max=0)])
    submit = SubmitField(_L("Reportar zona sin comunicación"))


class AbuseForm(FlaskForm):
    reason = SelectField(
        _L("Motivo"),
        choices=[
            ("false_information", _L("Información posiblemente falsa")),
            ("privacy", _L("Expone información sensible")),
            ("fraud", _L("Posible fraude o estafa")),
            ("resolved", _L("El caso ya fue resuelto")),
            ("other", _L("Otro")),
        ],
        validators=[DataRequired()],
    )
    details = TextAreaField(_L("Detalles"), validators=[Optional(), Length(max=1000)])
    contact = StringField(_L("Contacto opcional (privado)"), validators=[Optional(), Length(max=160)])
    website = StringField(_L("Dejar vacío"), validators=[Optional(), Length(max=0)])
    submit = SubmitField(_L("Enviar reporte de abuso"))
