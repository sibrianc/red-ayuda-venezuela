window.addEventListener("DOMContentLoaded", () => {
  "use strict";

  const wizard = document.querySelector("[data-report-wizard]");
  if (!wizard) return;

  const panels = [...wizard.querySelectorAll("[data-wizard-panel]")];
  const indicators = [...document.querySelectorAll("[data-wizard-indicator]")];
  const liveStatus = document.querySelector("[data-wizard-status]");
  let currentStep = Math.max(
    0,
    panels.findIndex((panel) => panel.querySelector(".has-error"))
  );

  const focusHeading = (panel) => {
    const legend = panel.querySelector("legend");
    if (!legend) return;
    legend.setAttribute("tabindex", "-1");
    legend.focus({ preventScroll: true });
  };

  const showStep = (index, options = {}) => {
    currentStep = Math.min(Math.max(index, 0), panels.length - 1);
    panels.forEach((panel, panelIndex) => {
      panel.hidden = panelIndex !== currentStep;
    });
    indicators.forEach((indicator, indicatorIndex) => {
      indicator.classList.toggle("is-current", indicatorIndex === currentStep);
      indicator.classList.toggle("is-complete", indicatorIndex < currentStep);
      if (indicatorIndex === currentStep) indicator.setAttribute("aria-current", "step");
      else indicator.removeAttribute("aria-current");
    });
    if (liveStatus) liveStatus.textContent = `Paso ${currentStep + 1} de ${panels.length}.`;
    if (options.focus !== false) {
      focusHeading(panels[currentStep]);
      panels[currentStep].scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const firstInvalidControl = (panel) => {
    const controls = [...panel.querySelectorAll("input, select, textarea")];
    return controls.find((control) => {
      if (control.disabled || control.type === "hidden") return false;
      return !control.checkValidity();
    });
  };

  const validatePanel = (panel) => {
    const invalid = firstInvalidControl(panel);
    if (!invalid) return true;
    invalid.reportValidity();
    invalid.focus();
    return false;
  };

  wizard.classList.add("is-enhanced");
  document.querySelectorAll(".optional-panel .has-error").forEach((error) => {
    const details = error.closest("details");
    if (details) details.open = true;
  });
  showStep(currentStep, { focus: false });

  wizard.querySelectorAll("[data-wizard-next]").forEach((button) => {
    button.addEventListener("click", () => {
      if (validatePanel(panels[currentStep])) showStep(currentStep + 1);
    });
  });
  wizard.querySelectorAll("[data-wizard-back]").forEach((button) => {
    button.addEventListener("click", () => showStep(currentStep - 1));
  });

  wizard.addEventListener("submit", (event) => {
    for (let index = 0; index < panels.length; index += 1) {
      const invalid = firstInvalidControl(panels[index]);
      if (!invalid) continue;
      event.preventDefault();
      showStep(index, { focus: false });
      invalid.reportValidity();
      invalid.focus();
      return;
    }
  });

  const assistant = wizard.querySelector("[data-location-assistant]");
  const locationButton = assistant?.querySelector("[data-use-location]");
  const locationStatus = assistant?.querySelector("[data-location-status]");
  const latitude = wizard.querySelector("[data-location-latitude]");
  const longitude = wizard.querySelector("[data-location-longitude]");

  const locationMessage = (message, state = "") => {
    if (!locationStatus) return;
    locationStatus.textContent = message;
    locationStatus.dataset.state = state;
  };

  if (locationButton) {
    locationButton.addEventListener("click", () => {
      if (!navigator.geolocation) {
        locationMessage("Este dispositivo no permite obtener la ubicación. Escribe la zona manualmente.", "error");
        return;
      }
      locationButton.disabled = true;
      locationMessage("Solicitando permiso al dispositivo…", "loading");
      navigator.geolocation.getCurrentPosition(
        (position) => {
          if (latitude) latitude.value = position.coords.latitude.toFixed(6);
          if (longitude) longitude.value = position.coords.longitude.toFixed(6);
          locationButton.disabled = false;
          locationButton.textContent = "Actualizar ubicación";
          locationMessage("Ubicación añadida de forma privada. En el mapa público se mostrará aproximada.", "success");
        },
        () => {
          locationButton.disabled = false;
          locationMessage("No pudimos obtener la ubicación. Puedes continuar escribiendo solo la zona.", "error");
        },
        { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
      );
    });
  }
});
