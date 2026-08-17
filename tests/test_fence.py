#!/usr/bin/env python3
"""The guards must block what they claim to block."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CMD = ROOT / "skills" / "fence" / "bin" / "check-commands.py"
BND = ROOT / "skills" / "fence" / "bin" / "check-boundary.py"

# (payload, expected decision or None for allow)
COMMANDS = [
    ('{"tool_input":{"command":"rm -rf /var/data"}}', "ask"),
    ('{"tool_input":{"command":"git commit -m \\"wip\\" && rm -rf /"}}', "ask"),
    ('{"tool_input":{"command":"psql -c \'DROP DATABASE prod\'"}}', "ask"),
    ('{"tool_input":{"command":"dropdb ledger_staging"}}', "ask"),
    ('{"tool_input":{"command":"python manage.py flush"}}', "ask"),
    ('{"tool_input":{"command":"git push --force origin main"}}', "ask"),
    ('{"tool_input":{"command":"git clean -fd"}}', "ask"),
    ('{"tool_input":{"command":"killall python"}}', "ask"),
    ('{"tool_input":{"command":"rm${IFS}-rf${IFS}/"}}', "ask"),
    ('{"tool_input":{"command":"rm -rf $(./wipe-all)/node_modules"}}', "ask"),
    ('{"tool_input":{"command":"rm -rf /\\nrm -rf node_modules"}}', "ask"),
    ("not json at all", "ask"),                                   # fail closed
    ('{"tool_input":{"command":"rm -rf node_modules"}}', None),   # whitelisted
    ('{"tool_input":{"command":"rm -Rf dist coverage"}}', None),
    ('{"tool_input":{"command":"ls -la"}}', None),
    ('{"tool_input":{"file_path":"a.py"}}', None),                # not a shell call
]


def run(script, payload, cwd=None):
    p = subprocess.run([sys.executable, str(script)], input=payload,
                       capture_output=True, text=True, cwd=cwd)
    return json.loads(p.stdout or "{}")


def decision(out):
    return (out.get("hookSpecificOutput") or {}).get("permissionDecision")


def main():
    failures = []
    for payload, expected in COMMANDS:
        got = decision(run(CMD, payload))
        if got != expected:
            failures.append(f"commands: {payload[:60]!r} -> {got}, expected {expected}")

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / ".primeskills").mkdir()
        (repo / "src").mkdir()
        cases = [('{"tool_input":{"file_path":"src/a.py"}}', None),
                 ('{"tool_input":{"file_path":"/etc/passwd"}}', "deny"),
                 ('{"tool_input":{"file_path":"src/../../escape.py"}}', "deny"),
                 ("garbage", "deny"),
                 ('{"tool_input":{"command":"ls"}}', None)]

        # no boundary file: everything allowed
        if decision(run(BND, '{"tool_input":{"file_path":"/etc/passwd"}}', cwd=repo)) is not None:
            failures.append("boundary: blocked with no boundary file set")

        (repo / ".primeskills" / "boundary").write_text(str(repo / "src") + "\n")
        for payload, expected in cases:
            got = decision(run(BND, payload, cwd=repo))
            if got != expected:
                failures.append(f"boundary: {payload[:50]!r} -> {got}, expected {expected}")

    for f in failures:
        print(f)
    total = len(COMMANDS) + 6
    print(f"{total} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
