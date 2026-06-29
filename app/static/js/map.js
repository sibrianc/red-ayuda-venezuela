// Centro de Operaciones — mapa de comando del terremoto.
// Diseño tipo sala de mando (oscuro, táctico) cableado a DATOS REALES:
//   /mapa/live  -> { situation, intensity, incidents, events, services }
//   /mapa/data  -> { reports }  (reportes ciudadanos revisados)
// Reglas que pidió el propietario:
//   - El radio CONCENTRA de verdad: lo que queda fuera NO se dibuja.
//   - El mapa de calor es consistente: se alimenta del campo de intensidad real
//     (zonas afectadas), no de blobs dispersos.
window.addEventListener("DOMContentLoaded", async () => {
  "use strict";
  const root = document.getElementById("cmd-map");
  if (!root) return;

  const fallback = document.getElementById("cmd-fallback");
  const lowBandwidth = document.documentElement.dataset.bandwidth === "low";
  // El modo ligero evita descargar teselas: dejamos el camino accesible
  // (listado + directorio) en lugar del mapa visual.
  if (lowBandwidth || typeof L === "undefined") {
    if (fallback) fallback.hidden = false;
    return;
  }

  const ACCENT = "#2de1d6";
  const TYPE = {
    zona:    { code: "Z", color: "#ff3b3b", label: "Zona afectada" },
    auxilio: { code: "A", color: "#ffb02e", label: "Solicitud de auxilio" },
    recurso: { code: "R", color: "#3ddc84", label: "Recurso disponible" },
    persona: { code: "P", color: "#c77dff", label: "Persona sin contacto" },
  };
  const PRI = {
    critical: { label: "CRÍTICA", color: "#ff3b3b" },
    high:     { label: "ALTA",    color: "#ffb02e" },
    medium:   { label: "MEDIA",   color: "#2de1d6" },
    low:      { label: "BAJA",    color: "#3ddc84" },
  };
  const REPORT_KIND = {
    help_request: "auxilio", resource_offer: "recurso",
    location_report: "zona", missing_person: "persona",
  };

  // ---------------- estado ----------------
  let items = [];
  let heatPoints = [];
  let epicenter = { lat: 10.6017, lng: -66.9331 }; // La Guaira (zona afectada) por defecto
  let magnitude = null;
  let radiusKm = 15;
  let selectedId = null;
  const layers = { heat: true, rings: true, zona: true, auxilio: true, recurso: true, persona: true };

  // ---------------- geo helpers ----------------
  const haversine = (aLat, aLng, bLat, bLng) => {
    const R = 6371, d = Math.PI / 180;
    const dLa = (bLat - aLat) * d, dLo = (bLng - aLng) * d;
    const a = Math.sin(dLa / 2) ** 2 + Math.cos(aLat * d) * Math.cos(bLat * d) * Math.sin(dLo / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(a));
  };
  const destination = (c, brng, km) => {
    const R = 6371, d = Math.PI / 180, r = 180 / Math.PI, dr = km / R, b = brng * d;
    const la1 = c.lat * d, lo1 = c.lng * d;
    const la2 = Math.asin(Math.sin(la1) * Math.cos(dr) + Math.cos(la1) * Math.sin(dr) * Math.cos(b));
    const lo2 = lo1 + Math.atan2(Math.sin(b) * Math.sin(dr) * Math.cos(la1), Math.cos(dr) - Math.sin(la1) * Math.sin(la2));
    return [la2 * r, lo2 * r];
  };
  const fmtDist = (km) => (km < 1 ? `${Math.round(km * 1000)} m` : `${km.toFixed(1)} km`);

  // ---------------- mapa ----------------
  const map = L.map(root, {
    zoomControl: false, attributionControl: true, scrollWheelZoom: true, preferCanvas: true,
    center: [epicenter.lat, epicenter.lng], zoom: 12, minZoom: 7, maxZoom: 18,
  });
  const cartoUrl = (theme) => theme === "light"
    ? "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
    : "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
  let baseLayer = null;
  const setBasemap = () => {
    const theme = document.documentElement.dataset.theme === "light" ? "light" : "dark";
    if (baseLayer) map.removeLayer(baseLayer);
    baseLayer = L.tileLayer(cartoUrl(theme), {
      subdomains: "abcd", maxZoom: 19, detectRetina: true,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · © <a href="https://carto.com/attributions">CARTO</a>',
    }).addTo(map);
    baseLayer.bringToBack();
  };
  setBasemap();
  window.addEventListener("rav:themechange", setBasemap);

  // ---------------- mapa de calor métrico (anclado a metros, consistente) -------
  let lut = null;
  const buildLut = () => {
    const cv = document.createElement("canvas");
    cv.width = 256; cv.height = 1;
    const g = cv.getContext("2d");
    const grad = g.createLinearGradient(0, 0, 256, 0);
    grad.addColorStop(0.00, "rgba(10,40,70,0)");
    grad.addColorStop(0.16, "rgba(20,90,120,0.32)");
    grad.addColorStop(0.36, "rgba(31,143,176,0.58)");
    grad.addColorStop(0.54, "rgba(45,225,214,0.72)");
    grad.addColorStop(0.70, "rgba(255,210,63,0.82)");
    grad.addColorStop(0.85, "rgba(255,122,26,0.9)");
    grad.addColorStop(1.00, "rgba(255,45,45,0.96)");
    g.fillStyle = grad; g.fillRect(0, 0, 256, 1);
    lut = g.getImageData(0, 0, 256, 1).data;
  };
  buildLut();
  const metersPerPixel = () => {
    const c = map.getCenter();
    const p1 = map.latLngToContainerPoint(c);
    const c2 = L.latLng(c.lat, c.lng + 0.05);
    const p2 = map.latLngToContainerPoint(c2);
    return map.distance(c, c2) / p1.distanceTo(p2);
  };
  const drawHeat = (cv) => {
    const ctx = cv.getContext("2d");
    ctx.clearRect(0, 0, cv.width, cv.height);
    if (!heatPoints.length) return;
    const mpp = metersPerPixel();
    for (const h of heatPoints) {
      const cp = map.latLngToContainerPoint([h.lat, h.lng]);
      if (cp.x < -300 || cp.y < -300 || cp.x > cv.width + 300 || cp.y > cv.height + 300) continue;
      const w = Math.max(0.15, Math.min(1, h.weight || 0.5));
      const rad = Math.max(10, (700 + w * 1100) / mpp);
      const g = ctx.createRadialGradient(cp.x, cp.y, 0, cp.x, cp.y, rad);
      g.addColorStop(0, `rgba(0,0,0,${0.12 * w})`);
      g.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(cp.x, cp.y, rad, 0, 6.2832); ctx.fill();
    }
    const img = ctx.getImageData(0, 0, cv.width, cv.height);
    const dd = img.data;
    for (let i = 0; i < dd.length; i += 4) {
      let al = dd[i + 3];
      if (al === 0) continue;
      if (al > 255) al = 255;
      const o = al * 4;
      dd[i] = lut[o]; dd[i + 1] = lut[o + 1]; dd[i + 2] = lut[o + 2]; dd[i + 3] = lut[o + 3];
    }
    ctx.putImageData(img, 0, 0);
  };
  const HeatLayer = L.Layer.extend({
    onAdd(m) {
      this._m = m;
      const cv = this._cv = L.DomUtil.create("canvas", "mapc-heat");
      cv.style.position = "absolute";
      cv.style.pointerEvents = "none";
      cv.style.mixBlendMode = "screen";
      m.getPanes().overlayPane.appendChild(cv);
      m.on("moveend zoomend resize", this._reset, this);
      this._reset();
    },
    onRemove(m) { L.DomUtil.remove(this._cv); m.off("moveend zoomend resize", this._reset, this); },
    redraw() { if (this._cv) drawHeat(this._cv); },
    _reset() {
      const m = this._m, size = m.getSize();
      const tl = m.containerPointToLayerPoint([0, 0]);
      L.DomUtil.setPosition(this._cv, tl);
      this._cv.width = size.x; this._cv.height = size.y;
      drawHeat(this._cv);
    },
  });
  const heatLayer = new HeatLayer();

  // ---------------- anillos radar ----------------
  const ringsGroup = L.layerGroup();
  const populateRings = () => {
    ringsGroup.clearLayers();
    [5, 10, 15, 20, 30].forEach((km) => {
      L.circle([epicenter.lat, epicenter.lng], {
        radius: km * 1000, color: ACCENT, weight: 1, opacity: 0.18, fill: false,
        dashArray: "2 7", interactive: false,
      }).addTo(ringsGroup);
      const lp = destination(epicenter, 0, km);
      L.marker(lp, {
        icon: L.divIcon({
          className: "",
          html: `<div style="color:${ACCENT};font-family:'IBM Plex Mono',monospace;font-size:9px;opacity:.55;white-space:nowrap;transform:translateY(-50%);background:rgba(5,8,11,.6);padding:0 3px;letter-spacing:.06em;">${km} KM</div>`,
          iconSize: [0, 0],
        }), interactive: false, keyboard: false,
      }).addTo(ringsGroup);
    });
    [0, 90, 180, 270].forEach((b) => {
      const end = destination(epicenter, b, 30);
      L.polyline([[epicenter.lat, epicenter.lng], end], { color: ACCENT, weight: 1, opacity: 0.08, interactive: false }).addTo(ringsGroup);
    });
  };

  // ---------------- radio + epicentro ----------------
  const radiusCircle = L.circle([epicenter.lat, epicenter.lng], {
    radius: radiusKm * 1000, color: ACCENT, weight: 1.5, opacity: 0.9,
    fillColor: ACCENT, fillOpacity: 0.05, interactive: false,
  }).addTo(map);
  const epiIcon = L.divIcon({
    className: "mapc-epi", html: "<div><i></i><i></i><b></b></div>", iconSize: [42, 42], iconAnchor: [21, 21],
  });
  const epiMarker = L.marker([epicenter.lat, epicenter.lng], { icon: epiIcon, draggable: true, zIndexOffset: 1200, keyboard: false }).addTo(map);
  epiMarker.on("drag", () => {
    const ll = epiMarker.getLatLng();
    epicenter = { lat: ll.lat, lng: ll.lng };
    radiusCircle.setLatLng(ll);
    populateRings();
    recompute();
  });

  // ---------------- marcadores ----------------
  const markersGroup = L.layerGroup().addTo(map);
  const makeIcon = (it) => {
    const t = TYPE[it.kind];
    return L.divIcon({
      className: "mapc-mk",
      html: `<span style="--c:${t.color}">${t.code}</span>`,
      iconSize: [24, 24], iconAnchor: [12, 12], popupAnchor: [0, -12],
    });
  };
  const popupFor = (it) => {
    const t = TYPE[it.kind];
    const pop = document.createElement("div");
    const tag = document.createElement("span");
    tag.className = "mapc-pop-tag";
    tag.style.setProperty("--c", t.color);
    tag.textContent = `${t.label}${it.priorityLabel ? " · " + it.priorityLabel : ""}`;
    const h = document.createElement("strong");
    h.textContent = it.title;
    pop.append(tag, h);
    if (it.meta) { const p = document.createElement("p"); p.style.margin = "4px 0 0"; p.style.color = "#9fc0c2"; p.textContent = it.meta; pop.append(p); }
    const actions = document.createElement("div");
    if (it.mapsUrl) {
      const a = document.createElement("a"); a.className = "mapc-pop-a"; a.href = it.mapsUrl; a.target = "_blank"; a.rel = "noopener noreferrer"; a.textContent = "Cómo llegar"; actions.append(a);
    }
    if (it.detailUrl) {
      const a = document.createElement("a"); a.className = "mapc-pop-a"; a.href = it.detailUrl; a.textContent = "Ver detalle"; actions.append(a);
    }
    if (actions.childNodes.length) pop.append(actions);
    return pop;
  };
  const inRadius = () => items.filter((it) => it.dist <= radiusKm && layers[it.kind]);
  const renderMarkers = () => {
    markersGroup.clearLayers();
    inRadius().forEach((it) => {
      const m = L.marker([it.lat, it.lng], { icon: makeIcon(it), keyboard: false });
      m.bindPopup(popupFor(it), { minWidth: 220 });
      m.on("click", () => { selectedId = it.id; renderIntel(); });
      markersGroup.addLayer(m);
    });
  };

  // ---------------- panel INTEL ----------------
  const intelList = document.getElementById("cmd-intel-list");
  const intelCount = document.getElementById("cmd-intel-count");
  const focus = (it) => {
    selectedId = it.id;
    map.flyTo([it.lat, it.lng], Math.max(map.getZoom(), 15), { duration: 0.6 });
    L.popup({ minWidth: 220, autoPan: true }).setLatLng([it.lat, it.lng]).setContent(popupFor(it)).openOn(map);
    renderIntel();
  };
  const renderIntel = () => {
    if (!intelList) return;
    const near = inRadius().slice().sort((a, b) => a.dist - b.dist).slice(0, 80);
    if (intelCount) intelCount.textContent = String(inRadius().length);
    intelList.replaceChildren();
    if (!near.length) {
      const p = document.createElement("p"); p.className = "mapc-intel-empty";
      p.textContent = "Sin elementos dentro del radio. Amplía el radio o arrastra el epicentro.";
      intelList.append(p); return;
    }
    near.forEach((it) => {
      const t = TYPE[it.kind];
      const card = document.createElement("button");
      card.type = "button";
      card.className = "mapc-card" + (it.id === selectedId ? " is-sel" : "");
      card.setAttribute("role", "listitem");
      const code = document.createElement("span");
      code.className = "mapc-card-code"; code.style.setProperty("--c", t.color); code.textContent = t.code;
      const body = document.createElement("span"); body.className = "mapc-card-body";
      const title = document.createElement("span"); title.className = "mapc-card-title"; title.textContent = it.title;
      const meta = document.createElement("span"); meta.className = "mapc-card-meta";
      meta.style.color = it.priorityColor || "#7fb6b3";
      meta.textContent = `${it.priorityLabel || ""}${it.priorityLabel ? " · " : ""}${t.label}`;
      body.append(title, meta);
      const dist = document.createElement("span"); dist.className = "mapc-card-dist"; dist.textContent = fmtDist(it.dist);
      card.append(code, body, dist);
      card.addEventListener("click", () => focus(it));
      intelList.append(card);
    });
  };

  // ---------------- recompute (distancias + filtro por radio) ----------------
  const insideEl = document.getElementById("cmd-inside");
  const totalEl = document.getElementById("cmd-total");
  const recompute = () => {
    let inside = 0;
    for (const it of items) {
      it.dist = haversine(epicenter.lat, epicenter.lng, it.lat, it.lng);
      if (it.dist <= radiusKm && layers[it.kind]) inside++;
    }
    if (insideEl) insideEl.textContent = String(inside);
    if (totalEl) totalEl.textContent = String(items.length);
    renderMarkers();
    renderIntel();
  };

  // ---------------- capas ----------------
  const applyStaticLayers = () => {
    if (layers.heat && !map.hasLayer(heatLayer)) heatLayer.addTo(map);
    else if (!layers.heat && map.hasLayer(heatLayer)) map.removeLayer(heatLayer);
    if (layers.rings && !map.hasLayer(ringsGroup)) ringsGroup.addTo(map);
    else if (!layers.rings && map.hasLayer(ringsGroup)) map.removeLayer(ringsGroup);
  };

  // ---------------- normalización de datos reales ----------------
  const priorityOf = (sev) => PRI[sev] ? sev : "medium";
  const normalize = (live, reports) => {
    const out = [];
    (live.incidents || []).forEach((i) => {
      if (i.latitude == null || i.longitude == null) return;
      const sev = priorityOf(i.severity);
      out.push({
        id: "inc-" + i.public_id, kind: "zona", lat: i.latitude, lng: i.longitude,
        title: i.label || i.category_label || "Zona afectada", meta: i.category_label,
        priorityLabel: PRI[sev].label, priorityColor: PRI[sev].color, mapsUrl: i.maps_url,
      });
    });
    (live.services || []).forEach((s) => {
      if (s.latitude == null || s.longitude == null) return;
      const sev = s.emergency ? "high" : "low";
      out.push({
        id: "svc-" + s.public_id, kind: "recurso", lat: s.latitude, lng: s.longitude,
        title: s.name || s.category_label || "Servicio", meta: s.category_label,
        priorityLabel: PRI[sev].label, priorityColor: PRI[sev].color, mapsUrl: s.maps_url,
      });
    });
    (reports || []).forEach((r) => {
      const loc = r.location || {};
      if (loc.latitude == null || loc.longitude == null) return;
      const kind = REPORT_KIND[r.type] || "auxilio";
      const sev = priorityOf(r.priority);
      out.push({
        id: "rep-" + (r.id || r.public_id || Math.random().toString(36).slice(2)),
        kind, lat: loc.latitude, lng: loc.longitude,
        title: r.title || TYPE[kind].label, meta: loc.label,
        priorityLabel: PRI[sev].label, priorityColor: PRI[sev].color, detailUrl: r.url,
      });
    });
    return out;
  };
  const computeEpicenter = (live) => {
    const pts = live.intensity || [];
    if (pts.length) {
      let sLat = 0, sLng = 0, sW = 0;
      pts.forEach((p) => { const w = (p[2] || 0.5); sLat += p[0] * w; sLng += p[1] * w; sW += w; });
      if (sW > 0) return { lat: sLat / sW, lng: sLng / sW };
    }
    const evs = (live.events || []).filter((e) => e.latitude != null && e.magnitude != null);
    if (evs.length) { const top = evs.reduce((a, b) => (b.magnitude > a.magnitude ? b : a)); return { lat: top.latitude, lng: top.longitude }; }
    return epicenter;
  };

  const loadData = async () => {
    let live = { incidents: [], services: [], events: [], intensity: [], situation: [] };
    let reports = [];
    try {
      const r = await fetch(root.dataset.liveEndpoint, { headers: { Accept: "application/json" } });
      if (r.ok) live = await r.json();
    } catch (_) { /* sin datos */ }
    try {
      const r = await fetch(root.dataset.dataEndpoint, { headers: { Accept: "application/json" } });
      if (r.ok) reports = (await r.json()).reports || [];
    } catch (_) { /* sin reportes */ }

    heatPoints = (live.intensity || []).map((p) => ({ lat: p[0], lng: p[1], weight: p[2] }));
    epicenter = computeEpicenter(live);
    const evs = (live.events || []).filter((e) => e.magnitude != null);
    magnitude = evs.length ? Math.max(...evs.map((e) => e.magnitude)) : null;
    items = normalize(live, reports);
  };

  // ---------------- cabecera (reloj, zoom, cursor, magnitud) -------------------
  const elClock = document.getElementById("cmd-clock");
  const elZoom = document.getElementById("cmd-zoom");
  const elCursor = document.getElementById("cmd-cursor");
  const elMag = document.getElementById("cmd-mag");
  const elEpi = document.getElementById("cmd-epi");
  const elScaleBar = document.getElementById("cmd-scale-bar");
  const elScaleText = document.getElementById("cmd-scale-text");
  const pad = (n) => String(n).padStart(2, "0");
  const tick = () => { const d = new Date(); if (elClock) elClock.textContent = `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`; };
  tick(); setInterval(tick, 1000);
  const updateScale = () => {
    const mpp = metersPerPixel();
    const nice = [50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000];
    let chosen = nice[0];
    nice.forEach((n) => { if (n / mpp <= 130) chosen = n; });
    if (elScaleBar) elScaleBar.style.width = Math.round(chosen / mpp) + "px";
    if (elScaleText) elScaleText.textContent = chosen >= 1000 ? (chosen / 1000) + " km" : chosen + " m";
  };
  let mm = 0;
  map.on("mousemove", (e) => {
    const now = performance.now(); if (now - mm < 60) return; mm = now;
    if (elCursor) elCursor.textContent = `${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)}`;
  });
  map.on("moveend zoomend", () => { if (elZoom) elZoom.textContent = "Z" + map.getZoom(); updateScale(); });

  // ---------------- controles ----------------
  document.querySelectorAll("[data-cmd-layer]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.cmdLayer;
      layers[key] = !layers[key];
      btn.classList.toggle("is-on", layers[key]);
      btn.setAttribute("aria-pressed", layers[key] ? "true" : "false");
      if (key === "heat" || key === "rings") applyStaticLayers();
      else recompute();
    });
  });
  const radiusInput = document.getElementById("cmd-radius");
  const radiusLabel = document.getElementById("cmd-radius-label");
  let raf = null;
  if (radiusInput) {
    radiusInput.addEventListener("input", () => {
      radiusKm = Number(radiusInput.value) || 1;
      if (radiusLabel) radiusLabel.textContent = String(radiusKm);
      radiusCircle.setRadius(radiusKm * 1000);
      if (!raf) raf = requestAnimationFrame(() => { raf = null; recompute(); });
    });
  }
  const qb = (sel, fn) => { const el = document.querySelector(sel); if (el) el.addEventListener("click", fn); };
  qb("[data-cmd-zoom-in]", () => map.zoomIn());
  qb("[data-cmd-zoom-out]", () => map.zoomOut());
  qb("[data-cmd-recenter]", () => map.flyTo([epicenter.lat, epicenter.lng], 12, { duration: 0.6 }));

  // ---------------- arranque ----------------
  await loadData();
  populateRings();
  radiusCircle.setLatLng([epicenter.lat, epicenter.lng]);
  epiMarker.setLatLng([epicenter.lat, epicenter.lng]);
  map.setView([epicenter.lat, epicenter.lng], 12);
  if (elMag) elMag.textContent = magnitude != null ? "M " + magnitude.toFixed(1) : "M —";
  if (elEpi) elEpi.textContent = `EPICENTRO · ${epicenter.lat.toFixed(3)}°N ${Math.abs(epicenter.lng).toFixed(3)}°W`;
  applyStaticLayers();
  recompute();
  updateScale();
  if (elZoom) elZoom.textContent = "Z" + map.getZoom();
  setTimeout(() => map.invalidateSize(), 160);
  setTimeout(() => map.invalidateSize(), 480);
});
