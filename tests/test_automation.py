from app.constants import Priority, ReportType
from app.models import HelpRequest, ResourceOffer
from app.services.automation import normalize, suggest_priority, suggest_resource_matches
from app.extensions import db


def test_priority_rules_are_deterministic():
    report = HelpRequest(
        title="Persona atrapada",
        request_type="rescue",
        people_affected=1,
        location_text="Zona",
        description_public="Hay una persona atrapada después de un derrumbe.",
        reporter_name_private="Privado",
        reporter_contact_private="Privado",
    )
    first = suggest_priority(ReportType.HELP_REQUEST, report)
    second = suggest_priority(ReportType.HELP_REQUEST, report)
    assert first == second
    assert first[0] is Priority.CRITICAL


def test_normalization_handles_spanish_accents():
    assert normalize("  Oxígeno / NIÑA ") == "oxigeno nina"


def test_resource_matching_is_structured_and_read_only(app):
    with app.app_context():
        need = HelpRequest(
            title="Se necesita agua",
            request_type="water",
            people_affected=10,
            location_text="La Guaira Centro",
            description_public="Solicitud comunitaria de agua potable.",
            reporter_name_private="Privado",
            reporter_contact_private="Privado",
        )
        resource = ResourceOffer(
            title="Agua disponible",
            resource_type="water",
            location_text="La Guaira Centro",
            description_public="Recurso revisado disponible.",
            reporter_name_private="Privado",
            reporter_contact_private="Privado",
            is_public=True,
        )
        db.session.add_all([need, resource])
        db.session.commit()
        matches = suggest_resource_matches(need)
        assert matches[0]["resource"].id == resource.id
        assert need.status.value == "pending"
