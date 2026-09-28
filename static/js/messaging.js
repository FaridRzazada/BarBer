/* ==========================================================================
   messaging.js — conversations list + thread with AJAX polling.
   Architecture stays transport-agnostic so WebSockets can replace polling.
   ========================================================================== */
(function () {
  "use strict";
  const { qs, qsa, get, post, toast, escapeHtml } = window.NB;

  document.addEventListener("DOMContentLoaded", function () {
    const root = qs("[data-messaging]");
    if (!root) return;

    const listHost = qs("#conv-list");
    const thread = qs("#chat-thread");
    const messagesHost = qs("#chat-messages");
    const composer = qs("#chat-composer");
    const input = qs("#chat-input");
    const titleEl = qs("#chat-title");
    let currentId = root.getAttribute("data-initial") || null;
    const pendingProfessional = root.getAttribute("data-professional") || null;
    let pollTimer = null;

    async function loadConversations() {
      try {
        const res = await get("/api/messages/");
        renderConversations(res.results);
        if (!currentId && res.results.length) openConversation(res.results[0].id);
      } catch (e) { /* silent */ }
    }

    function renderConversations(list) {
      if (!list.length) {
        listHost.innerHTML = '<div class="toast-empty" style="padding:1rem">No conversations yet.</div>';
        return;
      }
      listHost.innerHTML = list.map((c) => (
        '<button class="conv' + (String(c.id) === String(currentId) ? " is-active" : "") + '" data-conv="' + c.id + '">' +
          '<div style="flex:1;min-width:0">' +
            '<div class="conv__name">' + escapeHtml(c.other_name) + "</div>" +
            '<div class="conv__last">' + escapeHtml(c.last_message || "") + "</div>" +
          "</div>" +
          (c.unread_count ? '<span class="conv__unread">' + c.unread_count + "</span>" : "") +
        "</button>"
      )).join("");
      qsa(".conv", listHost).forEach((btn) =>
        btn.addEventListener("click", () => openConversation(btn.getAttribute("data-conv")))
      );
    }

    async function openConversation(id) {
      currentId = id;
      root.classList.add("show-thread");
      qsa(".conv", listHost).forEach((b) => b.classList.toggle("is-active", b.getAttribute("data-conv") === String(id)));
      await loadMessages();
      startPolling();
    }

    async function loadMessages() {
      if (!currentId) return;
      try {
        const res = await get("/api/messages/" + currentId + "/");
        if (titleEl) titleEl.textContent = res.other_name || "Conversation";
        renderMessages(res.results);
      } catch (e) { /* silent */ }
    }

    function renderMessages(list) {
      messagesHost.innerHTML = list.map((m) => (
        '<div class="bubble ' + (m.is_mine ? "bubble--out" : "bubble--in") + '">' +
          escapeHtml(m.body) +
          '<span class="bubble__time">' + formatTime(m.created_at) + "</span>" +
        "</div>"
      )).join("");
      messagesHost.scrollTop = messagesHost.scrollHeight;
    }

    function formatTime(iso) {
      try { return new Date(iso).toLocaleString([], { hour: "2-digit", minute: "2-digit", month: "short", day: "numeric" }); }
      catch (e) { return ""; }
    }

    if (composer) {
      composer.addEventListener("submit", async (e) => {
        e.preventDefault();
        const body = input.value.trim();
        if (!body) return;
        if (!currentId && !pendingProfessional) return;
        input.value = "";
        const payload = currentId
          ? { conversation: parseInt(currentId, 10), body: body }
          : { professional: parseInt(pendingProfessional, 10), body: body };
        try {
          const res = await post("/api/messages/", payload);
          if (!currentId) { currentId = res.conversation; root.classList.add("show-thread"); }
          await loadMessages();
          loadConversations();
        } catch (err) {
          toast(err.message, "danger");
          input.value = body;
        }
      });
    }

    // If arriving from a professional profile, show the composer ready to send.
    if (pendingProfessional && !currentId) {
      root.classList.add("show-thread");
      const empty = qs("#chat-empty");
      if (empty) empty.textContent = "Send a message to start the conversation.";
      if (input) input.focus();
    }

    function startPolling() {
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = setInterval(() => { loadMessages(); }, 8000);
    }

    // Back button on mobile
    const backBtn = qs("#chat-back");
    if (backBtn) backBtn.addEventListener("click", () => root.classList.remove("show-thread"));

    loadConversations();
    if (currentId) openConversation(currentId);
  });
})();
