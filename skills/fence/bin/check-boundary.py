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
import subprocess
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


def repo_root():
    """The boundary belongs to the repository, not to whatever directory the
    hook happened to start in. Resolving it relative to cwd meant a call made
    from a subdirectory found no file, and no file means everything allowed --
    the boundary disappeared exactly when the work went one level deep."""
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def boundaries(root=None):
    base = Path(root) if root else repo_root()
    path = (base / BOUNDARY_FILE) if base else BOUNDARY_FILE
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

    # NotebookEdit sends notebook_path, not file_path. Reading only the latter
    # let every notebook write past a boundary that claims to hold this tool:
    # the value came back None and None was answered with ALLOW, which is the
    # fail-open behaviour this file was ported to remove.
    fields = payload.get("tool_input") or {}
    target = next((fields[k] for k in ("file_path", "notebook_path", "path")
                   if isinstance(fields.get(k), str) and fields[k]), None)
    if not target:
        # The matcher fires on Edit|Write|NotebookEdit only, so a call with no
        # path is a shape we do not understand -- and an unrecognised write is
        # exactly what a boundary must refuse.
        return deny("a boundary is set and this call carries no readable path.")

    resolved = os.path.realpath(os.path.abspath(os.path.expanduser(target)))
    for base in allowed:
        if resolved == base or resolved.startswith(base.rstrip("/") + "/"):
            return ALLOW
    return deny(f"{resolved} is outside the boundary ({', '.join(allowed)}). "
                "Widen .primeskills/boundary or work inside it.")


if __name__ == "__main__":
    print(decide(sys.stdin.read()))
