"""Accessibility snapshot with element refs — the core value.

Instead of handing an LLM raw HTML or a screenshot, we return a compact list of
the page's interactive elements, each tagged with a stable ref (@e1, @e2, ...).
The agent reads the snapshot, then acts by ref ("click @e2"). Refs are real DOM
attributes we stamp on the elements, so re-locating a ref is exact, not a
fragile CSS guess.

This is a lighter-weight take on vercel-labs/agent-browser's snapshot+ref model:
Python + Playwright instead of a Rust/CDP daemon.
"""

from __future__ import annotations

# Injected into the page. Clears any prior refs, walks the DOM in document
# order, stamps each visible interactive element with data-agentweb-ref, and
# returns an ordered list of {ref, role, name}. Headings are included (ref=null)
# for context but are not actionable.
_SNAPSHOT_JS = r"""
() => {
  document.querySelectorAll('[data-agentweb-ref]')
    .forEach(e => e.removeAttribute('data-agentweb-ref'));

  const visible = (el) => {
    if (!el.getClientRects().length) return false;
    const s = getComputedStyle(el);
    return s.visibility !== 'hidden' && s.display !== 'none' && !el.hasAttribute('hidden');
  };

  const name = (el) => {
    let n = el.getAttribute('aria-label') || '';
    const lb = el.getAttribute('aria-labelledby');
    if (!n && lb) { const t = document.getElementById(lb); if (t) n = t.innerText || ''; }
    if (!n) n = el.getAttribute('placeholder') || '';
    if (!n && el.tagName === 'INPUT' && el.value) n = el.value;
    if (!n) n = el.getAttribute('alt') || '';
    if (!n) n = (el.innerText || el.textContent || '').trim();
    if (!n) n = el.getAttribute('title') || el.getAttribute('name') || '';
    return n.replace(/\s+/g, ' ').trim().slice(0, 120);
  };

  const role = (el) => {
    const r = el.getAttribute('role');
    if (r) return r;
    const tag = el.tagName.toLowerCase();
    if (tag === 'a') return 'link';
    if (tag === 'button') return 'button';
    if (tag === 'select') return 'combobox';
    if (tag === 'textarea') return 'textbox';
    if (tag === 'input') {
      const t = (el.getAttribute('type') || 'text').toLowerCase();
      if (['button', 'submit', 'reset'].includes(t)) return 'button';
      if (t === 'checkbox') return 'checkbox';
      if (t === 'radio') return 'radio';
      return 'textbox';
    }
    if (/^h[1-6]$/.test(tag)) return 'heading';
    return 'generic';
  };

  const interactive = 'a[href], button, input, select, textarea, ' +
    '[role=button], [role=link], [role=checkbox], [role=tab], [role=menuitem], ' +
    '[onclick], [contenteditable=""], [contenteditable=true]';

  const out = [];
  let n = 0;
  document.querySelectorAll('h1,h2,h3,h4,h5,h6,' + interactive).forEach(el => {
    if (!visible(el)) return;
    const rl = role(el);
    const nm = name(el);
    if (rl === 'heading') { if (nm) out.push({ref: null, role: 'heading', name: nm}); return; }
    if (el.tagName === 'INPUT' && (el.getAttribute('type') || '').toLowerCase() === 'hidden') return;
    n += 1;
    const ref = 'e' + n;
    el.setAttribute('data-agentweb-ref', ref);
    out.push({ref, role: rl, name: nm});
  });
  return out;
}
"""


def take_snapshot(page) -> dict:
    """Return {url, title, elements:[{ref, role, name}, ...]} for the page."""
    elements = page.evaluate(_SNAPSHOT_JS)
    return {"url": page.url, "title": page.title(), "elements": elements}


def ref_selector(ref: str) -> str:
    """CSS selector that re-locates a ref stamped by the last snapshot."""
    ref = ref.lstrip("@")
    return f'[data-agentweb-ref="{ref}"]'
