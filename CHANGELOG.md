# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier dokumentiert.

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung nach [Semantic Versioning](https://semver.org/lang/de/).

## 0.1.2 — 2026-07-30

### Behoben / Fixed
- **App im AppAPI-Embedded-Modus (Top-Menu-Proxy) unbenutzbar.** Fünf Blocker behoben, die im
  Browser zu 404 / leerer Seite / 405 führten. / Five blockers that made the app unusable in the
  AppAPI embedded (top-menu proxy) mode.
  - **Fehlender `<routes>`-Block** in `appinfo/info.xml` → AppAPI registrierte keine Proxy-Route,
    jeder Zugriff endete im 404. Routen für `/`, `/(js|css|img)/*`, `/api/*` ergänzt. / Missing
    `<routes>` block → 404 on everything; routes added.
  - **`static/` fehlte im installierten Paket** → App lieferte ihre Assets als 404. `static/**/*`
    als `package-data` (pyproject.toml) + Build-Assert im Dockerfile. / `static/` was not bundled.
  - **Frontend baute das DOM im Embedded-Modus nicht auf** → leere Seite. `main.js` erzeugt das UI
    jetzt zur Laufzeit per DOM-API in `#content` und lädt sein Stylesheet dynamisch. / Frontend now
    builds its DOM at runtime.
  - **API-Basis war `document.baseURI`** → POST landete auf der GET-only-Route (405). `API_BASE`
    wird jetzt aus dem Proxy-Pfad abgeleitet. / API base now derived from the proxy path.
  - **`user_manual`-Quell-URLs ohne `/en/`** → 404 auf docs.nextcloud.com. 84 URLs in
    `data/nextcloud_meta.jsonl` korrigiert (`admin_manual` bleibt ohne `/en/`). / 84 user_manual
    source URLs fixed.

### Geändert / Changed
- Store-Beschreibung um **Voraussetzungen** (AppAPI + Deploy-Daemon) und **Installation** ergänzt
  (DE + EN); `<nextcloud max-version>` 33 → 34. / Store description expanded with requirements and
  installation; max-version raised 33 → 34.

## 0.1.1 — 2026-07-27

### Behoben / Fixed
- **Konfigmaske und Chat gleichzeitig sichtbar.** Ein CSS-Konflikt (`.config`/`.chat` mit
  `display: flex` überschrieb das `[hidden]`-Attribut) ließ beide Bereiche gleichzeitig erscheinen.
  `[hidden] { display: none !important; }` ergänzt — es wird nun immer nur der passende Bereich
  gezeigt. / Config form and chat were shown at the same time (a `display: flex` rule overrode the
  `[hidden]` attribute); fixed with an explicit `[hidden]` rule.

### Hinzugefügt / Added
- Store-Screenshots (Konfigmaske + Chat mit Quellen) + `<screenshot>`-Verweise im info.xml;
  reproduzierbar über `tools/make_screenshots.py`. / Store screenshots + info.xml references.

## 0.1.0 — 2026-07-27

### Hinzugefügt / Added
- **Erste Version.** Eigenständige, autarke Nextcloud-App (AppAPI): lokale semantische Suche
  über die Nextcloud-Doku (admin/user/developer, stable33) mit mitgeliefertem FAISS/e5-large-Index,
  Bring-your-own-key (OpenAI/Anthropic/Ollama), Antworten mit Quellenangabe auf docs.nextcloud.com. /
  First release: standalone self-contained Nextcloud app with local semantic search over the
  Nextcloud docs, bring-your-own-key LLM, sourced answers.
