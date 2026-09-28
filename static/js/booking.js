/* ==========================================================================
   booking.js — booking wizard: pick service → (barber) → date → slot → confirm
   Always re-fetches availability from the backend; never trusts stale slots.
   ========================================================================== */
(function () {
  "use strict";
  const { qs, qsa, get, post, toast, escapeHtml, debounce } = window.NB;

  document.addEventListener("DOMContentLoaded", function () {
    const root = qs("[data-booking]");
    if (!root) return;

    const professionalId = root.getAttribute("data-professional");
    const isSalon = root.getAttribute("data-type") === "salon";

    const state = { service: null, duration: null, price: null, barber: "", date: "", start: "" };

    const slotHost = qs("#slot-options");
    const confirmBtn = qs("#booking-confirm");
    const dateInput = qs("#booking-date");

    // Preselects passed from the server (e.g. "Book with Ali")
    const pre = root.dataset;

    /* Service selection */
    qsa("#service-options .option").forEach((opt) => {
      opt.addEventListener("click", () => selectService(opt));
      if (pre.preselectService && opt.dataset.service === pre.preselectService) selectService(opt);
    });
    function selectService(opt) {
      qsa("#service-options .option").forEach((o) => o.classList.remove("is-selected"));
      opt.classList.add("is-selected");
      state.service = opt.dataset.service;
      state.duration = opt.dataset.duration;
      state.price = opt.dataset.price || "";
      setSummary("service", opt.dataset.name);
      setSummary("price", state.price ? state.price + " " + (opt.dataset.currency || "") : "—");
      loadSlots();
    }

    /* Barber selection (salon only) */
    qsa("#barber-options .option").forEach((opt) => {
      opt.addEventListener("click", () => {
        qsa("#barber-options .option").forEach((o) => o.classList.remove("is-selected"));
        opt.classList.add("is-selected");
        state.barber = opt.dataset.barber || "";
        setSummary("barber", opt.dataset.name);
        loadSlots();
      });
      if (pre.preselectBarber && opt.dataset.barber === pre.preselectBarber) opt.click();
    });

    /* Date selection */
    if (dateInput) {
      const today = new Date().toISOString().slice(0, 10);
      dateInput.min = today;
      dateInput.addEventListener("change", () => {
        state.date = dateInput.value;
        setSummary("date", dateInput.value);
        loadSlots();
      });
    }

    async function loadSlots() {
      state.start = "";
      setSummary("time", "—");
      if (!state.service || !state.date) {
        slotHost.innerHTML = '<p class="toast-empty">Pick a service and date to see available times.</p>';
        return;
      }
      slotHost.innerHTML = '<div class="skeleton skeleton-line w-80"></div><div class="skeleton skeleton-line w-60"></div>';
      const q = new URLSearchParams({ professional: professionalId, service: state.service, date: state.date });
      if (isSalon && state.barber) q.set("barber", state.barber);
      try {
        const res = await get("/api/bookings/available-slots/?" + q.toString());
        renderSlots(res.slots || []);
      } catch (err) {
        slotHost.innerHTML = '<p class="toast-empty">We couldn\'t load available times. Please try again.</p>';
        toast(err.message, "danger");
      }
    }

    function renderSlots(slots) {
      const available = slots.filter((s) => s.available);
      if (!available.length) {
        slotHost.innerHTML = '<div class="empty-state"><p>No available times on this day. Try another date.</p></div>';
        return;
      }
      slotHost.innerHTML = "";
      available.forEach((s) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "slot";
        btn.textContent = s.start;
        btn.addEventListener("click", () => {
          qsa(".slot", slotHost).forEach((b) => b.classList.remove("is-selected"));
          btn.classList.add("is-selected");
          state.start = s.start;
          setSummary("time", s.start + "–" + s.end);
        });
        slotHost.appendChild(btn);
      });
    }

    function setSummary(key, val) {
      const el = qs('[data-sum-' + key + ']');
      if (el) el.textContent = val || "—";
    }

    if (confirmBtn) {
      confirmBtn.addEventListener("click", async () => {
        if (!state.service) return toast("Please choose a service.", "warning");
        if (!state.date) return toast("Please choose a date.", "warning");
        if (!state.start) return toast("Please choose a time.", "warning");
        confirmBtn.classList.add("is-loading");
        confirmBtn.disabled = true;
        const payload = {
          professional: parseInt(professionalId, 10),
          service: parseInt(state.service, 10),
          date: state.date,
          start_time: state.start,
          notes: (qs("#booking-notes") || {}).value || "",
        };
        if (isSalon && state.barber) payload.barber = parseInt(state.barber, 10);
        try {
          const res = await post("/api/bookings/", payload);
          window.location.href = "/bookings/" + res.booking_id + "/?created=1";
        } catch (err) {
          toast(err.message, "danger");
          confirmBtn.classList.remove("is-loading");
          confirmBtn.disabled = false;
          loadSlots(); // availability may have changed
        }
      });
    }
  });
})();
