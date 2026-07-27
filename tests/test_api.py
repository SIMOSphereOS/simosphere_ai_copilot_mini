"""Backend-Endpoint-Tests: die Handler-Logik von app.py direkt (ohne HTTP/Middleware — die
AppAPI-Auth ist nc_py_api-Code, nicht unserer). config, rag und retriever werden gemockt, damit
kein echtes Modell/LLM nötig ist. Alle Schlüsselwerte sind offensichtliche Test-Platzhalter."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import HTTPException

from copilot_mini import app as appmod
from copilot_mini import config as cfgmod
from copilot_mini import llm, rag

_DUMMY = "dummy-not-a-real-key"


def _body(resp) -> dict:
    return json.loads(resp.body)


def test_config_set_then_get_verbirgt_key(monkeypatch, tmp_path):
    monkeypatch.setenv("COPILOT_MINI_STORAGE", str(tmp_path))
    leak_marker = "must-not-leak-value"
    req = appmod.ConfigRequest(provider="openai", api_key=leak_marker, base_url=None, model="gpt-4o-mini")
    set_resp = _body(asyncio.run(appmod.api_config_set(req, nc=None)))
    assert set_resp["configured"] is True and set_resp["provider"] == "openai"
    get_resp = _body(asyncio.run(appmod.api_config_get(nc=None)))
    # Der Status verrät NIE den Schlüssel.
    assert get_resp["configured"] is True
    assert leak_marker not in json.dumps(get_resp) and "api_key" not in get_resp


def test_config_ollama_ohne_key_ist_konfiguriert(monkeypatch, tmp_path):
    monkeypatch.setenv("COPILOT_MINI_STORAGE", str(tmp_path))
    req = appmod.ConfigRequest(provider="ollama", api_key=None, base_url="http://localhost:11434", model=None)
    resp = _body(asyncio.run(appmod.api_config_set(req, nc=None)))
    assert resp["configured"] is True and resp["provider"] == "ollama"


def test_config_unbekannter_provider_400():
    req = appmod.ConfigRequest(provider="bogus")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(appmod.api_config_set(req, nc=None))
    assert exc.value.status_code == 400


def test_chat_ohne_konfiguration_400(monkeypatch, tmp_path):
    monkeypatch.setenv("COPILOT_MINI_STORAGE", str(tmp_path))  # leer -> load() == None
    with pytest.raises(HTTPException) as exc:
        asyncio.run(appmod.api_chat(appmod.ChatRequest(question="hi"), nc=None))
    assert exc.value.status_code == 400


def test_chat_ok_liefert_antwort_und_quellen(monkeypatch, tmp_path):
    monkeypatch.setenv("COPILOT_MINI_STORAGE", str(tmp_path))
    cfgmod.save(llm.LLMConfig(provider="openai", api_key=_DUMMY))
    monkeypatch.setattr(appmod, "_get_retriever", lambda: object())

    async def fake_answer(retriever, config, question):
        return rag.Answer(
            text="Use occ maintenance:mode --on.",
            sources=[
                rag.Source(
                    title="occ",
                    url="https://docs.nextcloud.com/server/33/admin_manual/occ_command.html",
                )
            ],
            grounded=True,
        )

    monkeypatch.setattr(appmod.rag, "answer", fake_answer)
    resp = _body(asyncio.run(appmod.api_chat(appmod.ChatRequest(question="maintenance mode?"), nc=None)))
    assert resp["grounded"] is True
    assert "occ maintenance:mode" in resp["answer"]
    assert resp["sources"][0]["url"].startswith("https://docs.nextcloud.com/")


def test_chat_llm_fehler_502(monkeypatch, tmp_path):
    monkeypatch.setenv("COPILOT_MINI_STORAGE", str(tmp_path))
    cfgmod.save(llm.LLMConfig(provider="openai", api_key=_DUMMY))
    monkeypatch.setattr(appmod, "_get_retriever", lambda: object())

    async def boom(retriever, config, question):
        raise llm.LLMError("provider down")

    monkeypatch.setattr(appmod.rag, "answer", boom)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(appmod.api_chat(appmod.ChatRequest(question="x"), nc=None))
    assert exc.value.status_code == 502
