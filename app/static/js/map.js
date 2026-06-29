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
    shelter: { label: "Refugio", color: "#caa12f" },
    water_point: { label: "Punto de agua", color: "#2a8fd6" },
    community_center: { label: "Centro comunitario", color: "#8a7de0" },
    fuel: { label: "Combustible", color: "#6b7785" },
    supplies: { label: "Víveres", color: "#c2603d" },
    other: { label: "Servicio", color: "#9aa6ad" },
  };
  // Glifos SVG (trazo, estilo Lucide/OCHA) para que el icono hable por sí solo.
  const serviceGlyphs = {
    hospital: "M5 12h14M12 5v14",
    clinic: "M5 12h14M12 5v14",
    pharmacy: "M5 12h14M12 5v14",
    shelter: "m3 10.5 9-7 9 7M5 9v12h14V9M10 21v-6h4v6",
    water_point: "M12 21a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5S12.5 4.5 12 2c-.5 2.5-2 4.9-4 6.5S5 12 5 14a7 7 0 0 0 7 7z",
    fire_station: "M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.4-.5-2-1-3-1-2-.2-4 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.2.4-2.3 1-3a2.5 2.5 0 0 0 2.5 2.5z",
    police: "M12 3l7 3v5c0 4.5-3 7-7 8.5C8 18 5 15.5 5 11V6z",
    community_center: "M4 21V8l8-5 8 5v13M4 21h16M9 21v-5h6v5",
    fuel: "M5 21V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v16M4 21h11M7 9h4M14 10h2a2 2 0 0 1 2 2v4a1.5 1.5 0 0 0 3 0V9l-3-3",
    supplies: "M4 8h16l-1.5 11H5.5zM4 8l3-5h10l3 5M9 12v3m6-3v3",
    other: "M12 21s-7-6-7-11a7 7 0 0 1 14 0c0 5-7 11-7 11zM12 12a2 2 0 1 0 0-4 2 2 0 0 0 0 4z",
  };
  const serviceIcon = (meta, category) =>
    L.divIcon({
      className: "svc-pin",
      html: `<i style="--c:${meta.color}"><svg viewBox="0 0 24 24" fill="none" stroke="#fff" `
        + `stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round">`
        + `<path d="${serviceGlyphs[category] || serviceGlyphs.other}"/></svg></i>`,
      iconSize: [30, 30],
      iconAnchor: [15, 15],
      popupAnchor: [0, -15],
    });

  // --- Zonas de peligro (CRÍTICO: edificios colapsados / atrapados / incendio / vía
  // bloqueada). Marcador de advertencia + círculo de área a EVITAR, visible en todo zoom.
  const DANGER_CATEGORIES = new Set([
    "collapsed_structure", "trapped_persons", "buried_persons", "fire", "blocked_road",
  ]);
  const DAMAGE_CANDIDATE_CATEGORIES = new Set([
    "destroyed_structure_candidate", "major_damage_candidate", "minor_damage_candidate",
  ]);
  const dangerColor = (sev) =>
    ({ critical: "#e5253a", high: "#ef5f2e", medium: "#f0a23a", low: "#f0c93a" }[sev] || "#ef5f2e");
  const dangerRadiusM = (sev) =>
    ({ critical: 250, high: 150, medium: 90, low: 60 }[sev] || 120);
  const dangerIcon = (sev) =>
    L.divIcon({
      className: `danger-pin sev-${sev}`,
      html: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 22.5 21H1.5Z" `
        + `fill="${dangerColor(sev)}" stroke="#fff" stroke-width="1.3" stroke-linejoin="round"/>`
        + `<rect x="11" y="9" width="2" height="6" rx="1" fill="#fff"/>`
        + `<circle cx="12" cy="17.6" r="1.25" fill="#fff"/></svg>`,
      iconSize: [34, 34],
      iconAnchor: [17, 27],
      popupAnchor: [0, -24],
    });
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
  let dangerLayer = null;
  let assessmentLayer = null;
  let userLayer = null;
  let applyIncidentLayers = () => {};
  if (mapAvailable) {
    // Encuadre inicial en la ZONA AFECTADA (La Guaira / Caracas), no todo el país,
    // para que el mapa se vea concentrado donde están los daños.
    map = L.map(element, { scrollWheelZoom: false, zoomControl: false, preferCanvas: true })
      .setView([10.58, -66.93], 11);
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

    // Clustering más agresivo: agrupa los puntos en burbujas por zona en vez de
    // dispersarlos. Así se ve "concentrado en zonas afectadas", no un reguero de pines.
    const clusterGroup = () => (typeof L.markerClusterGroup === "function"
      ? L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 80, spiderfyOnMaxZoom: true, chunkedLoading: true })
      : L.layerGroup());

    // Mapa de calor (KDE) para el zoom-out: muchos kernels gaussianos que se suman
    // en un campo continuo y se colorean por densidad (verde→rojo).
    incidentsHeat = (typeof L.heatLayer === "function")
      ? L.heatLayer([], { radius: 34, blur: 24, maxZoom: 9, max: 8, minOpacity: 0.42,
          gradient: { 0.2: "#37d06f", 0.4: "#f0d836", 0.6: "#f4a23a", 0.8: "#ef5f2e", 1: "#e5253a" } }).addTo(map)
      : null;
    eventsLayer = L.layerGroup().addTo(map);
    servicesLayer = clusterGroup().addTo(map);
    incidentsCluster = clusterGroup();
    dangerLayer = L.layerGroup().addTo(map);
    assessmentLayer = clusterGroup().addTo(map);
    userLayer = L.layerGroup().addTo(map);    // "tú estás aquí" + radio de búsqueda
    pointLayer = L.layerGroup().addTo(map);
    densityLayer = L.layerGroup();

    // Transición por zoom (lo que pediste): a zoom bajo manda el CALOR; al acercar
    // (>= umbral) el calor desaparece y aparecen los clusters/puntos separados, sin estorbar.
    const HEAT_MAX_ZOOM = 11;
    applyIncidentLayers = () => {
      if (!map) return;
      const zoomedIn = map.getZoom() >= HEAT_MAX_ZOOM;
      const showHeat = layerVisible.assessments && !zoomedIn;
      const showCluster = layerVisible.incidents && zoomedIn;
      if (incidentsHeat && showHeat && !map.hasLayer(incidentsHeat)) {
        incidentsHeat.addTo(map);
      } else if (incidentsHeat && !showHeat && map.hasLayer(incidentsHeat)) {
        // leaflet.heat 0.2.0 no cancela su requestAnimationFrame al salir del
        // mapa. Si el zoom cambia durante ese frame, intenta pintar sin _map.
        if (incidentsHeat._frame) {
          L.Util.cancelAnimFrame(incidentsHeat._frame);
          incidentsHeat._frame = null;
        }
        map.removeLayer(incidentsHeat);
      }
      if (incidentsCluster && showCluster && !map.hasLayer(incidentsCluster)) {
        incidentsCluster.addTo(map);
      } else if (incidentsCluster && !showCluster && map.hasLayer(incidentsCluster)) {
        map.removeLayer(incidentsCluster);
      }
      // Zonas de peligro: visibles en TODO nivel de zoom mientras la capa esté activa.
      if (dangerLayer) {
        if (layerVisible.danger && !map.hasLayer(dangerLayer)) dangerLayer.addTo(map);
        else if (!layerVisible.danger && map.hasLayer(dangerLayer)) map.removeLayer(dangerLayer);
      }
      if (assessmentLayer) {
        if (layerVisible.assessments && !map.hasLayer(assessmentLayer)) assessmentLayer.addTo(map);
        else if (!layerVisible.assessments && map.hasLayer(assessmentLayer)) map.removeLayer(assessmentLayer);
      }
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
  const layerVisible = {
    danger: true, assessments: true, incidents: true,
    events: false, services: true, reports: true,
  };
  const filteredReports = () => reports.filter((report) => activeFilter === "all" || report.type === activeFilter);

  // --- GPS del usuario + radio de búsqueda configurable ---------------------
  let userLocation = null;
  let activeRadius = 0; // km; 0 = todo
  const haversineKm = (aLat, aLng, bLat, bLng) => {
    const toRad = (d) => (d * Math.PI) / 180;
    const dLat = toRad(bLat - aLat);
    const dLng = toRad(bLng - aLng);
    const x = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(aLat)) * Math.cos(toRad(bLat)) * Math.sin(dLng / 2) ** 2;
    return 6371 * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
  };
  const fmtDist = (km) => (km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`);
  const servicesInRange = () =>
    userLocation && activeRadius
      ? services.filter((s) => haversineKm(userLocation.lat, userLocation.lng, s.latitude, s.longitude) <= activeRadius)
      : services;
  const drawUserLayer = () => {
    if (!userLayer) return;
    userLayer.clearLayers();
    if (!userLocation) return;
    L.marker([userLocation.lat, userLocation.lng], {
      icon: L.divIcon({ className: "user-pin", html: "<span></span>", iconSize: [22, 22], iconAnchor: [11, 11] }),
      zIndexOffset: 1200,
    }).bindPopup("Tu ubicación").addTo(userLayer);
    if (activeRadius) {
      L.circle([userLocation.lat, userLocation.lng], {
        radius: activeRadius * 1000, color: "#2a8fd6", weight: 1.4,
        fillColor: "#2a8fd6", fillOpacity: 0.06, dashArray: "6 6", interactive: false,
      }).addTo(userLayer);
    }
  };
  const locateUser = (btn) => {
    if (!navigator.geolocation) {
      if (status) status.textContent = "Tu navegador no permite geolocalización.";
      return;
    }
    if (status) status.textContent = "Obteniendo tu ubicación…";
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        userLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        if (btn) { btn.classList.add("is-active"); btn.setAttribute("aria-pressed", "true"); }
        if (map) map.setView([userLocation.lat, userLocation.lng], Math.max(map.getZoom(), 12));
        drawUserLayer();
        render();
      },
      () => { if (status) status.textContent = "No pudimos obtener tu ubicación (permiso denegado o sin señal)."; },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  };

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
    if (incident.is_damage_candidate) {
      popupRow(
        popup,
        "Evaluación satelital: requiere validación en terreno.",
        "map-popup-assessment"
      );
    } else if (incident.is_verified_danger && DANGER_CATEGORIES.has(incident.category)) {
      popupRow(popup, "Zona de riesgo documentada — evita ingresar.", "map-popup-danger");
    }
    popupRow(popup, incident.address);
    popupRow(popup, incident.situation_note);
    if (incident.people_trapped_status === "confirmed") {
      const count = incident.people_trapped_count;
      popupRow(
        popup,
        count ? `Personas atrapadas confirmadas: ${count}` : "Personas atrapadas: confirmación activa",
        "map-popup-people"
      );
    } else if (incident.category === "collapsed_structure") {
      popupRow(popup, "Personas atrapadas: sin confirmación individual.", "map-popup-source");
    }
    if (incident.verification_label) {
      popupRow(popup, incident.verification_label, "map-popup-verification");
    }
    if (incident.confidence != null) {
      popupRow(
        popup,
        `Confianza del modelo: ${Math.round(incident.confidence * 100)}%`,
        "map-popup-source"
      );
    }
    if (incident.maps_url) {
      const link = document.createElement("a");
      link.className = "map-popup-maps";
      link.href = incident.maps_url; link.target = "_blank"; link.rel = "noopener noreferrer";
      link.textContent = "Abrir ubicación";
      popup.appendChild(link);
    }
    if (incident.source_url) {
      const source = document.createElement("a");
      source.className = "map-popup-source-link";
      source.href = incident.source_url;
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      source.textContent = incident.source_name ? `Fuente: ${incident.source_name}` : "Consultar fuente";
      popup.append(source);
    } else {
      popupRow(popup, incident.source_name || incident.attribution, "map-popup-source");
    }
    if (incident.source_date) {
      const date = new Intl.DateTimeFormat("es-VE", {
        day: "2-digit", month: "short", year: "numeric",
      }).format(new Date(incident.source_date));
      popupRow(popup, `Información publicada: ${date}`, "map-popup-source");
    }
    return popup;
  };
  const renderIncidents = () => {
    if (incidentsCluster) incidentsCluster.clearLayers();
    if (dangerLayer) dangerLayer.clearLayers();
    if (assessmentLayer) assessmentLayer.clearLayers();
    incidents.forEach((incident) => {
      const isDanger = incident.is_verified_danger && DANGER_CATEGORIES.has(incident.category);
      if (DAMAGE_CANDIDATE_CATEGORIES.has(incident.category) && assessmentLayer) {
        const marker = L.circleMarker([incident.latitude, incident.longitude], {
          radius: incident.category === "destroyed_structure_candidate" ? 8 : 6,
          weight: 2,
          color: incident.category === "destroyed_structure_candidate" ? "#ef6a60" : "#e0a02a",
          fillColor: incident.category === "minor_damage_candidate" ? "#f0c93a" : "#ef7d2e",
          fillOpacity: 0.72,
          className: "assessment-marker",
        });
        marker.bindPopup(incidentPopup(incident), { minWidth: 270 });
        assessmentLayer.addLayer(marker);
      } else if (isDanger && dangerLayer) {
        // Solo evidencia corroborada o verificada llega a esta capa pública.
        L.circle([incident.latitude, incident.longitude], {
          radius: incident.area_radius_m || dangerRadiusM(incident.severity),
          color: dangerColor(incident.severity),
          weight: 1.2, fillColor: dangerColor(incident.severity), fillOpacity: 0.14,
          dashArray: "5 4", interactive: false,
        }).addTo(dangerLayer);
        const marker = L.marker([incident.latitude, incident.longitude], {
          icon: dangerIcon(incident.severity), zIndexOffset: 1000,
        });
        marker.bindPopup(incidentPopup(incident), { minWidth: 248 });
        dangerLayer.addLayer(marker);
      } else if (incidentsCluster) {
        // Incidentes no peligrosos: cluster normal (aparecen al acercar).
        const marker = L.marker([incident.latitude, incident.longitude], {
          icon: dotIcon("incident", severityColor(incident.severity), incident.severity),
        });
        marker.bindPopup(incidentPopup(incident), { minWidth: 248 });
        incidentsCluster.addLayer(marker);
      }
    });
    // El mapa de calor usa la capa de intensidad de zonas afectadas (no los incidentes).
    if (incidentsHeat) {
      // Leaflet.heat no permite setLatLngs() mientras la capa está fuera del mapa:
      // intenta redibujar con this._map=null. Conservamos los datos para que onAdd
      // los pinte al volver a una escala de calor.
      if (map?.hasLayer(incidentsHeat)) incidentsHeat.setLatLngs(intensity);
      else incidentsHeat._latlngs = intensity;
    }
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
    servicesInRange().forEach((service) => {
      const meta = serviceMeta[service.category] || serviceMeta.other;
      const marker = L.marker([service.latitude, service.longitude], {
        icon: serviceIcon(meta, service.category),
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
      if (userLocation) {
        const dist = haversineKm(userLocation.lat, userLocation.lng, service.latitude, service.longitude);
        popupRow(popup, `A ${fmtDist(dist)} de ti`, "map-popup-dist");
      }
      if (service.maps_url) {
        const link = document.createElement("a");
        link.className = "map-popup-maps";
        link.href = service.maps_url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "Cómo llegar (Google Maps)";
        popup.appendChild(link);
      }
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

  // Vuela al punto exacto y abre su ficha (independiente del clustering).
  const focusOnPoint = (lat, lng, popupContent) => {
    if (!map || lat == null || lng == null) return;
    map.flyTo([lat, lng], 16, { duration: 0.7 });
    L.popup({ minWidth: 248, autoPan: true })
      .setLatLng([lat, lng])
      .setContent(popupContent)
      .openOn(map);
  };

  const listActions = (article, focusFn, externalUrl, externalLabel) => {
    const actions = document.createElement("div");
    actions.className = "map-result-actions";
    const focusBtn = document.createElement("button");
    focusBtn.type = "button";
    focusBtn.className = "map-result-action focus";
    focusBtn.textContent = "Ver en el mapa";
    focusBtn.addEventListener("click", (event) => { event.stopPropagation(); focusFn(); });
    actions.append(focusBtn);
    if (externalUrl) {
      const link = document.createElement("a");
      link.className = "map-result-action gmaps";
      link.href = externalUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = externalLabel;
      link.addEventListener("click", (event) => event.stopPropagation());
      actions.append(link);
    }
    article.append(actions);
  };

  const renderList = (visibleReports) => {
    if (!resultList) return;
    resultList.replaceChildren();
    const cards = incidents.slice(0, 16);
    cards.forEach((incident) => {
      const article = document.createElement("article");
      article.className = "map-result-card incident is-clickable";
      article.tabIndex = 0;
      article.setAttribute("role", "button");
      article.setAttribute("aria-label", `Ver ${incident.label} en el mapa`);
      const label = document.createElement("span");
      label.className = `map-result-type sev-${incident.severity}`;
      label.textContent = incident.is_damage_candidate
        ? `${incident.category_label} · por validar`
        : `${incident.category_label} · ${severityLabel(incident.severity)}`;
      const heading = document.createElement("h3");
      heading.textContent = incident.label;
      article.append(label, heading);
      if (incident.address) popupRow(article, incident.address);
      // Una sola línea de estado, sin repetir.
      const statusLine = incident.is_damage_candidate
        ? (incident.confidence != null
            ? `Daño satelital · confianza ${Math.round(incident.confidence * 100)}%`
            : "Daño satelital por validar")
        : (incident.verification_label || incident.source_name || "");
      if (statusLine) popupRow(article, statusLine, "map-result-source");
      const focus = () => focusOnPoint(incident.latitude, incident.longitude, incidentPopup(incident));
      listActions(article, focus, incident.maps_url, "Google Maps");
      article.addEventListener("click", focus);
      article.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") { event.preventDefault(); focus(); }
      });
      resultList.append(article);
    });
    if (!cards.length) {
      visibleReports.slice(0, 12).forEach((report) => {
        const meta = typeMeta[report.type] || typeMeta.help_request;
        const article = document.createElement("article");
        article.className = "map-result-card is-clickable";
        article.tabIndex = 0;
        article.setAttribute("role", "button");
        const label = document.createElement("span");
        label.className = `map-result-type ${meta.className}`;
        label.textContent = meta.label;
        const heading = document.createElement("h3");
        heading.textContent = report.title;
        article.append(label, heading);
        popupRow(article, report.location.label);
        const focus = () => focusOnPoint(report.location.latitude, report.location.longitude, popupFor(report));
        listActions(article, focus, report.url, "Ver detalle");
        article.addEventListener("click", focus);
        article.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") { event.preventDefault(); focus(); }
        });
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
    const structuralPoints = [];
    incidents.forEach((incident) => {
      const visible = incident.is_damage_candidate
        ? layerVisible.assessments
        : (incident.is_verified_danger && DANGER_CATEGORIES.has(incident.category)
          ? layerVisible.danger
          : layerVisible.incidents);
      if (visible) structuralPoints.push([incident.latitude, incident.longitude]);
    });
    // La prioridad visual son víctimas y daño. Los miles de servicios no deben
    // alejar el encuadre hasta mostrar todo el país cuando ya hay evidencia estructural.
    if (structuralPoints.length) return structuralPoints;
    const points = [];
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
      const candidates = incidents.filter((incident) => incident.is_damage_candidate).length;
      const documented = incidents.length - candidates;
      status.textContent = `${documented} incidentes documentados · ${candidates} evaluaciones por validar · ${services.length} servicios.`;
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

  document.querySelectorAll("[data-map-locate]").forEach((button) => {
    button.addEventListener("click", () => locateUser(button));
  });
  document.querySelectorAll("[data-map-radius]").forEach((button) => {
    button.addEventListener("click", () => {
      activeRadius = Number(button.dataset.mapRadius) || 0;
      document.querySelectorAll("[data-map-radius]").forEach((candidate) => {
        const active = candidate === button;
        candidate.classList.toggle("is-active", active);
        candidate.setAttribute("aria-pressed", active ? "true" : "false");
      });
      if (!userLocation && activeRadius) {
        locateUser(document.querySelector("[data-map-locate]"));
        return;
      }
      drawUserLayer();
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
