"""Auditoría visual local opcional. No se ejecuta contra producción."""

import json
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:5010"
OUTPUT = Path("/private/tmp/rav_browser_audit")
PRIVATE_MARKER = "CONTACTO-PRIVADO-E2E"


def run() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report_title = f"Prueba visual de agua {uuid4().hex[:8]}"
    results = {"console_errors": [], "page_errors": [], "checks": {}}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="es-VE")
        page = context.new_page()
        page.on("console", lambda message: results["console_errors"].append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: results["page_errors"].append(str(error)))

        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.screenshot(path=OUTPUT / "desktop-home.png", full_page=True)
        results["checks"]["home_h1"] = page.locator("h1").count() == 1
        results["checks"]["skip_link"] = page.locator(".skip-link").count() == 1
        results["checks"]["home_public_dashboard"] = page.locator(".signal-card").count() == 4
        results["checks"]["home_source_readiness"] = page.locator(".source-readiness").count() == 1

        with page.expect_navigation(wait_until="domcontentloaded"):
            page.get_by_role("button", name="Modo ligero").click()
        results["checks"]["low_bandwidth_persists"] = (
            page.locator("html").get_attribute("data-bandwidth") == "low"
        )
        page.goto(f"{BASE_URL}/mapa", wait_until="domcontentloaded")
        results["checks"]["low_bandwidth_skips_tiles"] = (
            page.locator(".low-bandwidth-map-notice").count() == 1
            and page.locator(".leaflet-tile").count() == 0
        )
        page.screenshot(path=OUTPUT / "desktop-map-low-bandwidth.png", full_page=True)
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.get_by_role("button", name="Salir del modo ligero").click()

        page.goto(f"{BASE_URL}/reportes/ayuda", wait_until="domcontentloaded")
        page.screenshot(path=OUTPUT / "desktop-help-form.png", full_page=True)
        page.get_by_label("Título breve").fill(report_title)
        page.get_by_label("Necesidad principal").select_option("water")
        page.get_by_label("Personas afectadas").fill("3")
        page.get_by_role("button", name="Continuar a ubicación").click()
        page.get_by_label("¿En qué zona ocurre?").fill("Zona de prueba La Guaira")
        page.get_by_text("Añadir una referencia privada para el equipo", exact=True).click()
        page.get_by_label("Referencia o dirección para el equipo (privada y opcional)").fill(
            "Dirección privada E2E"
        )
        page.screenshot(path=OUTPUT / "desktop-help-location.png", full_page=True)
        page.get_by_role("button", name="Continuar a contacto").click()
        page.get_by_label("Cuéntanos qué ocurre y qué se necesita").fill(
            "Descripción pública de prueba para revisión visual del flujo."
        )
        page.get_by_text("Añadir información privada para la revisión", exact=True).click()
        page.get_by_label("Información adicional solo para el equipo").fill("DETALLE-PRIVADO-E2E")
        page.get_by_label("Tu nombre").fill("Usuario de prueba")
        page.get_by_label("Teléfono o correo donde podamos contactarte").fill(PRIVATE_MARKER)
        page.get_by_label(
            "Entiendo que el reporte será revisado y que no debo incluir datos sensibles en la descripción pública."
        ).check()
        page.screenshot(path=OUTPUT / "desktop-help-contact.png", full_page=True)
        page.get_by_role("button", name="Enviar reporte de forma segura").click()
        page.wait_for_load_state("domcontentloaded")
        results["checks"]["confirmation"] = page.get_by_text("Ahora comienza la revisión.").count() == 1

        page.goto(f"{BASE_URL}/cuenta/login", wait_until="domcontentloaded")
        page.get_by_label("Correo").fill("demo@example.org")
        page.get_by_label("Contraseña").fill("Demo-Only-Password-2026!")
        page.get_by_role("button", name="Iniciar sesión").click()
        page.wait_for_load_state("domcontentloaded")
        page.get_by_role("link", name=report_title, exact=True).click()
        page.wait_for_load_state("domcontentloaded")
        page.screenshot(path=OUTPUT / "desktop-admin-review.png", full_page=True)
        page.get_by_label("Estado", exact=True).select_option("approved")
        page.get_by_label("Verificación", exact=True).select_option("volunteer")
        page.get_by_label("Prioridad", exact=True).select_option("high")
        page.get_by_label("Publicar si el estado es aprobado").check()
        page.get_by_label("Descripción pública revisada").fill(
            "Descripción pública sanitizada para la prueba visual."
        )
        page.get_by_label("Razón del cambio").fill("Verificación E2E local")
        page.get_by_role("button", name="Guardar revisión").click()
        page.wait_for_load_state("domcontentloaded")

        page.goto(f"{BASE_URL}/reportes", wait_until="domcontentloaded")
        page.screenshot(path=OUTPUT / "desktop-public-reports.png", full_page=True)
        public_html = page.content()
        results["checks"]["public_visible"] = "Descripción pública sanitizada" in public_html
        results["checks"]["private_not_in_html"] = PRIVATE_MARKER not in public_html and "DETALLE-PRIVADO-E2E" not in public_html

        response = context.request.get(f"{BASE_URL}/mapa/data")
        map_text = response.text()
        results["checks"]["private_not_in_map_json"] = PRIVATE_MARKER not in map_text and "DETALLE-PRIVADO-E2E" not in map_text

        page.goto(f"{BASE_URL}/mapa", wait_until="domcontentloaded")
        page.screenshot(path=OUTPUT / "desktop-map.png", full_page=True)
        results["checks"]["map_region"] = page.locator("#report-map").count() == 1
        results["checks"]["map_filters"] = page.locator("[data-map-filter]").count() == 5
        results["checks"]["map_density_mode"] = page.locator('[data-map-mode="density"]').count() == 1
        page.get_by_role("button", name="Concentración").click()
        results["checks"]["map_density_activates"] = (
            page.get_by_role("button", name="Concentración").get_attribute("aria-pressed") == "true"
        )
        page.screenshot(path=OUTPUT / "desktop-map-density.png", full_page=True)

        mobile = browser.new_context(viewport={"width": 375, "height": 812}, locale="es-VE")
        mobile_page = mobile.new_page()
        for name, path in (("home", "/"), ("form", "/reportes/ayuda"), ("reports", "/reportes")):
            mobile_page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded")
            overflow = mobile_page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            results["checks"][f"mobile_{name}_no_overflow"] = not overflow
            if name == "form":
                results["checks"]["mobile_form_guided"] = mobile_page.locator("[data-wizard-panel]").count() == 3
                results["checks"]["mobile_form_labels"] = mobile_page.locator("label").count() > 0
            mobile_page.screenshot(path=OUTPUT / f"mobile-{name}.png", full_page=True)
        mobile.close()
        context.close()
        browser.close()

    (OUTPUT / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(json.dumps(results, indent=2, ensure_ascii=False))
    if results["console_errors"] or results["page_errors"] or not all(results["checks"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    run()
