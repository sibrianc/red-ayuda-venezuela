window.addEventListener("DOMContentLoaded", async () => {
  "use strict";

  const element = document.getElementById("report-map");
  const status = document.getElementById("map-status");
  const resultList = document.querySelector("[data-map-results]");
  if (!element || typeof L === "undefined") return;

  const typeMeta = {
    help_request: { label: "Necesidad", color: "#d95c4f", className: "need" },
    resource_offer: { label: "Recurso", color: "#168579", className: "resource" },
    location_report: { label: "Zona afectada", color: "#d59726", className: "affected" },
    missing_person: { label: "Persona sin contacto", color: "#5e6ad2", className: "missing" },
  };

  const map = L.map(element, {
    scrollWheelZoom: false,
    zoomControl: false,
    preferCanvas: true,
  }).setView([8.0, -66.0], 6);
  L.control.zoom({ position: "bottomright" }).addTo(map);
  L.tileLayer(element.dataset.tileUrl, {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  const pointLayer = L.layerGroup().addTo(map);
  const densityLayer = L.layerGroup();
  let reports = [];
  let activeFilter = "all";
  let activeMode = "points";

  const filteredReports = () => reports.filter((report) => activeFilter === "all" || report.type === activeFilter);

  const popupFor = (report) => {
    const popup = document.createElement("div");
    popup.className = "map-popup";
    const meta = document.createElement("span");
    meta.className = `map-popup-type ${typeMeta[report.type]?.className || ""}`;
    meta.textContent = typeMeta[report.type]?.label || "Reporte";
    const heading = document.createElement("strong");
    heading.textContent = report.title;
    const location = document.createElement("p");
    location.textContent = report.location.label;
    const link = document.createElement("a");
    link.href = report.url;
    link.textContent = "Ver información revisada";
    popup.append(meta, heading, location, link);
    return popup;
  };

  const renderPoints = (visibleReports) => {
    pointLayer.clearLayers();
    visibleReports.forEach((report) => {
      const meta = typeMeta[report.type] || typeMeta.help_request;
      const point = [report.location.latitude, report.location.longitude];
      L.circleMarker(point, {
        radius: report.priority === "critical" ? 10 : 8,
        weight: 3,
        color: "#ffffff",
        fillColor: meta.color,
        fillOpacity: 0.94,
        className: `operational-marker marker-${meta.className}`,
      }).addTo(pointLayer).bindPopup(popupFor(report), { minWidth: 220 });
    });
  };

  const densityGroups = (visibleReports) => {
    const groups = new Map();
    visibleReports.forEach((report) => {
      const latitude = Math.round(report.location.latitude * 10) / 10;
      const longitude = Math.round(report.location.longitude * 10) / 10;
      const key = `${latitude}:${longitude}`;
      const group = groups.get(key) || { latitude, longitude, reports: [] };
      group.reports.push(report);
      groups.set(key, group);
    });
    return [...groups.values()];
  };

  const renderDensity = (visibleReports) => {
    densityLayer.clearLayers();
    const groups = densityGroups(visibleReports);
    const maximum = Math.max(...groups.map((group) => group.reports.length), 1);
    groups.forEach((group) => {
      const count = group.reports.length;
      const intensity = count / maximum;
      const circle = L.circleMarker([group.latitude, group.longitude], {
        radius: 18 + Math.sqrt(count) * 8,
        weight: 2,
        color: intensity > 0.65 ? "#9f352f" : "#bc7622",
        fillColor: intensity > 0.65 ? "#d95c4f" : "#f0ad3c",
        fillOpacity: 0.3 + intensity * 0.35,
        className: "density-marker",
      }).addTo(densityLayer);
      const summary = document.createElement("div");
      summary.className = "density-popup";
      const total = document.createElement("strong");
      total.textContent = `${count} ${count === 1 ? "reporte revisado" : "reportes revisados"}`;
      const note = document.createElement("p");
      note.textContent = "Concentración aproximada por sector; no representa una ubicación exacta.";
      summary.append(total, note);
      circle.bindPopup(summary, { minWidth: 230 });
    });
  };

  const renderList = (visibleReports) => {
    if (!resultList) return;
    resultList.replaceChildren();
    visibleReports.slice(0, 12).forEach((report) => {
      const meta = typeMeta[report.type] || typeMeta.help_request;
      const article = document.createElement("article");
      article.className = "map-result-card";
      const label = document.createElement("span");
      label.className = `map-result-type ${meta.className}`;
      label.textContent = meta.label;
      const heading = document.createElement("h3");
      const link = document.createElement("a");
      link.href = report.url;
      link.textContent = report.title;
      heading.append(link);
      const location = document.createElement("p");
      location.textContent = report.location.label;
      article.append(label, heading, location);
      resultList.append(article);
    });
    if (!visibleReports.length) {
      const empty = document.createElement("p");
      empty.className = "map-empty-state";
      empty.textContent = "No hay reportes aprobados para este filtro.";
      resultList.append(empty);
    }
  };

  const updateMetrics = () => {
    const total = document.querySelector("[data-map-total]");
    const priority = document.querySelector("[data-map-priority]");
    const zones = document.querySelector("[data-map-zones]");
    const updated = document.querySelector("[data-map-updated]");
    if (total) total.textContent = String(reports.length);
    if (priority) priority.textContent = String(reports.filter((report) => ["critical", "high"].includes(report.priority)).length);
    if (zones) zones.textContent = String(new Set(reports.map((report) => report.location.label.trim().toLocaleLowerCase("es"))).size);
    if (updated) {
      const newest = reports.reduce((latest, report) => Math.max(latest, Date.parse(report.updated_at) || 0), 0);
      updated.textContent = newest
        ? new Intl.DateTimeFormat("es-VE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(newest))
        : "Sin datos";
    }
  };

  const render = () => {
    const visibleReports = filteredReports();
    renderPoints(visibleReports);
    renderDensity(visibleReports);
    renderList(visibleReports);
    if (activeMode === "density") {
      map.removeLayer(pointLayer);
      densityLayer.addTo(map);
    } else {
      map.removeLayer(densityLayer);
      pointLayer.addTo(map);
    }
    if (status) status.textContent = `${visibleReports.length} ${visibleReports.length === 1 ? "reporte visible" : "reportes visibles"} con ubicación aproximada.`;
  };

  document.querySelectorAll("[data-map-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      activeFilter = button.dataset.mapFilter;
      document.querySelectorAll("[data-map-filter]").forEach((candidate) => {
        const active = candidate === button;
        candidate.classList.toggle("is-active", active);
        candidate.setAttribute("aria-pressed", active ? "true" : "false");
      });
      render();
    });
  });

  document.querySelectorAll("[data-map-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      activeMode = button.dataset.mapMode;
      document.querySelectorAll("[data-map-mode]").forEach((candidate) => {
        const active = candidate === button;
        candidate.classList.toggle("is-active", active);
        candidate.setAttribute("aria-pressed", active ? "true" : "false");
      });
      render();
    });
  });

  try {
    const response = await fetch(element.dataset.mapEndpoint, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("map-data");
    const payload = await response.json();
    reports = payload.reports.filter((report) => report.location?.latitude != null && report.location?.longitude != null);
    updateMetrics();
    render();
    if (reports.length) {
      map.fitBounds(reports.map((report) => [report.location.latitude, report.location.longitude]), {
        padding: [48, 48],
        maxZoom: 12,
      });
    }
  } catch (_) {
    if (status) status.textContent = "El mapa no pudo cargarse. Usa el listado accesible de reportes.";
    if (resultList) {
      const error = document.createElement("p");
      error.className = "map-empty-state";
      error.textContent = "La vista cartográfica no está disponible en este momento.";
      resultList.replaceChildren(error);
    }
  }
});
