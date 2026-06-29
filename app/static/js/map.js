window.addEventListener("DOMContentLoaded", async () => {
  "use strict";

  const element = document.getElementById("report-map");
  const status = document.getElementById("map-status");
  const resultList = document.querySelector("[data-map-results]");
  if (!element) return;
  const lowBandwidth = document.documentElement.dataset.bandwidth === "low";
  const mapAvailable = !lowBandwidth && typeof L !== "undefined";

  const typeMeta = {
    help_request: { label: "Necesidad", color: "#d95c4f", className: "need" },
    resource_offer: { label: "Recurso", color: "#168579", className: "resource" },
    location_report: { label: "Zona afectada", color: "#d59726", className: "affected" },
    missing_person: { label: "Persona sin contacto", color: "#5e6ad2", className: "missing" },
  };
  const serviceMeta = {
    hospital: { label: "Hospital", color: "#e2473d" },
    clinic: { label: "Clínica", color: "#27a59a" },
    pharmacy: { label: "Farmacia", color: "#4cae6a" },
    fire_station: { label: "Bomberos", color: "#ef7d2e" },
    police: { label: "Policía", color: "#2a6fd6" },
    shelter: { label: "Refugio", color: "#f3c534" },
    water_point: { label: "Punto de agua", color: "#2a8fd6" },
    community_center: { label: "Centro comunitario", color: "#8a7de0" },
    other: { label: "Servicio", color: "#9aa6ad" },
  };
  const severityColor = (severity) =>
    ({ critical: "#e5443a", high: "#ef7d2e", medium: "#f3c534", low: "#46b06a" }[severity] || "#ef7d2e");
  const severityLabel = (severity) =>
    ({ critical: "Crítico", high: "Alto", medium: "Medio", low: "Bajo" }[severity] || "Prioridad");

  const dotIcon = (kind, color, severity) =>
    L.divIcon({
      className: `rav-pin ${kind}${severity ? " " + severity : ""}`,
      html: `<span style="--c:${color}"></span>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10],
      popupAnchor: [0, -10],
    });

  let map = null;
  let pointLayer = null;
  let densityLayer = null;
  let eventsLayer = null;
  let servicesLayer = null;
  let incidentsCluster = null;
  let incidentsHeat = null;
  let applyIncidentLayers = () => {};
  if (mapAvailable) {
    map = L.map(element, { scrollWheelZoom: false, zoomControl: false, preferCanvas: true })
      .setView([10.5, -66.9], 7);
    L.control.zoom({ position: "bottomright" }).addTo(map);

    // Mapa base profesional CARTO (oscuro por defecto; "voyager" claro en modo sol).
    const cartoUrl = (theme) => theme === "light"
      ? "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
      : "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
    let baseLayer = null;
    const setBasemap = () => {
      const theme = document.documentElement.dataset.theme === "light" ? "light" : "dark";
      if (baseLayer) map.removeLayer(baseLayer);
      baseLayer = L.tileLayer(cartoUrl(theme), {
        subdomains: "abcd",
        maxZoom: 20,
        detectRetina: true,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      }).addTo(map);
      baseLayer.bringToBack();
    };
    setBasemap();
    window.addEventListener("rav:themechange", setBasemap);

    const clusterGroup = () => (typeof L.markerClusterGroup === "function"
      ? L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 46, spiderfyOnMaxZoom: true, chunkedLoading: true })
      : L.layerGroup());

    // Mapa de calor (KDE) para el zoom-out: muchos kernels gaussianos que se suman
    // en un campo continuo y se colorean por densidad (verde→rojo).
    incidentsHeat = (typeof L.heatLayer === "function")
      ? L.heatLayer([], { radius: 34, blur: 24, maxZoom: 9, max: 8, minOpacity: 0.42,
          gradient: { 0.2: "#37d06f", 0.4: "#f0d836", 0.6: "#f4a23a", 0.8: "#ef5f2e", 1: "#e5253a" } })
      : null;
    eventsLayer = L.layerGroup().addTo(map);
    servicesLayer = clusterGroup().addTo(map);
    incidentsCluster = clusterGroup();
    pointLayer = L.layerGroup().addTo(map);
    densityLayer = L.layerGroup();

    // Transición por zoom (lo que pediste): a zoom bajo manda el CALOR; al acercar
    // (>= umbral) el calor desaparece y aparecen los clusters/puntos separados, sin estorbar.
    const HEAT_MAX_ZOOM = 11;
    applyIncidentLayers = () => {
      if (!map) return;
      const zoomedIn = map.getZoom() >= HEAT_MAX_ZOOM;
      const showHeat = layerVisible.incidents && !zoomedIn;
      const showCluster = layerVisible.incidents && zoomedIn;
      if (incidentsHeat) showHeat ? incidentsHeat.addTo(map) : map.removeLayer(incidentsHeat);
      if (incidentsCluster) showCluster ? incidentsCluster.addTo(map) : map.removeLayer(incidentsCluster);
    };
    map.on("zoomend", applyIncidentLayers);
  } else {
    const notice = document.createElement("div");
    notice.className = "low-bandwidth-map-notice";
    const text = document.createElement("p");
    const heading = document.createElement("strong");
    heading.textContent = lowBandwidth ? "Mapa visual pausado" : "Mapa visual no disponible";
    text.append(
      heading,
      lowBandwidth
        ? "El modo ligero evita descargar teselas. Usa el listado accesible junto al mapa."
        : "Usa el listado accesible de información revisada."
    );
    notice.append(text);
    element.replaceChildren(notice);
  }

  let reports = [];
  let events = [];
  let services = [];
  let incidents = [];
  let situation = [];
  let intensity = [];
  let activeFilter = "all";
  let activeMode = "points";
  // Prioridad: los afectados. Los sismos quedan apagados por defecto (estorban y, con
  // datos de muestra, caen en el mar); siguen disponibles con su toggle.
  const layerVisible = { incidents: true, events: false, services: true, reports: true };
  const filteredReports = () => reports.filter((report) => activeFilter === "all" || report.type === activeFilter);

  const popupRow = (parent, text, className) => {
    if (!text) return;
    const p = document.createElement("p");
    if (className) p.className = className;
    p.textContent = text;
    parent.append(p);
  };

  // --- Incidentes de prioridad (heatmap + clustering + popup rico) ----------
  const incidentPopup = (incident) => {
    const popup = document.createElement("div");
    popup.className = "map-popup";
    const badge = document.createElement("span");
    badge.className = `map-popup-type sev-${incident.severity}`;
    badge.textContent = `${incident.category_label} · ${severityLabel(incident.severity)}`;
    const heading = document.createElement("strong");
    heading.textContent = incident.label;
    popup.append(badge, heading);
    popupRow(popup, incident.address);
    popupRow(popup, incident.situation_note);
    if (incident.status) popupRow(popup, `Estado: ${incident.status}`, "map-popup-source");
    popupRow(popup, incident.source_name || incident.attribution, "map-popup-source");
    return popup;
  };
  const renderIncidents = () => {
    if (incidentsCluster) incidentsCluster.clearLayers();
    // Marcadores: SOLO incidentes específicos (edificio + dirección). Posición exacta.
    incidents.forEach((incident) => {
      if (incidentsCluster) {
        const marker = L.marker([incident.latitude, incident.longitude], {
          icon: dotIcon("incident", severityColor(incident.severity), incident.severity),
        });
        marker.bindPopup(incidentPopup(incident), { minWidth: 248 });
        incidentsCluster.addLayer(marker);
      }
    });
    // El mapa de calor usa la capa de intensidad de zonas afectadas (no los incidentes).
    if (incidentsHeat) incidentsHeat.setLatLngs(intensity);
    applyIncidentLayers();
  };

  // --- Sismos ---------------------------------------------------------------
  const quakeColor = (magnitude) => {
    if (magnitude == null) return "#7c8a93";
    if (magnitude >= 6) return "#c0271f";
    if (magnitude >= 5) return "#e2473d";
    if (magnitude >= 4) return "#ef7d2e";
    if (magnitude >= 3) return "#f3c534";
    return "#46b06a";
  };
  const renderEvents = () => {
    if (!eventsLayer) return;
    eventsLayer.clearLayers();
    if (!layerVisible.events) return;
    events.forEach((event) => {
      const magnitude = event.magnitude;
      const radius = 4 + (magnitude != null ? Math.max(magnitude, 0) * 2.1 : 2);
      const marker = L.circleMarker([event.latitude, event.longitude], {
        radius, weight: 1.5, color: "#ffffff", fillColor: quakeColor(magnitude),
        fillOpacity: 0.82, className: "quake-marker",
      });
      const popup = document.createElement("div");
      popup.className = "map-popup";
      const meta = document.createElement("span");
      meta.className = "map-popup-type quake";
      meta.textContent = magnitude != null ? `Magnitud ${magnitude}` : "Sismo";
      const heading = document.createElement("strong");
      heading.textContent = event.place || event.title || "Sismo";
      popup.append(meta, heading);
      popupRow(popup, event.occurred_at
        ? new Intl.DateTimeFormat("es-VE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(event.occurred_at))
        : "");
      popupRow(popup, event.attribution, "map-popup-source");
      marker.bindPopup(popup, { minWidth: 220 }).addTo(eventsLayer);
    });
  };

  // --- Servicios (directorio, agrupados) ------------------------------------
  const renderServices = () => {
    if (!servicesLayer) return;
    servicesLayer.clearLayers();
    if (!layerVisible.services) return;
    services.forEach((service) => {
      const meta = serviceMeta[service.category] || serviceMeta.other;
      const marker = L.marker([service.latitude, service.longitude], {
        icon: dotIcon("service", meta.color),
      });
      const popup = document.createElement("div");
      popup.className = "map-popup";
      const tag = document.createElement("span");
      tag.className = "map-popup-type service";
      tag.textContent = service.category_label || meta.label;
      const heading = document.createElement("strong");
      heading.textContent = service.name;
      popup.append(tag, heading);
      popupRow(popup, service.address);
      popupRow(popup, service.phone);
      popupRow(popup, service.attribution, "map-popup-source");
      marker.bindPopup(popup, { minWidth: 220 });
      servicesLayer.addLayer(marker);
    });
  };

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
    if (!pointLayer) return;
    pointLayer.clearLayers();
    if (!layerVisible.reports) return;
    visibleReports.forEach((report) => {
      const meta = typeMeta[report.type] || typeMeta.help_request;
      L.circleMarker([report.location.latitude, report.location.longitude], {
        radius: report.priority === "critical" ? 10 : 8, weight: 3, color: "#ffffff",
        fillColor: meta.color, fillOpacity: 0.94, className: `operational-marker marker-${meta.className}`,
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
    if (!densityLayer) return;
    densityLayer.clearLayers();
    const groups = densityGroups(visibleReports);
    const maximum = Math.max(...groups.map((group) => group.reports.length), 1);
    groups.forEach((group) => {
      const count = group.reports.length;
      const intensity = count / maximum;
      const circle = L.circleMarker([group.latitude, group.longitude], {
        radius: 18 + Math.sqrt(count) * 8, weight: 2,
        color: intensity > 0.65 ? "#9f352f" : "#bc7622",
        fillColor: intensity > 0.65 ? "#d95c4f" : "#f0ad3c",
        fillOpacity: 0.3 + intensity * 0.35, className: "density-marker",
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
    const cards = incidents.slice(0, 14);
    cards.forEach((incident) => {
      const article = document.createElement("article");
      article.className = "map-result-card incident";
      const label = document.createElement("span");
      label.className = `map-result-type sev-${incident.severity}`;
      label.textContent = `${incident.category_label} · ${severityLabel(incident.severity)}`;
      const heading = document.createElement("h3");
      heading.textContent = incident.label;
      article.append(label, heading);
      popupRow(article, incident.address);
      resultList.append(article);
    });
    if (!cards.length) {
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
        article.append(label, heading);
        popupRow(article, report.location.label);
        resultList.append(article);
      });
    }
    if (!cards.length && !visibleReports.length) {
      const empty = document.createElement("p");
      empty.className = "map-empty-state";
      empty.textContent = "Aún no hay datos cargados para mostrar.";
      resultList.append(empty);
    }
  };

  const numberFmt = new Intl.NumberFormat("es-VE");
  const updateMetrics = () => {
    const host = document.querySelector("[data-situation-metrics]");
    if (!host) return;
    host.replaceChildren();
    if (!situation.length) {
      const empty = document.createElement("p");
      empty.className = "situation-loading";
      empty.textContent = "Aún no hay cifras de situación cargadas.";
      host.append(empty);
      return;
    }
    situation.forEach((metric) => {
      const cell = document.createElement("div");
      cell.className = `situation-cell metric-${metric.key}`;
      cell.setAttribute("role", "listitem");
      const value = document.createElement("strong");
      value.textContent = numberFmt.format(metric.value);
      const label = document.createElement("span");
      label.className = "situation-label";
      label.textContent = metric.label;
      const isLink = metric.attribution && /^https?:\/\//.test(metric.attribution);
      const source = document.createElement(isLink ? "a" : "span");
      source.className = "situation-source";
      if (isLink) { source.href = metric.attribution; source.target = "_blank"; source.rel = "noopener"; }
      const date = metric.as_of
        ? new Intl.DateTimeFormat("es-VE", { day: "2-digit", month: "short" }).format(new Date(metric.as_of))
        : "";
      source.textContent = [metric.source_name, date].filter(Boolean).join(" · ");
      if (metric.note) cell.title = metric.note;
      cell.append(value, label, source);
      if (metric.verification_status) {
        const status = document.createElement("span");
        status.className = "situation-status";
        status.textContent = metric.verification_status === "reported" ? "Reportada · en verificación" : metric.verification_status;
        cell.append(status);
      }
      host.append(cell);
    });
  };

  const allPoints = () => {
    const points = [];
    if (layerVisible.incidents) incidents.forEach((i) => points.push([i.latitude, i.longitude]));
    if (layerVisible.events) events.forEach((e) => points.push([e.latitude, e.longitude]));
    if (layerVisible.services) services.forEach((s) => points.push([s.latitude, s.longitude]));
    if (layerVisible.reports) filteredReports().forEach((r) => points.push([r.location.latitude, r.location.longitude]));
    return points;
  };

  const render = () => {
    const visibleReports = filteredReports();
    renderIncidents();
    renderEvents();
    renderServices();
    renderPoints(visibleReports);
    renderDensity(visibleReports);
    renderList(visibleReports);
    if (!map) {
      if (status) status.textContent = `${incidents.length} incidentes y ${services.length} servicios en el listado ligero.`;
      return;
    }
    if (activeMode === "density" && layerVisible.reports) {
      map.removeLayer(pointLayer);
      densityLayer.addTo(map);
    } else {
      map.removeLayer(densityLayer);
      pointLayer.addTo(map);
    }
    if (status) {
      status.textContent = `${incidents.length} incidentes · ${events.length} sismos · ${services.length} servicios.`;
    }
  };

  document.querySelectorAll("[data-map-layer]").forEach((button) => {
    button.addEventListener("click", () => {
      const layer = button.dataset.mapLayer;
      layerVisible[layer] = !layerVisible[layer];
      button.classList.toggle("is-active", layerVisible[layer]);
      button.setAttribute("aria-pressed", layerVisible[layer] ? "true" : "false");
      render();
    });
  });

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

  const fitToData = () => {
    if (!map) return;
    const points = allPoints();
    if (points.length) map.fitBounds(points, { padding: [48, 48], maxZoom: 12 });
  };

  const loadReports = async () => {
    try {
      const response = await fetch(element.dataset.mapEndpoint, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("map-data");
      const payload = await response.json();
      reports = payload.reports.filter((report) => report.location?.latitude != null && report.location?.longitude != null);
    } catch (_) { reports = []; }
  };

  const loadLive = async () => {
    if (!element.dataset.liveEndpoint) return;
    try {
      const response = await fetch(element.dataset.liveEndpoint, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("live-data");
      const payload = await response.json();
      situation = payload.situation || [];
      intensity = payload.intensity || [];
      const valid = (item) => item.latitude != null && item.longitude != null;
      incidents = (payload.incidents || []).filter(valid);
      events = (payload.events || []).filter(valid);
      services = (payload.services || []).filter(valid);
    } catch (_) { situation = []; intensity = []; incidents = []; events = []; services = []; }
  };

  await Promise.all([loadReports(), loadLive()]);
  updateMetrics();
  render();
  fitToData();
  if (status && !incidents.length && !events.length && !services.length && !reports.length) {
    status.textContent = "Aún no hay datos cargados. Ejecuta la ingesta de fuentes para ver el mapa vivo.";
  }
});
