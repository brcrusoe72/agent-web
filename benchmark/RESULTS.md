# agent-web benchmark — results

## The number: 16× smaller than raw HTML

Across 15 real pages, the accessibility snapshot an agent consumes is a
**median 16× smaller than the page's raw HTML — about 6% of the tokens** —
while preserving every actionable element with a stable ref (**1,910** refs
across the set).

| what an LLM might be handed | median tokens (≈ chars/4) |
|---|---:|
| raw HTML (`page.content()`) | 29,726 |
| **agent-web snapshot** (`--json`) | **3,429** |
| **reduction** | **16× — snapshot ≈ 6.1% of raw HTML**, range 2×–640× |

## What the range means

The win scales with how bloated the page is:

- **Heavyweight JS pages** — NYT **96×**, Reddit **640×**, Google **159×**:
  megabytes of inline scripts and markup collapse to a few hundred tokens of
  actionable elements.
- **Minimalist pages** — Hacker News **2×**, example.com **2×**: little HTML to
  begin with, so little to strip. The snapshot still hands the agent clean refs
  to act on.

## Honest note: a snapshot is not a text summarizer

On link-dense pages the snapshot can be *larger than the page's visible text*
(MDN: a 32k-char snapshot vs. 8k-char body text), because it enumerates every
interactive element with role + name + ref — data that plain-text extraction
throws away. That's the point: the snapshot is the *interaction surface*, not a
reader. If you only want prose, `agent-web text` is smaller. The honest
comparison for "what does an agent need in order to *act* on this page" is
snapshot vs. raw HTML — and there the median is 16×.

## Why tokens ≈ chars/4 *understates* the win

Real BPE tokenizers (tiktoken et al.) spend extra tokens on HTML's `<`, `>`,
and `="…"` punctuation, so raw HTML runs *more* than chars/4 tokens-per-char
while the clean snapshot runs about chars/4. Measured with a real tokenizer the
reduction would be **larger**, not smaller — chars/4 is the conservative
estimate.

## Method

- 15 URLs, `example.com` → `amazon.com`, spanning docs, search engines, news,
  a code host, and SPA-heavy pages (`benchmark/run_benchmark.py`).
- Real Chromium (same launch as the daemon), `wait_until=domcontentloaded` plus
  1s for JS to paint actionables.
- Per page we measure `page.content()` (raw HTML), `inner_text('body')` (visible
  text), and `to_json(take_snapshot(page))` (exactly what `--json` returns).
  Tokens = chars / 4.
- Single run. Page weights drift with ads/experiments, so treat the ratios as
  order-of-magnitude, not to the digit.

## Reproduce

```bash
uv sync --extra dev
uv run playwright install chromium
python benchmark/run_benchmark.py
```
