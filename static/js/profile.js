/* ==========================================================================
   profile.js — dashboard location picker (click the map to set lat/lng)
   ========================================================================== */
(function () {
  "use strict";
  const { qs } = window.NB;
  const cfg = window.NB_CONFIG || {};

  document.addEventListener("DOMContentLoaded", function () {
    const mapEl = qs("#location-picker");
    if (!mapEl || typeof L === "undefined") return;

    const latInput = qs("#id_latitude");
    const lngInput = qs("#id_longitude");
    const hasPoint = latInput && latInput.value && lngInput && lngInput.value;
    const start = hasPoint
      ? [parseFloat(latInput.value), parseFloat(lngInput.value)]
      : (cfg.mapCenter || [40.4093, 49.8671]);

    const map = L.map("location-picker").setView(start, hasPoint ? 15 : (cfg.zoom || 12));
    L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 19, attribution: "Tiles &copy; Esri" }
    ).addTo(map);

    let marker = hasPoint ? L.marker(start, { draggable: true }).addTo(map) : null;

    function setPoint(lat, lng) {
      if (latInput) latInput.value = lat.toFixed(6);
      if (lngInput) lngInput.value = lng.toFixed(6);
    }
    function placeMarker(lat, lng) {
      if (marker) marker.setLatLng([lat, lng]);
      else {
        marker = L.marker([lat, lng], { draggable: true }).addTo(map);
        marker.on("dragend", () => {
          const p = marker.getLatLng();
          setPoint(p.lat, p.lng);
        });
      }
      setPoint(lat, lng);
    }
    if (marker) {
      marker.on("dragend", () => {
        const p = marker.getLatLng();
        setPoint(p.lat, p.lng);
      });
    }

    map.on("click", (e) => placeMarker(e.latlng.lat, e.latlng.lng));

    const useBtn = qs("#location-use-gps");
    if (useBtn) {
      useBtn.addEventListener("click", () => {
        if (!navigator.geolocation) return window.NB.toast("Geolocation isn't available.", "warning");
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            map.setView([pos.coords.latitude, pos.coords.longitude], 15);
            placeMarker(pos.coords.latitude, pos.coords.longitude);
          },
          () => window.NB.toast("We couldn't access your location.", "warning")
        );
      });
    }

    setTimeout(() => map.invalidateSize(), 150);
  });
})();
