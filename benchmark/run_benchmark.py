#!/usr/bin/env python3
"""The number for agent-web: how much smaller is the accessibility snapshot an
agent consumes than the raw HTML it replaces — and does it keep the parts that
matter (the actionable elements, each with a stable ref)?

    python benchmark/run_benchmark.py

For each real page we load a real Chromium (same as the daemon) and measure
three things an LLM might be handed:
  * raw HTML          — page.content()          (what a naive scrape sends)
  * visible text      — inner_text('body')       (a readable-text reader)
  * agent-web snapshot — take_snapshot(page) as the --json an agent consumes

Tokens are estimated at chars / 4 — the standard rough rule. This *understates*
the win: real tokenizers spend extra tokens on HTML's angle brackets, quotes,
and attributes, so raw HTML costs more tokens-per-char than clean text does.
"""
from __future__ import annotations

import statistics
import sys

sys.path.insert(0, __file__.rsplit("/", 2)[0])
from agent_web.render import to_json  # noqa: E402
from agent_web.snapshot import take_snapshot  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

URLS = [
    "https://example.com",
    "https://en.wikipedia.org/wiki/Overall_equipment_effectiveness",
    "https://www.google.com",
    "https://news.ycombinator.com",
    "https://github.com/vercel-labs/agent-browser",
    "https://duckduckgo.com/",
    "https://www.python.org/",
    "https://developer.mozilla.org/en-US/docs/Web/HTML",
    "https://www.wikipedia.org/",
    "https://arxiv.org/abs/1706.03762",
    "https://stackoverflow.com/questions",
    "https://www.bbc.com/news",
    "https://www.nytimes.com/",
    "https://www.reddit.com/",
    "https://www.amazon.com/",
]

TOK = 4  # chars per token, rough


def tok(chars: int) -> int:
    return round(chars / TOK)


def main() -> int:
    rows = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.set_default_timeout(25_000)
        for url in URLS:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=25_000)
                page.wait_for_timeout(1000)  # let JS paint actionables
                html = page.content()
                text = page.inner_text("body")
                snap = take_snapshot(page)
                snap_json = to_json(snap)
                actionable = sum(1 for e in snap["elements"] if e.get("ref"))
                rows.append({
                    "url": url,
                    "html": len(html), "text": len(text), "snap": len(snap_json),
                    "acts": actionable,
                })
            except Exception as exc:
                rows.append({"url": url, "err": f"{type(exc).__name__}"})
        browser.close()

    ok = [r for r in rows if "err" not in r]

    print(f"\n=== agent-web benchmark — {len(ok)}/{len(rows)} pages loaded ===\n")
    hdr = (f"{'raw HTML':>10} {'text':>9} {'snapshot':>9} "
           f"{'HTML tok':>9} {'snap tok':>9} {'reduce':>7} {'acts':>5}  url")
    print(hdr)
    for r in rows:
        if "err" in r:
            print(f"{'(load failed: ' + r['err'] + ')':>62}  {r['url']}")
            continue
        red = r["html"] / r["snap"]
        print(f"{r['html']:>10} {r['text']:>9} {r['snap']:>9} "
              f"{tok(r['html']):>9} {tok(r['snap']):>9} {red:>6.0f}x {r['acts']:>5}  {r['url']}")

    if not ok:
        print("\nno pages loaded")
        return 1

    reductions = sorted(r["html"] / r["snap"] for r in ok)
    html_toks = [tok(r["html"]) for r in ok]
    snap_toks = [tok(r["snap"]) for r in ok]
    snap_pct = [100 * r["snap"] / r["html"] for r in ok]

    print(f"\nmedian raw-HTML tokens : {int(statistics.median(html_toks)):>7,}")
    print(f"median snapshot tokens : {int(statistics.median(snap_toks)):>7,}")
    print(f"median reduction       : {statistics.median(reductions):>6.0f}x  "
          f"(snapshot ≈ {statistics.median(snap_pct):.1f}% of raw-HTML tokens)")
    print(f"reduction range        : {reductions[0]:.0f}x – {reductions[-1]:.0f}x")
    print(f"total actionable refs preserved across pages: "
          f"{sum(r['acts'] for r in ok)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
