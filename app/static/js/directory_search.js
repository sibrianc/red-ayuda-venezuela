(() => {
  "use strict";

  // Búsqueda en vivo del directorio: mientras se escribe, consulta al servidor (que ya
  // filtra y pagina) y reemplaza solo los resultados. Cubre TODA la data, no solo la
  // página visible. Mejora progresiva: sin JS, el formulario envía normal.
  const form = document.querySelector(".rv-dir-search");
  const results = document.getElementById("dir-results");
  if (!form || !results) return;
  const input = form.querySelector('input[name="q"]');
  if (!input) return;

  let timer = null;
  let controller = null;
  let lastUrl = location.pathname + location.search;

  const run = async () => {
    const params = new URLSearchParams(location.search);
    const value = input.value.trim();
    if (value) params.set("q", value); else params.delete("q");
    params.delete("page"); // nueva búsqueda → primera página
    const qs = params.toString();
    const url = location.pathname + (qs ? "?" + qs : "");
    if (url === lastUrl) return;
    lastUrl = url;

    if (controller) controller.abort();
    controller = new AbortController();
    results.setAttribute("aria-busy", "true");
    try {
      const resp = await fetch(url, {
        headers: { "X-Requested-With": "fetch" },
        signal: controller.signal,
      });
      if (!resp.ok) return;
      const html = await resp.text();
      const fresh = new DOMParser().parseFromString(html, "text/html").getElementById("dir-results");
      if (fresh) results.replaceChildren(...fresh.childNodes);
      history.replaceState(null, "", url);
    } catch (_) {
      /* abortado o sin red: se deja lo que hay */
    } finally {
      results.removeAttribute("aria-busy");
    }
  };

  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(run, 220);
  });
  // No recargar toda la página al enviar: ya filtramos en vivo.
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    clearTimeout(timer);
    run();
  });
})();
