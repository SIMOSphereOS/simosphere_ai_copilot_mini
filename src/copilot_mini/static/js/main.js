// SIMOSphere AI Copilot Mini — Frontend.
// CSP-hart: ausschliesslich createElement / textContent / addEventListener, nie innerHTML mit Daten.
// Kein externes Skript, keine Inline-Handler.
"use strict";

(function () {
  const $ = (id) => document.getElementById(id);

  // Relative API-Basis: die ExApp wird über den AppAPI-Proxy ausgeliefert, Pfade sind relativ.
  const api = (path) => new URL(path, document.baseURI).toString();

  async function getJSON(path) {
    const r = await fetch(api(path), { headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }
  async function postJSON(path, body) {
    const r = await fetch(api(path), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      let detail = "HTTP " + r.status;
      try {
        const j = await r.json();
        if (j && j.detail) detail = j.detail;
      } catch (e) {
        /* Text-Antwort ohne JSON — Status genügt. */
      }
      throw new Error(detail);
    }
    return r.json();
  }

  // --- Ansichten umschalten --------------------------------------------------------------

  function showConfig(status) {
    $("config").hidden = false;
    $("chat").hidden = true;
    if (status && status.provider) $("provider").value = status.provider;
    syncProviderFields();
  }
  function showChat() {
    $("config").hidden = true;
    $("chat").hidden = false;
    $("q").focus();
  }

  function syncProviderFields() {
    const p = $("provider").value;
    const isOllama = p === "ollama";
    $("baseurl").hidden = !isOllama;
    document.querySelector('label[data-for="ollama"]').hidden = !isOllama;
    // Ollama braucht keinen Key.
    $("apikey").hidden = isOllama;
    document.querySelector('label[data-for="key"]').hidden = isOllama;
  }

  // --- Konfiguration ---------------------------------------------------------------------

  async function saveConfig() {
    const msg = $("config-msg");
    msg.textContent = "Saving…";
    const body = {
      provider: $("provider").value,
      api_key: $("apikey").value || null,
      base_url: $("baseurl").value || null,
      model: $("model").value || null,
    };
    try {
      const status = await postJSON("api/config", body);
      if (status.configured) {
        msg.textContent = "";
        $("apikey").value = "";
        showChat();
      } else {
        msg.textContent = "Please provide the required credentials for this provider.";
      }
    } catch (e) {
      msg.textContent = "Could not save: " + e.message;
    }
  }

  // --- Chat ------------------------------------------------------------------------------

  function addMessage(role, text) {
    const el = document.createElement("div");
    el.className = "msg " + role;
    el.textContent = text;
    $("log").appendChild(el);
    $("log").scrollTop = $("log").scrollHeight;
    return el;
  }

  function addSources(sources) {
    if (!Array.isArray(sources) || sources.length === 0) return;
    const box = document.createElement("div");
    box.className = "sources";
    const label = document.createElement("span");
    label.className = "sources-label";
    label.textContent = "Sources:";
    box.appendChild(label);
    for (const s of sources) {
      // Nur vertrauenswürdige Doku-Links als anklickbar rendern; sonst reiner Text.
      const url = typeof s.url === "string" ? s.url : "";
      const title = (s.title && String(s.title)) || url || "source";
      if (url.startsWith("https://docs.nextcloud.com/")) {
        const a = document.createElement("a");
        a.href = url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.textContent = title;
        box.appendChild(a);
      } else {
        const span = document.createElement("span");
        span.textContent = title;
        box.appendChild(span);
      }
    }
    $("log").appendChild(box);
    $("log").scrollTop = $("log").scrollHeight;
  }

  async function ask(event) {
    event.preventDefault();
    const q = $("q").value.trim();
    if (!q) return;
    $("q").value = "";
    addMessage("user", q);
    $("send").disabled = true;
    const pending = addMessage("ai pending", "…");
    try {
      const res = await postJSON("api/chat", { question: q });
      pending.classList.remove("pending");
      pending.textContent = res.answer || "";
      addSources(res.sources);
    } catch (e) {
      pending.classList.remove("pending");
      pending.classList.add("error");
      pending.textContent =
        e.message === "LLM not configured"
          ? "No language model is configured yet."
          : "Sorry — something went wrong (" + e.message + ").";
      if (e.message === "LLM not configured") showConfig(null);
    } finally {
      $("send").disabled = false;
      $("q").focus();
    }
  }

  // --- Start -----------------------------------------------------------------------------

  async function init() {
    $("provider").addEventListener("change", syncProviderFields);
    $("save").addEventListener("click", saveConfig);
    $("ask").addEventListener("submit", ask);
    $("reconfigure").addEventListener("click", () => showConfig(null));
    try {
      const status = await getJSON("api/config");
      if (status.configured) showChat();
      else showConfig(status);
    } catch (e) {
      showConfig(null);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
