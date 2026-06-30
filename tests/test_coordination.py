from app.ingestion.incidents import curated_collapsed_structures
from app.ingestion.pipeline import ingest_incidents
from app.services.operational import coordination_overview


def test_coordination_priorities_include_collapses_without_coordinates(app):
    # Los colapsos curados son reales (severidad alta) pero SIN coordenada exacta (no se
    # inventan). "Prioridades de rescate" es una lista operativa: deben aparecer igual.
    with app.app_context():
        ingest_incidents(curated_collapsed_structures())
        overview = coordination_overview()

        assert overview["incident_total"] >= 1
        assert len(overview["priorities"]) >= 1
        # aparecen aunque no tengan coordenada (antes el filtro los excluía → 0)
        assert any(p.get("latitude") is None for p in overview["priorities"])
        # y son de severidad de prioridad
        assert all(p["severity"] in {"critical", "high"} for p in overview["priorities"])


def test_coordination_priorities_order_critical_and_mappable_first(app):
    # A igual conjunto, las críticas y las que tienen coordenada deben ir primero.
    from app.extensions import db
    from app.models import Incident

    with app.app_context():
        db.session.add(Incident(
            source_slug="x", external_id="a", content_hash="a", category="collapsed_structure",
            severity="high", label="Sin coords", verification_status="reported", status="reported",
            latitude=None, longitude=None,
        ))
        db.session.add(Incident(
            source_slug="x", external_id="b", content_hash="b", category="collapsed_structure",
            severity="critical", label="Crítica con coords", verification_status="reported",
            status="reported", latitude=10.6, longitude=-66.9,
        ))
        db.session.commit()

        priorities = coordination_overview()["priorities"]
        assert priorities[0]["label"] == "Crítica con coords"  # crítica primero
