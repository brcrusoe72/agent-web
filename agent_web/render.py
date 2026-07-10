"""Format a snapshot: compact ref-list for humans, JSON for agents."""

from __future__ import annotations

import json


def to_json(snap: dict) -> str:
    return json.dumps(snap, indent=2)


def to_terminal(snap: dict) -> str:
    if not snap.get("ok", True) and snap.get("error"):
        return f"[error: {snap['error']}]"
    lines = [f"# {snap.get('title') or '(untitled)'}", f"  {snap.get('url', '')}", ""]
    elements = snap.get("elements", [])
    if not elements:
        lines.append("(no interactive elements found)")
    for el in elements:
        if el["role"] == "heading":
            lines.append(f"\n[{el['name']}]")
        else:
            name = f' "{el["name"]}"' if el["name"] else ""
            lines.append(f"- {el['role']}{name} [@{el['ref']}]")
    n = sum(1 for e in elements if e.get("ref"))
    lines.append(f"\n{n} actionable element(s). Act by ref, e.g. `click @e1`.")
    return "\n".join(lines)
