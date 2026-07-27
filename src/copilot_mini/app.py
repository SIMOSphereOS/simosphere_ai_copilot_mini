"""FastAPI-Backend der ExApp — AppAPI-authentifiziert, self-contained.

Endpunkte:
* ``POST /api/chat``   — Frage -> lokales Retrieval -> geerdete Antwort mit Quellen.
* ``GET  /api/config`` — Status der LLM-Konfiguration (OHNE Key).
* ``POST /api/config`` — LLM-Zugang setzen (Provider + Key/Ollama-URL).
* ``GET  /``           — die Chat-Oberfläche (statisches Frontend).

Auth über ``AppAPIAuthMiddleware``: jeder Request wird gegen die AppAPI-Signatur des Nextcloud-
Servers geprüft; die Health-/Init-Routen registriert ``set_handlers``. Das Embedding-Modell wird
über ``models_to_fetch`` beim Aktivieren einmalig in den Offline-Cache geholt.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from nc_py_api import NextcloudApp
from nc_py_api.ex_app import AppAPIAuthMiddleware, nc_app, run_app, set_handlers
from pydantic import BaseModel, Field

from . import config as appconfig
from . import llm, rag
from .retrieval import Retriever

_APP_ID = "simosphere_ai_copilot_mini"
_DISPLAY = "SIMOSphere AI Copilot Mini"
_MODEL = "intfloat/multilingual-e5-large"

_STATIC = Path(__file__).resolve().parent / "static"


def _data_dir() -> Path:
    env = os.environ.get("COPILOT_MINI_DATA")
    return Path(env) if env else Path(__file__).resolve().parents[2] / "data"


_retriever: Retriever | None = None


def _get_retriever() -> Retriever:
    """Lädt Index + Embedding-Modell lazy (erst bei der ersten Frage)."""
    global _retriever
    if _retriever is None:
        _retriever = Retriever(_data_dir())
    return _retriever


def _enabled_handler(enabled: bool, nc: NextcloudApp) -> str:
    """Registriert/entfernt den Menü-Eintrag beim Aktivieren/Deaktivieren der App."""
    try:
        if enabled:
            nc.ui.resources.set_script("top_menu", _APP_ID, "js/main")
            nc.ui.top_menu.register(_APP_ID, _DISPLAY, "img/app.svg")
        else:
            nc.ui.top_menu.unregister(_APP_ID)
            nc.ui.resources.delete_script("top_menu", _APP_ID, "js/main")
    except Exception as exc:  # noqa: BLE001 — Fehlermeldung geht an AppAPI zurück, nicht als Crash
        return str(exc)
    return ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_handlers(app, _enabled_handler, models_to_fetch={_MODEL: {}})
    yield


APP = FastAPI(lifespan=lifespan)
APP.add_middleware(AppAPIAuthMiddleware)
if _STATIC.is_dir():
    APP.mount("/js", StaticFiles(directory=_STATIC / "js"), name="js")
    APP.mount("/css", StaticFiles(directory=_STATIC / "css"), name="css")
    APP.mount("/img", StaticFiles(directory=_STATIC / "img"), name="img")


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ConfigRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=16)
    api_key: str | None = Field(default=None, max_length=512)
    base_url: str | None = Field(default=None, max_length=256)
    model: str | None = Field(default=None, max_length=128)


@APP.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


@APP.post("/api/chat")
async def api_chat(req: ChatRequest, nc: NextcloudApp = Depends(nc_app)) -> JSONResponse:
    cfg = appconfig.load()
    if cfg is None:
        raise HTTPException(status_code=400, detail="LLM not configured")
    try:
        ans = await rag.answer(_get_retriever(), cfg, req.question)
    except llm.LLMNotConfigured as exc:
        raise HTTPException(status_code=400, detail="LLM not configured") from exc
    except llm.LLMError as exc:
        # Nur der Typ, nie die Provider-Rohmeldung (könnte den Key-Kontext tragen).
        raise HTTPException(status_code=502, detail="LLM provider error") from exc
    return JSONResponse(
        {
            "answer": ans.text,
            "grounded": ans.grounded,
            "sources": [{"title": s.title, "url": s.url} for s in ans.sources],
        }
    )


@APP.get("/api/config")
async def api_config_get(nc: NextcloudApp = Depends(nc_app)) -> JSONResponse:
    return JSONResponse(appconfig.public_status())


@APP.post("/api/config")
async def api_config_set(req: ConfigRequest, nc: NextcloudApp = Depends(nc_app)) -> JSONResponse:
    provider = req.provider.lower().strip()
    if provider not in ("openai", "anthropic", "ollama"):
        raise HTTPException(status_code=400, detail="unknown provider")
    appconfig.save(
        llm.LLMConfig(provider=provider, api_key=req.api_key, base_url=req.base_url, model=req.model)
    )
    return JSONResponse(appconfig.public_status())


if __name__ == "__main__":
    run_app("copilot_mini.app:APP", log_level="info")
