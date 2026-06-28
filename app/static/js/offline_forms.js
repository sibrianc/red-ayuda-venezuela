(() => {
  "use strict";
  const sensitiveNames = new Set([
    "exact_address_private",
    "description_private",
    "reporter_name_private",
    "reporter_contact_private",
    "relationship_to_person_private",
    "medical_information_private",
    "contact",
    "latitude",
    "longitude",
  ]);
  const maxAgeMs = 24 * 60 * 60 * 1000;

  const clearTarget = document.querySelector("[data-clear-draft-key]");
  if (clearTarget?.dataset.clearDraftKey) {
    localStorage.removeItem(clearTarget.dataset.clearDraftKey);
  }

  const controls = document.querySelector("[data-draft-controls]");
  const form = document.querySelector("[data-draft-form]");
  if (!controls || !form) return;
  const key = controls.dataset.draftKey;
  const status = controls.querySelector("[data-draft-controls] .draft-status") || controls.querySelector(".draft-status");
  let enabled = localStorage.getItem(`${key}-enabled`) === "yes";

  const say = (message) => { if (status) status.textContent = message; };
  const fields = [...form.elements].filter((field) => field.name && !sensitiveNames.has(field.name) && !["csrf_token", "website", "submit"].includes(field.name));

  const restore = () => {
    const raw = localStorage.getItem(key);
    if (!raw) return;
    try {
      const draft = JSON.parse(raw);
      if (Date.now() - draft.savedAt > maxAgeMs) {
        localStorage.removeItem(key);
        return;
      }
      fields.forEach((field) => {
        if (!(field.name in draft.values)) return;
        if (field.type === "checkbox") field.checked = Boolean(draft.values[field.name]);
        else field.value = draft.values[field.name];
      });
      say("Borrador no sensible restaurado.");
    } catch (_) {
      localStorage.removeItem(key);
    }
  };
  const save = () => {
    if (!enabled) return;
    const values = {};
    fields.forEach((field) => { values[field.name] = field.type === "checkbox" ? field.checked : field.value; });
    localStorage.setItem(key, JSON.stringify({ savedAt: Date.now(), values }));
    say("Borrador guardado en este dispositivo.");
  };
  controls.querySelector("[data-enable-draft]")?.addEventListener("click", () => {
    enabled = true;
    localStorage.setItem(`${key}-enabled`, "yes");
    save();
  });
  controls.querySelector("[data-clear-draft]")?.addEventListener("click", () => {
    localStorage.removeItem(key);
    localStorage.removeItem(`${key}-enabled`);
    enabled = false;
    say("Borrador borrado.");
  });
  form.addEventListener("input", save);
  if (enabled) restore();
})();
