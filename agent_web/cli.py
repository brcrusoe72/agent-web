"""agent-web — drive a real browser from the CLI, for AI agents.

    agent-web open https://example.com
    agent-web snapshot
    agent-web click @e2
    agent-web fill @e3 "hello@example.com"
    agent-web text
    agent-web stop

A persistent headless browser auto-starts on first command and holds state
(page, cookies, refs) between calls. Add --json to any command for agents.
Works against localhost too — verify your own dev server.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .client import DaemonError, send, stop
from .render import to_json, to_terminal


def main(argv: list[str] | None = None) -> int:
    # Strip --json positionally so an agent can put it anywhere
    # (`agent-web --json snapshot` or `agent-web snapshot --json`).
    argv = list(sys.argv[1:] if argv is None else argv)
    want_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]

    parser = argparse.ArgumentParser(
        prog="agent-web",
        description="Drive a real browser from the CLI. Snapshot pages as "
        "ref-tagged element lists; act by ref.",
    )
    parser.add_argument("--json", action="store_true", help="JSON output for agents (any position)")
    parser.add_argument("--version", action="version", version=f"agent-web {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_open = sub.add_parser("open", help="navigate to a URL")
    p_open.add_argument("url")
    sub.add_parser("snapshot", help="re-snapshot the current page")
    p_click = sub.add_parser("click", help="click an element by ref")
    p_click.add_argument("ref")
    p_fill = sub.add_parser("fill", help="type text into an element by ref")
    p_fill.add_argument("ref")
    p_fill.add_argument("text")
    p_nav = sub.add_parser("nav", help="back | forward | reload")
    p_nav.add_argument("action", choices=["back", "forward", "reload"])
    p_text = sub.add_parser("text", help="readable text of the current page")
    p_text.add_argument("--max-chars", type=int, default=15000)
    sub.add_parser("status", help="is the daemon up? what page?")
    sub.add_parser("stop", help="shut the browser daemon down")
    sub.add_parser("install", help="download the Chromium browser (one-time)")

    args = parser.parse_args(argv)
    args.json = want_json

    if args.command == "install":
        return _install()
    if args.command == "stop":
        print("stopped" if stop() else "no daemon running")
        return 0

    try:
        result = _dispatch(args)
    except DaemonError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not result.get("ok", True):
        print(to_json(result) if args.json else f"error: {result.get('error')}",
              file=sys.stderr)
        return 1

    if args.command == "text":
        print(to_json(result) if args.json else result.get("text", ""))
    elif args.command == "status":
        print(to_json(result) if args.json
              else f"daemon up — {result.get('title')} ({result.get('url')})")
    else:
        print(to_json(result) if args.json else to_terminal(result))
    return 0


def _install() -> int:
    import subprocess
    print("Downloading Chromium via Playwright...", file=sys.stderr)
    return subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"]).returncode


def _dispatch(args) -> dict:
    if args.command == "open":
        return send("/open", {"url": args.url})
    if args.command == "snapshot":
        return send("/snapshot", {})
    if args.command == "click":
        return send("/click", {"ref": args.ref})
    if args.command == "fill":
        return send("/fill", {"ref": args.ref, "text": args.text})
    if args.command == "nav":
        return send("/nav", {"action": args.action})
    if args.command == "text":
        return send("/text", {"max_chars": args.max_chars})
    if args.command == "status":
        return send("/status")
    raise DaemonError(f"unknown command {args.command}")


if __name__ == "__main__":
    sys.exit(main())
