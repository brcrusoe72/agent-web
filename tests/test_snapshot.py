"""Snapshot engine against a real headless browser (Playwright required)."""

import pytest

playwright = pytest.importorskip("playwright.sync_api")

from agent_web.snapshot import ref_selector, take_snapshot

PAGE = """
<html><body>
<h1>Sign in</h1>
<nav><a href="/home">Home</a></nav>
<form>
  <input type="text" placeholder="Email">
  <input type="password" placeholder="Password">
  <button type="submit">Log in</button>
</form>
<input type="hidden" name="csrf" value="secret">
</body></html>
"""


@pytest.fixture(scope="module")
def page():
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pg = browser.new_page()
        pg.set_content(PAGE)
        yield pg
        browser.close()


def test_snapshot_lists_interactive_elements_with_refs(page):
    snap = take_snapshot(page)
    roles = [(e["role"], e["name"], e["ref"]) for e in snap["elements"]]
    assert ("heading", "Sign in", None) in roles
    assert any(r == "link" and n == "Home" for r, n, _ in roles)
    assert any(r == "button" and n == "Log in" for r, n, _ in roles)
    # Two textboxes (email, password) — hidden csrf input must be excluded.
    textboxes = [e for e in snap["elements"] if e["role"] == "textbox"]
    assert len(textboxes) == 2
    assert all(e["ref"] for e in snap["elements"] if e["role"] != "heading")


def test_refs_relocate_the_element(page):
    snap = take_snapshot(page)
    button = next(e for e in snap["elements"] if e["role"] == "button")
    # The ref selector must find exactly the element we stamped.
    assert page.inner_text(ref_selector(button["ref"])).strip() == "Log in"


def test_hidden_input_not_exposed(page):
    snap = take_snapshot(page)
    assert not any("secret" in (e["name"] or "") for e in snap["elements"])


@pytest.mark.parametrize('metadata', ['', 'name="password"', 'placeholder="Password"', 'aria-label="Password"'])
def test_password_value_never_becomes_snapshot_name(page, metadata):
    page.set_content(f'<input type="password" {metadata}>')
    page.locator('input').fill('SYNTHETIC-SECRET')
    snap = take_snapshot(page)
    assert len(snap['elements']) == 1
    assert 'SYNTHETIC-SECRET' not in str(snap)
    assert snap['elements'][0]['role'] == 'textbox'
    assert snap['elements'][0]['ref']
