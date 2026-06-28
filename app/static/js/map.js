window.addEventListener("DOMContentLoaded", async () => {
  "use strict";
  const element = document.getElementById("report-map");
  const status = document.getElementById("map-status");
  if (!element || typeof L === "undefined") return;
  const map = L.map(element, { scrollWheelZoom: false }).setView([8.0, -66.0], 6);
  L.tileLayer(element.dataset.tileUrl, {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);
  try {
    const response = await fetch(element.dataset.mapEndpoint, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("map-data");
    const payload = await response.json();
    const bounds = [];
    payload.reports.forEach((report) => {
      const point = [report.location.latitude, report.location.longitude];
      bounds.push(point);
      const popup = document.createElement("div");
      const heading = document.createElement("strong");
      heading.textContent = report.title;
      const location = document.createElement("p");
      location.textContent = report.location.label;
      const link = document.createElement("a");
      link.href = report.url;
      link.textContent = "Ver reporte revisado";
      popup.append(heading, location, link);
      L.marker(point).addTo(map).bindPopup(popup);
    });
    if (bounds.length) map.fitBounds(bounds, { padding: [24, 24], maxZoom: 13 });
    status.textContent = `${payload.reports.length} reportes con ubicación aproximada.`;
  } catch (_) {
    status.textContent = "El mapa no pudo cargarse. Usa el listado de reportes.";
  }
});
