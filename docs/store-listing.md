# App Store Listing — SIMOSphere AI Copilot Mini

Vorlage für die Veröffentlichung auf https://apps.nextcloud.com (ExApp / AppAPI).
Der eigentliche Upload erfolgt nach dem Merge des Zertifikatsantrags (PR #1113).

## Eckdaten
- **App-ID:** `simosphere_ai_copilot_mini`
- **Kategorien:** `tools`, `integration`
- **Lizenz:** AGPL-3.0-or-later
- **Nextcloud:** 30–33
- **Image:** `ghcr.io/simosphereos/simosphere-ai-copilot-mini:0.1.0` (public)
- **Quellcode:** https://github.com/SIMOSphereOS/simosphere_ai_copilot_mini

## Summary (max. ~1 Satz)
Ask your Nextcloud documentation in natural language — answers with sources, using your own LLM key.

## Beschreibung (Store-Text, EN)
**SIMOSphere AI Copilot Mini** is a free, open-source assistant for the Nextcloud documentation.
Ask how to configure, administer or use Nextcloud and get concise, practical answers — each one
citing the exact `docs.nextcloud.com` page it is based on.

- **Local semantic search** over the official admin, user and developer manuals. A prebuilt,
  multilingual index ships with the app — ask in your language, get answers grounded in the docs.
- **Bring your own key** — use OpenAI, Anthropic or a local Ollama model. Nothing is sent to any
  SIMO server; the app is fully self-contained.
- **Sourced answers** — every reply links to the documentation page it came from.
- **Privacy-first** — the knowledge base is bundled with the app; only your question and the
  retrieved snippets reach the LLM provider you configured.

Copilot Mini is the free little sibling of **SIMOSphere AI Copilot**, the full product that brings
the same assistant to *your own* data — files, mail, ERP, compliance knowledge, roles and tools,
all under your users' own Nextcloud identities. See https://www.simo-online.com.

*Documentation content: Nextcloud Documentation, CC BY 3.0. Not affiliated with Nextcloud GmbH.*

## Screenshots (OFFEN — vor Upload zu erstellen)
Der Store erwartet 1–5 Screenshots. Benötigt die laufende App:
1. **Konfigmaske** (Provider-Auswahl + Key) — ohne LLM-Key erreichbar, kann sofort erstellt werden.
2. **Chat mit Quellen-Badges** — braucht einen konfigurierten LLM-Key (echte Antwort + docs-Links).
Ablage: `screenshots/*.png` im Repo, im finalen `info.xml` als `<screenshot>`-URLs (raw.githubusercontent) referenzieren.

## Upload-Checkliste (nach Zertifikat-Merge)
1. Signiertes Release-Paket bauen (`info.xml` + Signatur mit `simosphere_ai_copilot_mini.key`).
2. App-ID-Signatur: `echo -n "simosphere_ai_copilot_mini" | openssl dgst -sha512 -sign <key> | openssl base64`.
3. Screenshots erzeugen + `<screenshot>`-Tags in `info.xml` ergänzen.
4. Auf apps.nextcloud.com hochladen (Stufe-1-Freigabe).
