/* ==========================================================================
   notifications.js — navbar bell: unread polling + mark-read interactions
   ========================================================================== */
(function () {
  "use strict";
  const { qs, qsa, get, post } = window.NB;

  document.addEventListener("DOMContentLoaded", function () {
    const bell = qs("#notif-bell");
    if (!bell) return; // only for authenticated pages
    const badge = qs("#notif-badge");
    const dropdown = qs("#notif-dropdown");

    async function refreshCount() {
      try {
        const res = await get("/api/notifications/unread-count/");
        updateBadge(res.count);
      } catch (e) { /* silent */ }
    }
    function updateBadge(count) {
      if (!badge) return;
      if (count > 0) {
        badge.textContent = count > 99 ? "99+" : count;
        badge.hidden = false;
      } else {
        badge.hidden = true;
      }
    }

    // Mark read on click (works for navbar dropdown items and the page list).
    document.body.addEventListener("click", async (e) => {
      const item = e.target.closest("[data-notif-id]");
      if (!item) return;
      const id = item.getAttribute("data-notif-id");
      const url = item.getAttribute("data-notif-url");
      try {
        await post("/api/notifications/" + id + "/read/", {});
        item.classList.remove("is-unread");
        refreshCount();
      } catch (err) { /* navigate anyway */ }
      if (url) window.location.href = url;
    });

    const markAll = qs("#notif-mark-all");
    if (markAll) {
      markAll.addEventListener("click", async () => {
        try {
          await post("/api/notifications/read-all/", {});
          qsa(".is-unread").forEach((el) => el.classList.remove("is-unread"));
          updateBadge(0);
        } catch (e) {}
      });
    }

    refreshCount();
    setInterval(refreshCount, 45000);
  });
})();
