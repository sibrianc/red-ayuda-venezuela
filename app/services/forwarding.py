"""Reenvío automático de reportes públicos a instituciones.

Diseñado para que la información llegue a quien puede actuar sin intervención
manual. Por seguridad sólo envía la PROYECCIÓN PÚBLICA (sin contacto privado,
sin dirección exacta, coordenadas redondeadas) y está DESACTIVADO por defecto:
el operador debe fijar INSTITUTION_FORWARD_ENABLED=true y un INSTITUTION_WEBHOOK_URL
propio (p. ej. el endpoint de una institución o un flujo intermedio autorizado).
"""

import json
import urllib.request

from flask import current_app

from app.constants import ReportType
from app.services.reporting import public_report_dict


def institutions_forwarding_enabled() -> bool:
    return bool(
        current_app.config.get("INSTITUTION_FORWARD_ENABLED")
        and current_app.config.get("INSTITUTION_WEBHOOK_URL")
    )


def forward_report_to_institutions(report_type: ReportType, report) -> bool:
    """Envía la proyección pública del reporte al webhook configurado.

    Devuelve True si se intentó el envío. Nunca lanza: un fallo de red no debe
    tumbar el alta del reporte.
    """
    if not institutions_forwarding_enabled():
        return False
    url = current_app.config["INSTITUTION_WEBHOOK_URL"]
    payload = {
        "source": "red-ayuda-venezuela",
        "kind": "citizen_report",
        "report": public_report_dict(report_type, report),
    }
    try:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "red-ayuda-venezuela/forwarder"},
            method="POST",
        )
        urllib.request.urlopen(request, timeout=5)  # noqa: S310 (URL la fija el operador)
        return True
    except Exception as exc:  # noqa: BLE001 - el reenvío es best-effort
        current_app.logger.warning("No se pudo reenviar el reporte a instituciones: %s", exc)
        return False
