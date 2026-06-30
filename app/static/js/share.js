/* Botón "copiar enlace" de los grupos de compartir. Copia al portapapeles y
   muestra una confirmación breve. Sin dependencias. */
(() => {
  "use strict";

  async function copy(text) {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch (_) {
      /* cae al método antiguo */
    }
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "absolute";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch (_) {
      return false;
    }
  }

  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-share-copy]");
    if (!btn) return;
    const ok = await copy(btn.getAttribute("data-share-copy"));
    const toast = btn.querySelector("[data-share-toast]");
    if (ok && toast) {
      toast.hidden = false;
      btn.classList.add("is-copied");
      setTimeout(() => {
        toast.hidden = true;
        btn.classList.remove("is-copied");
      }, 1800);
    }
  });
})();
