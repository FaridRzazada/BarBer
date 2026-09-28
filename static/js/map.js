/* ==========================================================================
   map.js — Leaflet + OpenStreetMap helpers (window.NBMap)
   Pure map concerns: init, markers, geolocation, centering. No page logic here.
   ========================================================================== */
window.NBMap = (function () {
  "use strict";
  let map = null;
  let markersLayer = null;
  let userMarker = null;
  const registry = {}; // proId -> marker

  const PIN_SVG =
    '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><circle cx="12" cy="10" r="3"/><path d="M12 21s-6-5.7-6-11a6 6 0 1 1 12 0c0 5.3-6 11-6 11z" fill="none"/></svg>';

  function makeIcon(type) {
    return L.divIcon({
      className: "pin-wrap",
      html: '<div class="pin ' + (type === "salon" ? "pin--salon" : "") + '">' + PIN_SVG + "</div>",
      iconSize: [30, 30],
      iconAnchor: [15, 30],
      popupAnchor: [0, -30],
    });
  }

  function init(elId, center, zoom) {
    if (map) return map;
    map = L.map(elId, { scrollWheelZoom: true, zoomControl: true }).setView(center, zoom);
    // Esri basemap: keyless and browser-friendly. (OSM's own tile servers block
    // apps under their tile-usage policy; CARTO now watermarks keyless tiles.)
    L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
      {
        maxZoom: 19,
        attribution: "Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors",
      }
    ).addTo(map);
    markersLayer = L.layerGroup().addTo(map);
    return map;
  }

  function popupHtml(p) {
    const rating = p.rating ? "★ " + p.rating + " (" + p.review_count + ")" : "No reviews yet";
    return (
      '<div class="map-popup">' +
      '<div class="map-popup__name">' + esc(p.name) + "</div>" +
      '<div class="map-popup__meta">' + esc(p.type_label || p.type) +
      (p.city ? " · " + esc(p.city) : "") + " · " + rating + "</div>" +
      '<a class="map-popup__link" href="' + p.url + '">View profile →</a>' +
      "</div>"
    );
  }
  function esc(s) { return window.NB.escapeHtml(s); }

  function setMarkers(list, opts) {
    opts = opts || {};
    if (!markersLayer) return;
    markersLayer.clearLayers();
    Object.keys(registry).forEach((k) => delete registry[k]);
    const bounds = [];
    list.forEach((p) => {
      if (p.latitude == null || p.longitude == null) return;
      const marker = L.marker([p.latitude, p.longitude], { icon: makeIcon(p.type) });
      marker.bindPopup(popupHtml(p));
      if (opts.onSelect) marker.on("click", () => opts.onSelect(p.id));
      marker.addTo(markersLayer);
      registry[p.id] = marker;
      bounds.push([p.latitude, p.longitude]);
    });
    if (opts.fit && bounds.length) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
    }
  }

  function highlight(proId) {
    const marker = registry[proId];
    if (marker) marker.openPopup();
  }

  function centerOn(lat, lng, zoom) {
    if (map) map.setView([lat, lng], zoom || 14);
  }

  function setUser(lat, lng) {
    if (!map) return;
    if (userMarker) userMarker.remove();
    userMarker = L.circleMarker([lat, lng], {
      radius: 8, color: "#2b5b8a", weight: 2, fillColor: "#2b5b8a", fillOpacity: 0.5,
    }).addTo(map);
  }

  function locate() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) return reject({ code: 0, message: "unsupported" });
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        (err) => reject(err),
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
      );
    });
  }

  function invalidate() {
    if (map) setTimeout(() => map.invalidateSize(), 120);
  }

  return { init, setMarkers, highlight, centerOn, setUser, locate, invalidate, get map() { return map; } };
})();
