"""The browser daemon — one persistent Playwright browser, served over a local
HTTP socket so each CLI call is cheap.

Single-threaded on purpose: Playwright's sync API is thread-affine, and one
agent driving one browser wants its actions serialized anyway. Requests are
handled in the same thread that owns the browser. An idle watchdog shuts the
daemon down after inactivity so we don't leak a Chromium.
"""

from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .snapshot import ref_selector, take_snapshot

STATE_DIR = Path.home() / ".agent-web"
STATE_FILE = STATE_DIR / "state.json"
IDLE_TIMEOUT = float(os.environ.get("AGENT_WEB_IDLE_TIMEOUT", "300"))
ACTION_TIMEOUT = 15_000  # ms


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silence default stderr logging
        pass

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        return json.loads(self.rfile.read(length) or b"{}")

    def _send(self, payload: dict, status: int = 200):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.server.touch()
        if self.path == "/status":
            page = self.server.page
            self._send({"ok": True, "url": page.url, "title": page.title()})
        else:
            self._send({"ok": False, "error": "unknown endpoint"}, 404)

    def do_POST(self):
        self.server.touch()
        try:
            if self.path == "/stop":
                self._send({"ok": True, "stopped": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            result = self.server.dispatch(self.path, self._body())
            self._send(result)
        except Exception as exc:  # never crash the daemon on one bad request
            self._send({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 200)


class BrowserServer(HTTPServer):
    def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=not os.environ.get("AGENT_WEB_HEADED")
        )
        self._context = self._browser.new_context()
        self.page = self._context.new_page()
        self.page.set_default_timeout(ACTION_TIMEOUT)
        self._last = time.time()

    def touch(self):
        self._last = time.time()

    def dispatch(self, path: str, body: dict) -> dict:
        page = self.page
        if path == "/open":
            page.goto(body["url"], wait_until="domcontentloaded")
        elif path == "/snapshot":
            pass
        elif path == "/click":
            page.click(ref_selector(body["ref"]))
            self._settle()
        elif path == "/fill":
            page.fill(ref_selector(body["ref"]), body.get("text", ""))
        elif path == "/nav":
            action = body.get("action", "reload")
            {"back": page.go_back, "forward": page.go_forward,
             "reload": page.reload}[action]()
        elif path == "/text":
            return {"ok": True, "url": page.url, "title": page.title(),
                    "text": page.inner_text("body")[: body.get("max_chars", 15000)]}
        else:
            return {"ok": False, "error": f"unknown endpoint {path}"}
        snap = take_snapshot(page)
        snap["ok"] = True
        return snap

    def _settle(self):
        # After a click the page may navigate or re-render; give it a beat but
        # don't hang if it never goes idle.
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

    def cleanup(self):
        for close in (self._context.close, self._browser.close, self._pw.stop):
            try:
                close()
            except Exception:
                pass

    def idle_seconds(self) -> float:
        return time.time() - self._last


def main():
    STATE_DIR.mkdir(exist_ok=True)
    server = BrowserServer()
    port = server.server_address[1]
    STATE_FILE.write_text(json.dumps({"port": port, "pid": os.getpid()}))

    def watchdog():
        while True:
            time.sleep(5)
            if server.idle_seconds() > IDLE_TIMEOUT:
                server.shutdown()
                return

    threading.Thread(target=watchdog, daemon=True).start()
    try:
        server.serve_forever()
    finally:
        server.cleanup()
        try:
            STATE_FILE.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
