# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier dokumentiert.

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung nach [Semantic Versioning](https://semver.org/lang/de/).

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
