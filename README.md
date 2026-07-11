# agent-web

Drive a real browser from the CLI, for AI agents. Snapshot a page as a compact
list of ref-tagged elements, then act by ref. Playwright-backed — no Rust, no
cloud, no API key.

```bash
uv tool install agent-web
agent-web install          # one-time: downloads Chromium
agent-web open https://example.com
```

```
# Example Domain
  https://example.com/

- link "More information..." [@e1]

1 actionable element(s). Act by ref, e.g. `click @e1`.
```

Then act by ref, and get a fresh snapshot back each time:

```bash
agent-web click @e1
agent-web fill @e3 "hello@example.com"
agent-web text                 # readable page text
agent-web --json snapshot      # structured, for agents
agent-web stop                 # shut the browser down
```

## Why

Handing an LLM raw HTML or a screenshot burns thousands of tokens per page.
`agent-web` returns just the interactive elements, each with a stable ref
(`@e1`, `@e2`) that maps to a real DOM attribute — so `click @e2` is exact, not
a fragile CSS guess. It's a lighter-weight take on the snapshot+ref model from
[vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser):
Python + Playwright instead of a Rust/CDP daemon.

## The number

Across 15 real pages, the snapshot an agent consumes is a **median 16× smaller
than the page's raw HTML — about 6% of the tokens** — while preserving every
actionable element with a stable ref (1,910 across the set). The win scales with
page bloat: 640× on Reddit, 96× on nytimes.com, 2× on minimalist Hacker News.
It's not a text summarizer — on link-heavy pages the snapshot can exceed the
visible *text*, because it keeps every ref plain-text extraction discards; the
honest comparison for *acting* on a page is snapshot vs. raw HTML.
[Full results + method](benchmark/RESULTS.md).

## How it works

A headless browser auto-starts on your first command and **persists** — page,
cookies, and refs survive between CLI calls, so each call is cheap. It shuts
down after 5 minutes idle (`AGENT_WEB_IDLE_TIMEOUT` to change), or `agent-web
stop`. Set `AGENT_WEB_HEADED=1` to watch it work.

## Commands

| Command | Does |
|---|---|
| `open <url>` | navigate; returns a snapshot |
| `snapshot` | re-snapshot the current page |
| `click <ref>` | click element by ref; returns a fresh snapshot |
| `fill <ref> <text>` | type into an element by ref |
| `nav back\|forward\|reload` | history / reload |
| `text` | readable text of the current page |
| `status` | is the daemon up? what page? |
| `stop` | shut the browser down |

`--json` on any command gives agent-friendly structured output.

## Non-goals

- **No search / no reading pipeline.** For turning a URL into clean text
  (paywalls, PDFs, 403s), use a reader; this tool is for *interaction*.
- **No cloud browsers, no captcha solving, no stealth.** Local Chromium only.
- **Not a test framework.** No assertions or runner — it's the hands, the
  agent is the brain.

## Localhost is allowed

Unlike a fetch tool, `agent-web` deliberately does **not** block localhost or
private IPs — the whole point is to let an agent open and verify its own dev
server. Only point it at pages you trust.

## Development

```bash
uv sync --extra dev
uv run playwright install chromium
uv run pytest
```

## License

MIT
