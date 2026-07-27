"""Persistente Konfiguration des LLM-Zugangs (Bring-your-own-key).

Gespeichert wird im **persistenten App-Volume** (``nc_py_api.ex_app.persistent_storage``), das
Updates überdauert und nur der Instanz selbst zugänglich ist. Der Schlüssel steht in einer Datei
mit Rechten 600 und wird NIE nach aussen gegeben: ``public_status`` meldet nur, ob und welcher
Provider konfiguriert ist — nie den Key selbst.

Für lokale Tests/Entwicklung (ausserhalb einer ExApp) greift ein Fallback-Verzeichnis über
``COPILOT_MINI_STORAGE``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .llm import LLMConfig

_CONFIG_FILE = "llm_config.json"


def _store_dir() -> Path:
    try:
        from nc_py_api.ex_app import persistent_storage

        return Path(persistent_storage())
    except Exception:  # noqa: BLE001 — ausserhalb einer ExApp (Tests/Dev): Fallback
        return Path(os.environ.get("COPILOT_MINI_STORAGE", str(Path.home() / ".copilot_mini")))


def load() -> LLMConfig | None:
    """Lädt die gespeicherte Konfiguration, oder ``None`` wenn nichts (Gültiges) hinterlegt ist."""
    path = _store_dir() / _CONFIG_FILE
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    provider = str(data.get("provider") or "").strip().lower()
    if not provider:
        return None
    return LLMConfig(
        provider=provider,
        api_key=data.get("api_key") or None,
        base_url=data.get("base_url") or None,
        model=data.get("model") or None,
    )


def save(cfg: LLMConfig) -> None:
    """Schreibt die Konfiguration fail-safe mit Datei-Rechten 600 (Key nie im Log)."""
    directory = _store_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / _CONFIG_FILE
    payload = {
        "provider": cfg.provider,
        "api_key": cfg.api_key,
        "base_url": cfg.base_url,
        "model": cfg.model,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(path, 0o600)


def public_status() -> dict:
    """Nach aussen sichtbarer Status — OHNE den Schlüssel. Für die Konfig-Maske im Frontend."""
    cfg = load()
    if cfg is None:
        return {"configured": False}
    # Ollama braucht keinen Key; die anderen schon.
    ready = cfg.provider == "ollama" or bool(cfg.api_key)
    return {
        "configured": ready,
        "provider": cfg.provider,
        "model": cfg.resolved_model(),
        "base_url": cfg.base_url or "",
    }
