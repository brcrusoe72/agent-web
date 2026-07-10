"""Render formatting — pure, no browser."""

from agent_web.render import to_terminal
from agent_web.snapshot import ref_selector

SNAP = {
    "ok": True, "url": "https://x.com", "title": "X",
    "elements": [
        {"ref": None, "role": "heading", "name": "Welcome"},
        {"ref": "e1", "role": "link", "name": "Home"},
        {"ref": "e2", "role": "button", "name": "Go"},
    ],
}


def test_terminal_lists_refs_and_counts_actionable():
    out = to_terminal(SNAP)
    assert "[@e1]" in out and "[@e2]" in out
    assert "[Welcome]" in out          # heading, no ref
    assert "2 actionable element(s)" in out


def test_error_snapshot_renders_error():
    assert "boom" in to_terminal({"ok": False, "error": "boom"})


def test_ref_selector_strips_at_sign():
    assert ref_selector("@e5") == ref_selector("e5") == '[data-agentweb-ref="e5"]'
