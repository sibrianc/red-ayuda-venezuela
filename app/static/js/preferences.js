(() => {
  "use strict";

  const storageKey = "rav-bandwidth-mode";
  const root = document.documentElement;
  let storedMode = null;
  try {
    storedMode = localStorage.getItem(storageKey);
  } catch (_) {
    storedMode = null;
  }
  const initialMode = storedMode === "low" ? "low" : "standard";

  const applyMode = (mode) => {
    root.dataset.bandwidth = mode;
    document.querySelectorAll("[data-bandwidth-toggle]").forEach((button) => {
      const low = mode === "low";
      button.setAttribute("aria-pressed", low ? "true" : "false");
      button.textContent = low ? "Salir del modo ligero" : "Modo ligero";
    });
  };

  applyMode(initialMode);

  window.addEventListener("DOMContentLoaded", () => {
    applyMode(root.dataset.bandwidth);
    document.querySelectorAll("[data-bandwidth-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        const nextMode = root.dataset.bandwidth === "low" ? "standard" : "low";
        let persisted = false;
        try {
          localStorage.setItem(storageKey, nextMode);
          persisted = true;
        } catch (_) {
          // The preference still applies for the current page when storage is blocked.
        }
        applyMode(nextMode);
        if (persisted) window.location.reload();
      });
    });
  });
})();
