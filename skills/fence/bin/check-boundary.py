#!/usr/bin/env python3
"""PreToolUse guard: block edits outside the declared boundary.

Ported from gstack's check-freeze.sh, with one deliberate change. The original
allows the write when it cannot read a file path out of the payload -- it fails
OPEN, while its sibling command guard fails CLOSED. A boundary that yields to
an unreadable payload is not a boundary, so this one denies instead.

Boundary lives in .primeskills/boundary (repo-local, one absolute path per
line). No file, no boundary, everything allowed.
"""
import json
import os
import sys
from pathlib import Path

ALLOW = "{}"
BOUNDARY_FILE = Path(".primeskills/boundary")


def deny(reason):
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"[fence] {reason}",
        }
    })


def boundaries(root=None):
    path = (Path(root) / BOUNDARY_FILE) if root else BOUNDARY_FILE
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(os.path.realpath(os.path.expanduser(line)))
    return out


def decide(raw, root=None):
    allowed = boundaries(root)
    if not allowed:
        return ALLOW

    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        return deny("could not read the tool payload while a boundary is set.")

    target = (payload.get("tool_input") or {}).get("file_path")
    if target is None:
        return ALLOW  # not a file-writing call
    if not isinstance(target, str) or not target:
        return deny("a boundary is set and this call carries no readable path.")

    resolved = os.path.realpath(os.path.abspath(os.path.expanduser(target)))
    for base in allowed:
        if resolved == base or resolved.startswith(base.rstrip("/") + "/"):
            return ALLOW
    return deny(f"{resolved} is outside the boundary ({', '.join(allowed)}). "
                "Widen .primeskills/boundary or work inside it.")


if __name__ == "__main__":
    print(decide(sys.stdin.read()))
