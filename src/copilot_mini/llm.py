"""Bring-your-own-key-LLM-Client: OpenAI, Anthropic oder ein (lokaler) Ollama-Server.

Bewusst schlank und ohne Provider-SDKs — ein einziger ``httpx``-Client, zwei Wire-Formate:

* **openai-kompatibel** — deckt OpenAI *und* Ollama ab (Ollama bietet ``/v1/chat/completions``).
* **anthropic** — eigenes ``/v1/messages``-Format.

Der Schlüssel kommt vom Nutzer (siehe ``config``), wird nur im Authorization-Header mitgeschickt und
nie geloggt. Ausgehend wird ausschliesslich der vom Nutzer gewählte Provider angesprochen — es gibt
keinen SIMO-Endpunkt.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

_TIMEOUT = 60.0

#: Vorgabemodelle je Provider (überschreibbar über die Konfiguration).
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "ollama": "llama3.1",
}


class LLMError(RuntimeError):
    """Der Provider hat nicht wie erwartet geantwortet (Netz, Auth, Format)."""


class LLMNotConfigured(LLMError):
    """Es ist kein nutzbarer Provider konfiguriert."""


@dataclass(frozen=True)
class LLMConfig:
    provider: str  # "openai" | "anthropic" | "ollama"
    api_key: str | None = None
    base_url: str | None = None  # nur Ollama (z. B. http://localhost:11434)
    model: str | None = None

    def resolved_model(self) -> str:
        return self.model or DEFAULT_MODELS.get(self.provider, "")


async def generate(config: LLMConfig, system: str, user: str) -> str:
    """Erzeugt eine Antwort. Wirft ``LLMError`` bei Fehlkonfiguration oder Provider-Fehler."""
    provider = (config.provider or "").lower()
    if provider == "anthropic":
        return await _anthropic(config, system, user)
    if provider in ("openai", "ollama"):
        return await _openai_compatible(config, system, user)
    raise LLMNotConfigured(f"Unbekannter Provider: {provider!r}")


def _require_key(config: LLMConfig) -> str:
    if not config.api_key:
        raise LLMNotConfigured(f"Kein API-Key für {config.provider} hinterlegt.")
    return config.api_key


async def _openai_compatible(config: LLMConfig, system: str, user: str) -> str:
    if config.provider == "ollama":
        base = (config.base_url or "http://localhost:11434").rstrip("/")
        url = f"{base}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
    else:  # openai
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {_require_key(config)}", "Content-Type": "application/json"}
    payload = {
        "model": config.resolved_model(),
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.2,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            r = await client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise LLMError(f"{config.provider} nicht erreichbar: {type(exc).__name__}") from exc
    if r.status_code >= 400:
        raise LLMError(f"{config.provider} HTTP {r.status_code}")
    try:
        return r.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError) as exc:
        raise LLMError(f"Unerwartete {config.provider}-Antwort") from exc


async def _anthropic(config: LLMConfig, system: str, user: str) -> str:
    headers = {
        "x-api-key": _require_key(config),
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.resolved_model(),
        "max_tokens": 1024,
        "temperature": 0.2,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            r = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise LLMError(f"Anthropic nicht erreichbar: {type(exc).__name__}") from exc
    if r.status_code >= 400:
        raise LLMError(f"Anthropic HTTP {r.status_code}")
    try:
        blocks = r.json()["content"]
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
    except (KeyError, IndexError, ValueError) as exc:
        raise LLMError("Unerwartete Anthropic-Antwort") from exc
