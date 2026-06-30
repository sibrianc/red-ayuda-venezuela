/*
 * Guía interactiva paso a paso para usuarios casuales (no desarrolladores).
 * Botón flotante discreto que abre un recorrido con burbujas explicativas,
 * resaltando cada función del sitio con botones "Atrás / Siguiente".
 * Sin dependencias externas; bilingüe (es/en) según el idioma de la página.
 */
(() => {
  "use strict";

  // El mapa es una vista inmersiva a pantalla completa con sus propios controles:
  // ahí no mostramos la guía para no estorbar. Se explica desde el resto del sitio.
  if (location.pathname.startsWith("/mapa")) return;

  const lang = (document.documentElement.lang || "es").slice(0, 2) === "en" ? "en" : "es";
  const L = (es, en) => (lang === "en" ? en : es);
  const path = location.pathname.replace(/\/+$/, "") || "/";

  const T = {
    open: L("Abrir la guía del sitio", "Open the site guide"),
    title: L("Guía", "Guide"),
    next: L("Siguiente", "Next"),
    prev: L("Atrás", "Back"),
    finish: L("Entendido", "Got it"),
    skip: L("Saltar guía", "Skip guide"),
    close: L("Cerrar", "Close"),
    step: L("Paso", "Step"),
    of: L("de", "of"),
  };

  // -- Definición de pasos --------------------------------------------------
  // target: selector CSS (o null para una tarjeta centrada). Si el elemento no
  // existe en la página, el paso se omite automáticamente.
  function buildSteps() {
    const steps = [];

    steps.push({
      target: null,
      title: L("Bienvenido/a a Red de Ayuda Venezuela", "Welcome to Red de Ayuda Venezuela"),
      body: L(
        "En menos de un minuto te mostramos, paso a paso, todo lo que puedes hacer aquí. Avanza con <b>Siguiente</b> y puedes salir cuando quieras.<br><br>Importante: este sitio reúne información pública del terremoto. <b>No es un servicio oficial de emergencia</b>: ante un peligro inmediato, llama al <b>9-1-1</b>.",
        "In under a minute we’ll walk you through everything you can do here, step by step. Use <b>Next</b> to continue, and you can leave anytime.<br><br>Important: this site gathers public earthquake information. <b>It is not an official emergency service</b>: in immediate danger, call <b>9-1-1</b>."
      ),
    });

    steps.push({
      target: ".official-warning",
      title: L("Aviso siempre visible", "Always-visible notice"),
      body: L(
        "Esta franja te recuerda en cada página que no somos una línea oficial de emergencia. Si hay peligro inmediato, busca primero la ayuda local disponible.",
        "This bar reminds you on every page that we are not an official emergency line. If there is immediate danger, seek locally available help first."
      ),
    });

    // -- Pasos propios de la página actual ---------------------------------
    if (path === "/") {
      steps.push({
        target: ".rv-hero-actions",
        title: L("Acciones rápidas", "Quick actions"),
        body: L(
          "Desde aquí entras al <b>mapa en vivo</b> con la situación del terremoto, o a los <b>teléfonos de emergencia</b> si necesitas ayuda urgente.",
          "From here you can open the <b>live map</b> with the earthquake situation, or the <b>emergency phone numbers</b> if you need urgent help."
        ),
      });
      steps.push({
        target: ".rv-stats",
        title: L("Cifras de un vistazo", "Numbers at a glance"),
        body: L(
          "Un resumen en números: registros visibles, casos de atención prioritaria, personas sin contacto y zonas representadas. Se actualizan con la información publicada.",
          "A quick numeric summary: visible records, priority-attention cases, people out of contact and zones represented. They update with the published information."
        ),
      });
      steps.push({
        target: ".rv-action-grid",
        title: L("¿Qué información buscas?", "What are you looking for?"),
        body: L(
          "Estas tarjetas te llevan directo a cada sección: <b>Personas</b>, <b>Edificios e incidentes</b>, <b>Servicios</b> (hospitales, refugios, agua…), <b>Mascotas</b>, <b>Zonas sin comunicación</b> y <b>Reconocimientos</b>.",
          "These cards take you straight to each section: <b>People</b>, <b>Buildings & incidents</b>, <b>Services</b> (hospitals, shelters, water…), <b>Pets</b>, <b>Areas without communication</b> and <b>Acknowledgements</b>."
        ),
      });
      steps.push({
        target: ".rv-registry-banner",
        title: L("Buscar o reportar un familiar", "Search or report a relative"),
        body: L(
          "Si buscas a una persona desaparecida, este botón te lleva al <b>registro ciudadano oficial</b>, que es donde se gestionan esos reportes. Nosotros lo complementamos con el mapa y los servicios.",
          "If you are looking for a missing person, this button takes you to the <b>official citizen registry</b>, where those reports are handled. We complement it with the map and services."
        ),
      });
    } else if (path.startsWith("/directorio/personas")) {
      steps.push({
        target: ".dir-chips",
        title: L("Pestañas de personas", "People tabs"),
        body: L(
          "Cambia entre <b>Desaparecidas</b>, <b>Localizadas</b> y <b>Fallecidas</b>. Por respeto a las familias, en Fallecidas no se publican nombres: hay un mensaje y un enlace al registro oficial.",
          "Switch between <b>Missing</b>, <b>Found</b> and <b>Deceased</b>. Out of respect for families, the Deceased tab lists no names: it shows a message and a link to the official registry."
        ),
      });
      steps.push({
        target: ".rv-dir-search",
        title: L("Buscador", "Search box"),
        body: L(
          "Escribe un nombre, dirección o lugar para filtrar los resultados al instante dentro de la pestaña en la que estés.",
          "Type a name, address or place to filter the results instantly within the tab you are on."
        ),
      });
      steps.push({
        target: ".dir-registries",
        title: L("Registros oficiales", "Official registries"),
        body: L(
          "Aquí reunimos los registros oficiales y ciudadanos para buscar y reportar personas, con una breve descripción de cada uno.",
          "Here we gather the official and citizen registries to search for and report people, with a short description of each."
        ),
      });
    } else if (path === "/directorio") {
      steps.push({
        target: ".rv-chipnav",
        title: L("Secciones del directorio", "Directory sections"),
        body: L(
          "Usa esta barra para moverte entre las secciones: personas, edificios e incidentes, servicios, zonas sin comunicación y mascotas.",
          "Use this bar to move between sections: people, buildings & incidents, services, areas without communication and pets."
        ),
      });
    }

    // -- Recorrido global (presente en todas las páginas) ------------------
    steps.push({
      target: '[data-tour="map"]',
      title: L("Mapa en vivo", "Live map"),
      body: L(
        "Un mapa interactivo con hospitales, refugios, puntos de agua, combustible, edificios dañados y zonas afectadas. Puedes activar o desactivar capas, usar tu ubicación (GPS) y buscar lugares cercanos.",
        "An interactive map with hospitals, shelters, water points, fuel, damaged buildings and affected areas. You can toggle layers, use your location (GPS) and search for nearby places."
      ),
    });
    steps.push({
      target: '[data-tour="directory"]',
      title: L("Directorio", "Directory"),
      body: L(
        "El directorio reúne cinco secciones — <b>Personas</b>, <b>Edificios e incidentes</b>, <b>Servicios</b>, <b>Zonas sin comunicación</b> y <b>Mascotas</b> — cada dato con su fuente. Puedes buscar dentro de cada una.",
        "The directory gathers five sections — <b>People</b>, <b>Buildings & incidents</b>, <b>Services</b>, <b>Areas without communication</b> and <b>Pets</b> — each item with its source. You can search within each one."
      ),
    });
    steps.push({
      target: '[data-tour="coordination"]',
      title: L("Coordinación", "Coordination"),
      body: L(
        "El centro de coordinación organiza la respuesta por roles (familias, rescatistas, recursos) y muestra las prioridades de rescate con su fuente.",
        "The coordination center organizes the response by roles (families, rescuers, resources) and shows rescue priorities with their source."
      ),
    });
    steps.push({
      target: '[data-tour="report"]',
      title: L("Reportar desaparecido", "Report a missing person"),
      body: L(
        "Este enlace abre el <b>registro ciudadano oficial</b> (en otra pestaña) para reportar o buscar a una persona desaparecida. Ahí se concentran esos datos.",
        "This link opens the <b>official citizen registry</b> (in a new tab) to report or search for a missing person. That is where this data is concentrated."
      ),
    });
    steps.push({
      target: '[data-tour="emergency"]',
      title: L("Emergencia", "Emergency"),
      body: L(
        "Acceso directo a teléfonos y contactos de emergencia. Recuerda: ante peligro inmediato, el 9-1-1 es siempre la primera opción.",
        "Direct access to emergency phones and contacts. Remember: in immediate danger, 9-1-1 is always the first option."
      ),
    });
    steps.push({
      target: ".lang-toggle",
      title: L("Idioma", "Language"),
      body: L(
        "Cambia el sitio entre <b>español</b> e <b>inglés</b> con un clic.",
        "Switch the site between <b>Spanish</b> and <b>English</b> with one click."
      ),
    });
    steps.push({
      target: ".theme-toggle",
      title: L("Modo claro u oscuro", "Light or dark mode"),
      body: L(
        "Alterna entre el modo oscuro y el modo claro (“sol”), más legible con luz directa.",
        "Toggle between dark mode and light (“sun”) mode, which is easier to read in bright light."
      ),
    });
    steps.push({
      target: ".bandwidth-toggle",
      title: L("Modo ligero", "Light data mode"),
      body: L(
        "Activa el <b>modo ligero</b> para consumir menos datos y cargar más rápido cuando tienes poca señal de internet.",
        "Turn on <b>light data mode</b> to use less data and load faster when your internet signal is weak."
      ),
    });
    steps.push({
      target: ".site-footer",
      title: L("Pie de página", "Footer"),
      body: L(
        "Abajo siempre encontrarás más enlaces: todas las secciones, cómo <b>reportar un problema</b>, la página de <b>privacidad y uso responsable</b> y las fuentes de los datos.",
        "At the bottom you’ll always find more links: all sections, how to <b>report a problem</b>, the <b>privacy & responsible use</b> page and the data sources."
      ),
    });
    steps.push({
      target: ".tour-fab",
      title: L("Puedes volver cuando quieras", "Come back anytime"),
      body: L(
        "Esta guía siempre está disponible en este botón. Ábrela cuando tengas una duda. ¡Gracias por estar aquí!",
        "This guide is always available on this button. Open it whenever you have a question. Thank you for being here!"
      ),
    });

    // Conserva solo los pasos cuyo objetivo existe en esta página.
    return steps.filter((s) => !s.target || document.querySelector(s.target));
  }

  // -- Estado y elementos ---------------------------------------------------
  let steps = [];
  let idx = 0;
  let active = false;
  let lastFocus = null;
  let dot = null;

  const fab = document.createElement("button");
  fab.type = "button";
  fab.className = "tour-fab";
  fab.setAttribute("aria-label", T.open);
  fab.innerHTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9.1 9a3 3 0 1 1 4.5 2.6c-.8.5-1.6 1.1-1.6 2.1"/><circle cx="12" cy="17.5" r=".6" fill="currentColor" stroke="none"/></svg>' +
    '<span class="tour-fab-label">' + T.title + "</span>";

  let overlay, spot, bubble;

  function ensureDom() {
    if (overlay) return;
    overlay = document.createElement("div");
    overlay.className = "tour-overlay";
    overlay.setAttribute("aria-hidden", "true");

    spot = document.createElement("div");
    spot.className = "tour-spot";

    bubble = document.createElement("div");
    bubble.className = "tour-bubble";
    bubble.setAttribute("role", "dialog");
    bubble.setAttribute("aria-modal", "true");
    bubble.setAttribute("aria-live", "polite");
    bubble.tabIndex = -1;

    overlay.appendChild(spot);
    document.body.appendChild(overlay);
    document.body.appendChild(bubble);

    overlay.addEventListener("click", stop);
  }

  // -- Navegación de la barra (abrir menú colapsado en móvil) ---------------
  function ensureNavVisible(target) {
    const nav = document.getElementById("navPrincipal");
    if (nav && target && nav.contains(target) && !nav.classList.contains("show")) {
      nav.classList.add("show");
      nav.dataset.tourForced = "1";
    }
  }
  function restoreNav() {
    const nav = document.getElementById("navPrincipal");
    if (nav && nav.dataset.tourForced) {
      nav.classList.remove("show");
      delete nav.dataset.tourForced;
    }
  }

  // -- Render de un paso ----------------------------------------------------
  function render() {
    const step = steps[idx];
    const target = step.target ? document.querySelector(step.target) : null;
    restoreNav();
    if (target) ensureNavVisible(target);

    const isLast = idx === steps.length - 1;
    bubble.innerHTML =
      '<button type="button" class="tour-x" aria-label="' + T.close + '">&times;</button>' +
      '<p class="tour-eyebrow">' + T.step + " " + (idx + 1) + " " + T.of + " " + steps.length + "</p>" +
      '<h2 class="tour-h">' + step.title + "</h2>" +
      '<div class="tour-body">' + step.body + "</div>" +
      '<div class="tour-actions">' +
      '<button type="button" class="tour-skip">' + T.skip + "</button>" +
      '<div class="tour-nav">' +
      (idx > 0 ? '<button type="button" class="tour-btn tour-prev">' + T.prev + "</button>" : "") +
      '<button type="button" class="tour-btn tour-primary tour-next">' + (isLast ? T.finish : T.next) + "</button>" +
      "</div></div>";

    bubble.querySelector(".tour-x").addEventListener("click", stop);
    bubble.querySelector(".tour-skip").addEventListener("click", stop);
    bubble.querySelector(".tour-next").addEventListener("click", () => (isLast ? stop() : go(1)));
    const prev = bubble.querySelector(".tour-prev");
    if (prev) prev.addEventListener("click", () => go(-1));

    position(target);
    bubble.focus();
  }

  function position(target) {
    const pad = 8;
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    if (target && target.getBoundingClientRect) {
      target.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
    }
    // Reposiciona tras un respiro para que termine el scroll.
    requestAnimationFrame(() => {
      const r = target ? target.getBoundingClientRect() : null;
      if (r && r.width && r.height) {
        // Recuadro resaltado alrededor del elemento.
        spot.classList.remove("is-collapsed");
        spot.style.top = r.top - pad + "px";
        spot.style.left = r.left - pad + "px";
        spot.style.width = r.width + pad * 2 + "px";
        spot.style.height = r.height + pad * 2 + "px";
      } else {
        // Sin objetivo (bienvenida): el recuadro se colapsa al centro, pero su
        // sombra gigante sigue oscureciendo toda la pantalla.
        spot.classList.add("is-collapsed");
        spot.style.top = vh / 2 + "px";
        spot.style.left = vw / 2 + "px";
        spot.style.width = "0px";
        spot.style.height = "0px";
      }

      const bw = bubble.offsetWidth;
      const bh = bubble.offsetHeight;
      let top, left;
      if (!r || !r.width) {
        top = (vh - bh) / 2;
        left = (vw - bw) / 2;
      } else {
        const below = r.bottom + 14;
        const above = r.top - bh - 14;
        top = below + bh <= vh - 8 ? below : above >= 8 ? above : Math.max(8, (vh - bh) / 2);
        left = r.left + r.width / 2 - bw / 2;
      }
      left = Math.min(Math.max(12, left), vw - bw - 12);
      top = Math.min(Math.max(12, top), vh - bh - 12);
      bubble.style.top = top + "px";
      bubble.style.left = left + "px";
    });
  }

  // -- Control --------------------------------------------------------------
  function go(delta) {
    idx = Math.min(Math.max(0, idx + delta), steps.length - 1);
    render();
  }

  function start() {
    steps = buildSteps();
    if (!steps.length) return;
    ensureDom();
    idx = 0;
    active = true;
    lastFocus = document.activeElement;
    document.body.classList.add("tour-active");
    overlay.classList.add("is-on");
    bubble.classList.add("is-on");
    fab.classList.remove("tour-fab-hint");
    try { localStorage.setItem("rav-tour-seen", "1"); } catch (_) {}
    if (dot) { dot.remove(); dot = null; }
    render();
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", onReflow);
    window.addEventListener("scroll", onReflow, true);
  }

  function stop() {
    if (!active) return;
    active = false;
    restoreNav();
    document.body.classList.remove("tour-active");
    overlay.classList.remove("is-on");
    bubble.classList.remove("is-on");
    window.removeEventListener("keydown", onKey);
    window.removeEventListener("resize", onReflow);
    window.removeEventListener("scroll", onReflow, true);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  let reflowQueued = false;
  function onReflow() {
    if (reflowQueued) return;
    reflowQueued = true;
    requestAnimationFrame(() => {
      reflowQueued = false;
      if (active) position(steps[idx].target ? document.querySelector(steps[idx].target) : null);
    });
  }

  function onKey(e) {
    if (e.key === "Escape") stop();
    else if (e.key === "ArrowRight") go(1);
    else if (e.key === "ArrowLeft") go(-1);
  }

  // -- Montaje --------------------------------------------------------------
  function mount() {
    document.body.appendChild(fab);
    fab.addEventListener("click", start);

    // Pista discreta la primera vez (un punto), sin abrir nada solo.
    let seen = null;
    try { seen = localStorage.getItem("rav-tour-seen"); } catch (_) {}
    if (!seen) {
      fab.classList.add("tour-fab-hint");
      dot = document.createElement("span");
      dot.className = "tour-fab-dot";
      dot.setAttribute("aria-hidden", "true");
      fab.appendChild(dot);
    }
  }

  if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
