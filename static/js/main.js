/* ==========================================================================
   main.js — global UI: mobile nav, user menu, alerts, favorites, modals
   ========================================================================== */
(function () {
  "use strict";
  const { qs, qsa, post, toast } = window.NB;

  document.addEventListener("DOMContentLoaded", function () {
    initNavToggle();
    initDropdowns();
    initAlerts();
    initFavorites();
    initConfirmForms();
  });

  function initNavToggle() {
    const toggle = qs(".nav__toggle");
    const menu = qs(".nav__mobile");
    if (toggle && menu) {
      toggle.addEventListener("click", () => {
        const open = menu.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }
  }

  // Generic click-to-toggle for elements with [data-toggle="#id"]
  function initDropdowns() {
    qsa("[data-toggle]").forEach((btn) => {
      const target = qs(btn.getAttribute("data-toggle"));
      if (!target) return;
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const cls = btn.getAttribute("data-toggle-class") || "is-open";
        target.classList.toggle(cls);
      });
    });
    document.addEventListener("click", (e) => {
      qsa(".usermenu.is-open, .notif-dropdown.is-open").forEach((el) => {
        if (!el.contains(e.target)) el.classList.remove("is-open");
      });
    });
  }

  function initAlerts() {
    qsa(".alerts .alert").forEach((alert) => {
      const close = alert.querySelector(".alert__close");
      if (close) close.addEventListener("click", () => alert.remove());
      setTimeout(() => alert.remove(), 5200);
    });
  }

  // Favorite heart toggle (used on cards + profile) ------------------------
  function initFavorites() {
    document.body.addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-fav]");
      if (!btn) return;
      e.preventDefault();
      if (btn.dataset.auth === "0") {
        window.location.href = btn.dataset.loginUrl || "/login/";
        return;
      }
      const id = btn.getAttribute("data-fav");
      btn.disabled = true;
      try {
        const res = await post("/api/favorites/", { professional: id });
        btn.classList.toggle("is-active", res.favorited);
        btn.setAttribute("aria-pressed", res.favorited ? "true" : "false");
        toast(res.favorited ? "Added to favorites" : "Removed from favorites", "success", 2200);
      } catch (err) {
        toast(err.message, "danger");
      } finally {
        btn.disabled = false;
      }
    });
  }

  // Confirm before destructive form submits --------------------------------
  function initConfirmForms() {
    qsa("form[data-confirm]").forEach((form) => {
      form.addEventListener("submit", (e) => {
        if (!window.confirm(form.getAttribute("data-confirm"))) e.preventDefault();
      });
    });
  }
})();
