/* ==========================================================================
   search.js — Find page controller + home map. Talks to the API, renders
   cards, and keeps the list and the map in sync. (No results are ever
   filtered in the browser — the backend does the searching.)
   ========================================================================== */
(function () {
  "use strict";
  const { qs, qsa, get, toast, escapeHtml, debounce } = window.NB;
  const cfg = window.NB_CONFIG || {};

  document.addEventListener("DOMContentLoaded", function () {
    if (qs("[data-find-page]")) initFind();
    if (qs("#home-map")) initHome();
    bindHeroSearch();
    bindUseLocationLinks();
  });

  /* ---- shared rendering ------------------------------------------------- */
  function starsHtml(rating) {
    const pct = rating ? (rating / 5) * 100 : 0;
    return '<span class="stars" aria-hidden="true"><span class="stars__fill" style="width:' + pct + '%"></span></span>';
  }

  function cardHtml(p) {
    const verified = p.is_verified
      ? '<span class="badge badge--verified" title="Verified">✓</span>' : "";
    const media = p.profile_image
      ? '<img src="' + p.profile_image + '" alt="' + escapeHtml(p.name) + '" loading="lazy">'
      : '<div class="pro-card__media-fallback"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 20a8 8 0 0 1 16 0"/><circle cx="12" cy="8" r="4"/></svg></div>';
    const ratingBlock = p.review_count
      ? '<span class="rating-inline">' + starsHtml(p.rating) + " <strong>" + p.rating + "</strong> (" + p.review_count + ")</span>"
      : '<span class="muted">No reviews yet</span>';
    const openBadge = p.is_open
      ? '<span class="badge badge--open"><span class="status-dot status-dot--open"></span>Open</span>'
      : '<span class="badge badge--closed"><span class="status-dot status-dot--closed"></span>Closed</span>';
    const price = p.starting_price
      ? '<span class="pro-card__price">' + p.starting_price + " " + (p.currency || "") + ' <small>from</small></span>'
      : '<span class="muted">Price not specified</span>';
    const distance = p.distance != null ? '<span class="pro-card__distance">' + p.distance + " km</span>" : "";
    const favActive = p.is_favorited ? " is-active" : "";

    return (
      '<article class="pro-card" data-pro-id="' + p.id + '">' +
        '<div class="pro-card__media">' +
          '<span class="pro-card__type badge badge--type">' + escapeHtml(p.type_label || p.type) + "</span>" +
          '<div class="pro-card__fav"><button class="fav-btn' + favActive + '" data-fav="' + p.id + '" data-auth="' + (cfg.auth ? "1" : "0") + '" data-login-url="' + (cfg.loginUrl || "/login/") + '" aria-label="Save to favorites" aria-pressed="' + (p.is_favorited ? "true" : "false") + '"><svg viewBox="0 0 24 24"><path d="M12 21s-7-4.5-9.5-9A5.3 5.3 0 0 1 12 6a5.3 5.3 0 0 1 9.5 6c-2.5 4.5-9.5 9-9.5 9z"/></svg></button></div>' +
          media +
        "</div>" +
        '<div class="pro-card__body">' +
          '<h3 class="pro-card__title"><a href="' + p.url + '">' + escapeHtml(p.name) + "</a>" + verified + "</h3>" +
          '<div class="pro-card__meta">' + ratingBlock + (p.city ? '<span class="pro-card__loc">' + escapeHtml(p.city) + "</span>" : "") + openBadge + "</div>" +
          '<div class="pro-card__foot">' +
            "<div>" + price + " " + distance + "</div>" +
            '<div class="pro-card__actions"><a class="btn btn--sm" href="' + p.url + '">View</a>' +
            '<a class="btn btn--sm btn--primary" href="/bookings/new/?professional=' + p.id + '">Book</a></div>' +
          "</div>" +
        "</div>" +
      "</article>"
    );
  }

  function skeletons(host, n) {
    host.innerHTML = "";
    for (let i = 0; i < n; i++) {
      const s = document.createElement("div");
      s.className = "skeleton skeleton-card";
      host.appendChild(s);
    }
  }

  function geoErrorMessage(err) {
    switch (err && err.code) {
      case 1: return "We couldn't access your location. You can search by city or location instead.";
      case 2: return "Your location is unavailable right now. Try searching by city.";
      case 3: return "Getting your location timed out. Try again or search by city.";
      default: return "Location isn't available. You can search by city instead.";
    }
  }

  function buildQuery(params) {
    const q = new URLSearchParams();
    Object.keys(params).forEach((k) => {
      if (params[k] !== "" && params[k] != null && params[k] !== false) q.set(k, params[k]);
    });
    return q.toString();
  }

  /* ---- Find page -------------------------------------------------------- */
  function initFind() {
    const resultsHost = qs("[data-results]");
    const countEl = qs("[data-count]");
    const layout = qs(".find-layout");
    const state = {
      q: (qs("[data-filter='q']") || {}).value || "",
      city: (qs("[data-filter='city']") || {}).value || "",
      professional_type: (document.querySelector(".type-pills .is-active") || {}).dataset?.type || "all",
      service: "",
      sort: "nearest",
      open_now: false,
      price_available: false,
      rating: "",
      lat: null, lng: null,
    };

    const center = cfg.mapCenter || [40.4093, 49.8671];
    NBMap.init("map", center, cfg.zoom || 12);
    NBMap.invalidate();

    async function run() {
      if (resultsHost) skeletons(resultsHost, 6);
      let url, res, list;
      try {
        if (state.lat != null && state.lng != null) {
          url = "/api/professionals/nearby/?" + buildQuery({
            latitude: state.lat, longitude: state.lng, radius: state.radius || cfg.defaultRadius || 10,
            professional_type: state.professional_type, q: state.q, city: state.city,
            service: state.service, open_now: state.open_now, price_available: state.price_available,
            rating: state.rating, sort: state.sort,
          });
          res = await get(url);
          list = res.results;
        } else {
          url = "/api/professionals/?" + buildQuery({
            professional_type: state.professional_type, q: state.q, city: state.city,
            service: state.service, price_available: state.price_available, rating: state.rating,
            sort: state.sort === "nearest" ? "newest" : state.sort,
          });
          res = await get(url);
          list = res.results;
        }
      } catch (err) {
        toast(err.message, "danger");
        if (resultsHost) resultsHost.innerHTML = emptyState("We couldn't load results.", "Please try again.");
        return;
      }
      render(list);
    }

    function render(list) {
      if (countEl) countEl.textContent = list.length + (list.length === 1 ? " result" : " results");
      if (resultsHost) {
        resultsHost.innerHTML = list.length
          ? list.map(cardHtml).join("")
          : emptyState("No professionals found.", "Try increasing your radius or changing your filters.");
      }
      NBMap.setMarkers(list, { fit: list.length > 0, onSelect: (id) => focusCard(id) });
    }

    function focusCard(id) {
      qsa(".pro-card").forEach((c) => c.classList.remove("is-highlight"));
      const card = qs('.pro-card[data-pro-id="' + id + '"]');
      if (card) { card.classList.add("is-highlight"); card.scrollIntoView({ behavior: "smooth", block: "center" }); }
    }

    // Filter bindings
    const debouncedRun = debounce(run, 350);
    qsa("[data-filter]").forEach((el) => {
      const evt = el.tagName === "SELECT" || el.type === "checkbox" ? "change" : "input";
      el.addEventListener(evt, () => {
        const key = el.getAttribute("data-filter");
        state[key] = el.type === "checkbox" ? el.checked : el.value;
        if (evt === "change") run(); else debouncedRun();
      });
    });
    qsa(".type-pills [data-type]").forEach((btn) => {
      btn.addEventListener("click", () => {
        qsa(".type-pills [data-type]").forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        state.professional_type = btn.dataset.type;
        run();
      });
    });

    const locBtn = qs("[data-use-location]");
    if (locBtn) {
      locBtn.addEventListener("click", async () => {
        locBtn.classList.add("is-loading");
        try {
          const { lat, lng } = await NBMap.locate();
          state.lat = lat; state.lng = lng; state.sort = "nearest";
          NBMap.centerOn(lat, lng, 13); NBMap.setUser(lat, lng);
          run();
          toast("Showing professionals near you.", "success", 2200);
        } catch (err) {
          toast(geoErrorMessage(err), "warning");
        } finally {
          locBtn.classList.remove("is-loading");
        }
      });
    }

    // Card hover highlights the matching marker
    if (resultsHost) {
      resultsHost.addEventListener("mouseover", (e) => {
        const card = e.target.closest(".pro-card");
        if (card) NBMap.highlight(card.getAttribute("data-pro-id"));
      });
    }

    // Mobile list/map toggle
    qsa("[data-view]").forEach((btn) => {
      btn.addEventListener("click", () => {
        qsa("[data-view]").forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        layout.classList.remove("show-map", "show-list");
        layout.classList.add(btn.dataset.view === "map" ? "show-map" : "show-list");
        NBMap.invalidate();
      });
    });

    run();
  }

  /* ---- Home page map ---------------------------------------------------- */
  function initHome() {
    const center = cfg.mapCenter || [40.4093, 49.8671];
    NBMap.init("home-map", center, cfg.zoom || 12);
    NBMap.invalidate();
    const listHost = qs("#home-nearby");

    async function load(lat, lng) {
      try {
        const res = await get("/api/professionals/nearby/?" + buildQuery({
          latitude: lat, longitude: lng, radius: cfg.defaultRadius || 10,
        }));
        NBMap.setMarkers(res.results, { fit: res.results.length > 0, onSelect: () => {} });
        if (listHost && res.results.length) {
          listHost.innerHTML = res.results.slice(0, 8).map(cardHtml).join("");
        }
      } catch (e) { /* keep server-rendered fallback */ }
    }
    load(center[0], center[1]);

    const locBtn = qs("[data-use-location]");
    if (locBtn) {
      locBtn.addEventListener("click", async () => {
        locBtn.classList.add("is-loading");
        try {
          const { lat, lng } = await NBMap.locate();
          NBMap.centerOn(lat, lng, 13); NBMap.setUser(lat, lng);
          load(lat, lng);
        } catch (err) {
          toast(geoErrorMessage(err), "warning");
        } finally {
          locBtn.classList.remove("is-loading");
        }
      });
    }
  }

  function emptyState(title, sub) {
    return '<div class="empty-state"><h3>' + escapeHtml(title) + "</h3><p>" + escapeHtml(sub) + "</p></div>";
  }

  /* Hero search submits to /find/ with query params */
  function bindHeroSearch() {
    const form = qs("[data-hero-search]");
    if (!form) return;
    form.addEventListener("submit", (e) => {
      // Native GET submit to /find/ is fine; nothing to do.
    });
  }

  function bindUseLocationLinks() {
    // handled per-page above; placeholder for future global hooks
  }
})();
