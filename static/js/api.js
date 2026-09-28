/* ==========================================================================
   api.js — shared fetch wrapper, CSRF, toasts, small DOM utilities.
   Exposed as window.NB so other plain scripts can use it without bundling.
   ========================================================================== */
(function () {
  "use strict";

  function getCookie(name) {
    const match = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return match ? decodeURIComponent(match.pop()) : "";
  }

  const csrfToken = () =>
    getCookie("csrftoken") ||
    (document.querySelector('meta[name="csrf-token"]') || {}).content ||
    "";

  async function request(url, options = {}) {
    const opts = Object.assign({ method: "GET", headers: {} }, options);
    opts.headers = Object.assign(
      { "X-Requested-With": "XMLHttpRequest" },
      opts.headers
    );
    const unsafe = !/^(GET|HEAD|OPTIONS)$/i.test(opts.method);
    if (unsafe) opts.headers["X-CSRFToken"] = csrfToken();
    if (opts.json !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.json);
      delete opts.json;
    }
    let response, data;
    try {
      response = await fetch(url, opts);
    } catch (e) {
      throw { message: "Network error. Please check your connection.", status: 0 };
    }
    const text = await response.text();
    try {
      data = text ? JSON.parse(text) : {};
    } catch (e) {
      data = { raw: text };
    }
    if (!response.ok) {
      throw {
        message: (data && (data.error || data.detail)) || "Something went wrong.",
        status: response.status,
        data: data,
      };
    }
    return data;
  }

  const get = (url) => request(url);
  const post = (url, json) => request(url, { method: "POST", json });
  const patch = (url, json) => request(url, { method: "PATCH", json });
  const del = (url) => request(url, { method: "DELETE" });

  /* Toasts ---------------------------------------------------------------- */
  function ensureToastHost() {
    let host = document.querySelector(".alerts");
    if (!host) {
      host = document.createElement("div");
      host.className = "alerts";
      document.body.appendChild(host);
    }
    return host;
  }
  function toast(message, type = "info", timeout = 4200) {
    const host = ensureToastHost();
    const el = document.createElement("div");
    el.className = "alert alert--" + type;
    el.setAttribute("role", "status");
    el.innerHTML =
      '<div>' + escapeHtml(message) + "</div>" +
      '<button class="alert__close" aria-label="Dismiss">&times;</button>';
    el.querySelector(".alert__close").addEventListener("click", () => el.remove());
    host.appendChild(el);
    if (timeout) setTimeout(() => el.remove(), timeout);
  }

  /* Utilities ------------------------------------------------------------- */
  function escapeHtml(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function debounce(fn, wait = 300) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }
  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  window.NB = {
    getCookie, csrfToken, request, get, post, patch, del,
    toast, escapeHtml, debounce, qs, qsa,
  };
})();
