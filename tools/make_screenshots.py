#!/usr/bin/env python3
"""Erzeugt Store-Screenshots des Copilot-Mini-Frontends — headless, ohne echtes Nextcloud.

Startet einen kleinen Mock-Server (liefert das echte static/-Frontend + gefakte /api/-Antworten)
und nimmt mit Playwright/Chromium zwei Ansichten auf:
  1) screenshots/01-configure.png  — die Bring-your-own-key-Konfigmaske
  2) screenshots/02-chat.png       — ein realistisches Chat-Beispiel mit Quellen-Badges

Aufruf: .venv/bin/python tools/make_screenshots.py
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "copilot_mini" / "static"
OUT = ROOT / "screenshots"

# Umschaltbarer Zustand: steuert, ob /api/config "konfiguriert" meldet (Config-Maske vs. Chat).
STATE = {"configured": False}

_MOCK_ANSWER = (
    "To put your Nextcloud into maintenance mode, run this occ command on the server:\n\n"
    "    sudo -u www-data php occ maintenance:mode --on\n\n"
    "This blocks user logins and shows a maintenance page while you upgrade or back up your "
    "instance. Turn it off again with `--off` when you are done. [1]"
)
_MOCK_SOURCES = [
    {
        "title": "Using the occ command",
        "url": "https://docs.nextcloud.com/server/33/admin_manual/occ_command.html",
    },
    {
        "title": "Maintenance mode",
        "url": "https://docs.nextcloud.com/server/33/admin_manual/maintenance/mode.html",
    },
]

_CTYPE = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        self._send(200, json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path.startswith("/__set/"):  # Test-Steuerung: /__set/configured/1
            STATE["configured"] = path.rsplit("/", 1)[-1] == "1"
            self._json({"ok": True})
            return
        if path == "/api/config":
            self._json({"configured": STATE["configured"], "provider": "openai", "model": "gpt-4o-mini"})
            return
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        f = STATIC / rel
        if f.is_file():
            self._send(200, f.read_bytes(), _CTYPE.get(f.suffix, "application/octet-stream"))
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        if path == "/api/config":
            STATE["configured"] = True
            self._json({"configured": True, "provider": "openai", "model": "gpt-4o-mini"})
        elif path == "/api/chat":
            self._json({"answer": _MOCK_ANSWER, "grounded": True, "sources": _MOCK_SOURCES})
        else:
            self._send(404, b"not found", "text/plain")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 820}, device_scale_factor=2)

        # 1) Konfigmaske
        page.goto(f"{base}/__set/configured/0")
        page.goto(base)
        page.wait_for_selector("#config:not([hidden])", timeout=8000)
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "01-configure.png"))
        print("geschrieben:", OUT / "01-configure.png")

        # 2) Chat mit Antwort + Quellen
        page.goto(f"{base}/__set/configured/1")
        page.goto(base)
        page.wait_for_selector("#chat:not([hidden])", timeout=8000)
        page.fill("#q", "How do I put my Nextcloud into maintenance mode?")
        page.click("#send")
        page.wait_for_selector(".sources a", timeout=8000)
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "02-chat.png"))
        print("geschrieben:", OUT / "02-chat.png")

        browser.close()
    srv.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
