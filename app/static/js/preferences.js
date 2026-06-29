(() => {
  "use strict";

  const root = document.documentElement;

  const read = (key) => {
    try { return localStorage.getItem(key); } catch (_) { return null; }
  };
  const write = (key, value) => {
    try { localStorage.setItem(key, value); return true; } catch (_) { return false; }
  };

  // --- Tema: OSCURO por defecto + modo "sol" (claro, alto contraste) ---------
  const themeKey = "rav-theme";
  const applyTheme = (theme) => {
    root.dataset.theme = theme;
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      const sun = theme === "light";
      button.setAttribute("aria-pressed", sun ? "true" : "false");
      const label = button.querySelector("[data-theme-label]");
      if (label) label.textContent = sun ? "Modo oscuro" : "Modo sol";
    });
    window.dispatchEvent(new CustomEvent("rav:themechange", { detail: { theme } }));
  };
  applyTheme(read(themeKey) === "light" ? "light" : "dark");

  // --- Ancho de banda: modo ligero (sin teselas ni decoración) ---------------
  const bandwidthKey = "rav-bandwidth-mode";
  const applyBandwidth = (mode) => {
    root.dataset.bandwidth = mode;
    document.querySelectorAll("[data-bandwidth-toggle]").forEach((button) => {
      const low = mode === "low";
      button.setAttribute("aria-pressed", low ? "true" : "false");
      button.textContent = low ? "Salir del modo ligero" : "Modo ligero";
    });
  };
  applyBandwidth(read(bandwidthKey) === "low" ? "low" : "standard");

  window.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        const next = root.dataset.theme === "light" ? "dark" : "light";
        write(themeKey, next);
        applyTheme(next);
      });
    });

    document.querySelectorAll("[data-bandwidth-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        const next = root.dataset.bandwidth === "low" ? "standard" : "low";
        const persisted = write(bandwidthKey, next);
        applyBandwidth(next);
        if (persisted) window.location.reload();
      });
    });
  });
})();
