// SIMOSphere AI Copilot Mini — Frontend.
// CSP-hart: ausschliesslich createElement / textContent / addEventListener, nie innerHTML mit Daten.
// Kein externes Skript, keine Inline-Handler.
//
// Läuft in ZWEI Modi:
//   * Standalone  — index.html wird über "/" ausgeliefert, enthält bereits <div id="content">.
//   * AppAPI-Embedded (Top-Menu) — Nextcloud rendert nur <div id="content"></div> und injiziert
//     dieses Skript; das UI-Markup existiert dann NICHT und muss zur Laufzeit erzeugt werden.
// Deshalb baut main.js sein UI immer selbst in #content auf (einzige UI-Quelle, kein Duplikat zur
// index.html) und lädt sein Stylesheet dynamisch.
"use strict";

(function () {
  // --- API-Basis -------------------------------------------------------------------------
  // Im Embedded-Modus zeigt die Seiten-URL auf .../app_api/embedded/<appid>/...; relative fetch()
  // müssen aber über .../app_api/proxy/<appid>/ laufen, sonst landet POST auf der GET-only-Route
  // (HTTP 405) bzw. der Asset-Pfad im 404. Standalone: Basis = Verzeichnis der aktuellen Seite.
  const API_BASE = (function () {
    const p = window.location.pathname;
    if (/\/embedded\/[^/]+\//.test(p)) {
      return new URL(
        p.replace(/\/embedded\/([^/]+)\/.*$/, "/proxy/$1/"),
        window.location.origin
      ).toString();
    }
    return new URL(".", document.baseURI).toString();
  })();
  const api = (path) => new URL(path, API_BASE).toString();

  const $ = (id) => document.getElementById(id);

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

  // --- DOM-Helfer + UI-Aufbau ------------------------------------------------------------

  function el(tag, props, children) {
    const n = document.createElement(tag);
    if (props) {
      for (const k in props) {
        const v = props[k];
        if (v === null || v === undefined || v === false) continue;
        if (k === "class") n.className = v;
        else if (k === "text") n.textContent = v;
        else if (k === "hidden") n.hidden = !!v;
        else if (k in n) n[k] = v;
        else n.setAttribute(k, v);
      }
    }
    if (children) for (const c of children) if (c) n.appendChild(c);
    return n;
  }

  // Lädt css/style.css relativ zur API-Basis, falls noch kein passendes Stylesheet eingebunden ist
  // (im Embedded-Modus fehlt der <link> aus index.html).
  function ensureStylesheet() {
    const has = Array.prototype.some.call(
      document.querySelectorAll('link[rel="stylesheet"]'),
      (l) => (l.getAttribute("href") || "").indexOf("style.css") !== -1
    );
    if (has) return;
    document.head.appendChild(el("link", { rel: "stylesheet", href: api("css/style.css") }));
  }

  // Baut das komplette UI (identisch zu index.html) per DOM-API in `root`.
  function buildUI(root) {
    const header = el("header", { class: "head" }, [
      el("h1", { text: "Nextcloud Documentation Assistant" }),
      el("p", {
        class: "sub",
        text: "Ask about administering and using Nextcloud — answers cite the docs.",
      }),
    ]);

    const provider = el("select", { id: "provider" }, [
      el("option", { value: "openai", text: "OpenAI" }),
      el("option", { value: "anthropic", text: "Anthropic" }),
      el("option", { value: "ollama", text: "Ollama (local)" }),
    ]);

    const config = el("section", { id: "config", class: "config", hidden: true }, [
      el("h2", { text: "Connect a language model" }),
      el("p", {
        class: "hint",
        text:
          "Bring your own key — nothing is sent to any SIMO server. The key is stored only in your " +
          "Nextcloud instance.",
      }),
      el("label", { for: "provider", text: "Provider" }),
      provider,
      el("label", { for: "apikey", "data-for": "key", text: "API key" }),
      el("input", { id: "apikey", type: "password", autocomplete: "off", placeholder: "sk-…" }),
      el("label", { for: "baseurl", "data-for": "ollama", hidden: true, text: "Ollama base URL" }),
      el("input", { id: "baseurl", type: "url", placeholder: "http://localhost:11434", hidden: true }),
      el("label", { for: "model", text: "Model (optional)" }),
      el("input", { id: "model", type: "text", placeholder: "leave empty for default" }),
      el("button", { id: "save", type: "button", text: "Save" }),
      el("p", { id: "config-msg", class: "msg", role: "status", "aria-live": "polite" }),
    ]);

    const ask = el("form", { id: "ask", class: "ask" }, [
      el("input", {
        id: "q",
        type: "text",
        autocomplete: "off",
        placeholder: "How do I put the server into maintenance mode?",
        "aria-label": "Your question",
      }),
      el("button", { id: "send", type: "submit", text: "Ask" }),
    ]);

    const chat = el("section", { id: "chat", class: "chat", hidden: true }, [
      el("div", { id: "log", class: "log", "aria-live": "polite" }),
      ask,
      el("button", { id: "reconfigure", type: "button", class: "link", text: "Change model" }),
    ]);

    const footer = el("footer", { class: "foot" }, [
      el("p", {}, [
        el("span", { text: "Free & open source. The full " }),
        el("strong", { text: "SIMOSphere AI Copilot" }),
        el("span", { text: " brings this assistant to " }),
        el("em", { text: "your own" }),
        el("span", { text: " data — files, mail, ERP and more. " }),
        el("a", {
          id: "upgrade",
          href: "https://www.simo-online.com",
          target: "_blank",
          rel: "noopener noreferrer",
          text: "Learn more →",
        }),
      ]),
      el("p", {
        class: "attr",
        text:
          "Documentation content: Nextcloud Documentation, CC BY 3.0. Not affiliated with Nextcloud GmbH.",
      }),
    ]);

    const appEl = el("main", { id: "app" }, [header, config, chat, footer]);
    root.appendChild(appEl);
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
    const el2 = document.createElement("div");
    el2.className = "msg " + role;
    el2.textContent = text;
    $("log").appendChild(el2);
    $("log").scrollTop = $("log").scrollHeight;
    return el2;
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

  function start() {
    // Ziel-Container: sowohl standalone (index.html) als auch AppAPI-Embedded liefern #content.
    const root = $("content") || document.body;
    ensureStylesheet();
    // Doppel-Aufbau vermeiden, falls das Skript zweimal injiziert wird.
    if (!$("app")) buildUI(root);
    init();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
