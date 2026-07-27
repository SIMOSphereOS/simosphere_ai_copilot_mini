# SIMOSphere AI Copilot Mini

[![CI](https://github.com/SIMOSphereOS/simosphere_ai_copilot_mini/actions/workflows/ci.yml/badge.svg)](https://github.com/SIMOSphereOS/simosphere_ai_copilot_mini/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

**Ask your Nextcloud documentation in natural language — right inside Nextcloud.**

Copilot Mini is a free, open-source Nextcloud app (built with AppAPI) that answers
questions about administering and using Nextcloud. It searches the official Nextcloud
manuals locally and lets a language model of *your* choice phrase the answer — every
response links back to the exact documentation page it came from.

- 🔍 **Local semantic search** over the Nextcloud admin, user and developer manuals
  (prebuilt, multilingual index — ask in German, get answers grounded in the English docs).
- 🔑 **Bring your own key** — use OpenAI, Anthropic or a local Ollama model. Nothing is
  sent to any SIMO server; the app is fully self-contained.
- 📎 **Sourced answers** — every reply cites the `docs.nextcloud.com` page it is based on.
- 🔒 **Privacy-first** — the knowledge base ships with the app; only your question and the
  retrieved documentation snippets go to the LLM provider *you* configured.

> Copilot Mini is the free little sibling of **SIMOSphere AI Copilot** — the full product
> that brings the same assistant to *your own* data: files, mail, ERP, compliance knowledge,
> roles and tools, all under your users' own Nextcloud identities.
> Learn more at [simo-online.com](https://www.simo-online.com).

## How it works

1. You ask a question in the chat.
2. The app embeds your question (multilingual e5) and searches a local FAISS index built
   from the Nextcloud documentation.
3. The top passages — with their source URLs — are handed to your configured LLM.
4. The model answers **only** from those passages and cites the sources.

No SIMO backend, no telemetry, no lock-in. The only outbound call is to the LLM provider
whose key you entered (or none at all, if you use a local Ollama).

## Configuration

Open the app and enter one of:

- an **OpenAI** API key, or
- an **Anthropic** API key, or
- the URL of a local/remote **Ollama** server.

The key is stored in Nextcloud's app configuration and never logged or shared.

## Knowledge base

The bundled index is derived from the official
[Nextcloud Documentation](https://github.com/nextcloud/documentation) (stable33) under
**CC BY 3.0** — see [`NOTICE`](NOTICE). Rebuild it for another version with
[`tools/rst_to_md.py`](tools/rst_to_md.py) + `tools/build_index.py`.

## License

[GNU AGPL v3.0](LICENSE). The bundled documentation content is CC BY 3.0 (see `NOTICE`).

*Not affiliated with Nextcloud GmbH.*
