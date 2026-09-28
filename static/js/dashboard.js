/* ==========================================================================
   dashboard.js — small enhancements: tabs, hours "open" toggles
   ========================================================================== */
(function () {
  "use strict";
  const { qs, qsa } = window.NB;

  document.addEventListener("DOMContentLoaded", function () {
    initTabs();
    initHoursToggles();
  });

  function initTabs() {
    qsa("[data-tabs]").forEach((group) => {
      const tabs = qsa(".tab", group);
      tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
          tabs.forEach((t) => t.classList.remove("is-active"));
          tab.classList.add("is-active");
          const panelId = tab.getAttribute("data-tab");
          qsa("[data-panel]").forEach((p) => {
            p.hidden = p.getAttribute("data-panel") !== panelId;
          });
        });
      });
    });
  }

  // On the hours editor, disable time inputs for closed days.
  function initHoursToggles() {
    qsa(".hours-row").forEach((row) => {
      const toggle = row.querySelector('input[type="checkbox"]');
      const times = qsa('input[type="time"]', row);
      if (!toggle) return;
      const sync = () => times.forEach((t) => (t.disabled = !toggle.checked));
      toggle.addEventListener("change", sync);
      sync();
    });
  }
})();
