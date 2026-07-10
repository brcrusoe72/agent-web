"""CLI-side daemon control: ensure one is running, then send it commands."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

from .daemon import STATE_FILE

STARTUP_TIMEOUT = 30.0  # first launch has to boot Chromium


class DaemonError(RuntimeError):
    pass


def _base_url() -> str | None:
    if not STATE_FILE.exists():
        return None
    try:
        port = json.loads(STATE_FILE.read_text())["port"]
    except (json.JSONDecodeError, KeyError, OSError):
        return None
    return f"http://127.0.0.1:{port}"


def _request(base: str, path: str, body: dict | None, timeout: float) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        base + path, data=data, method="GET" if body is None else "POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _alive(base: str) -> bool:
    try:
        return _request(base, "/status", None, 3).get("ok", False)
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return False


def ensure_daemon() -> str:
    base = _base_url()
    if base and _alive(base):
        return base
    # Spawn a detached daemon and wait for it to publish a live port.
    subprocess.Popen(
        [sys.executable, "-m", "agent_web.daemon"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.time() + STARTUP_TIMEOUT
    while time.time() < deadline:
        time.sleep(0.4)
        base = _base_url()
        if base and _alive(base):
            return base
    raise DaemonError("browser daemon did not start in time")


def send(path: str, body: dict | None = None, timeout: float = 45.0) -> dict:
    # body is None → GET (e.g. /status); a dict (even empty) → POST.
    base = ensure_daemon()
    try:
        return _request(base, path, body, timeout)
    except urllib.error.URLError as exc:
        raise DaemonError(f"daemon request failed: {exc}") from exc


def stop() -> bool:
    """Stop the daemon if running. Returns True if one was stopped."""
    base = _base_url()
    if not base or not _alive(base):
        return False
    try:
        _request(base, "/stop", {}, 5)
    except (urllib.error.URLError, OSError):
        pass
    return True
