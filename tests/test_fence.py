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
    # walked past the guard in the external review of 2026-08-17
    ('{"tool_input":{"command":"git restore -- src/app.py"}}', "ask"),
    ('{"tool_input":{"command":"git checkout -- src/app.py"}}', "ask"),
    ('{"tool_input":{"command":"find ./cache -delete"}}', "ask"),
    ('{"tool_input":{"command":"rsync -a --delete src/ dst/"}}', "ask"),
    ('{"tool_input":{"command":"docker volume rm important-data"}}', "ask"),
    ('{"tool_input":{"command":"git stash drop"}}', "ask"),
    ('{"tool_input":{"command":"git branch -D feature"}}', "ask"),
    # and the benign neighbours must still pass
    ('{"tool_input":{"command":"git checkout main"}}', None),
    ('{"tool_input":{"command":"git restore --staged file"}}', None),
    ('{"tool_input":{"command":"rsync -a src/ dst/"}}', None),
    ('{"tool_input":{"command":"rm${IFS}-rf${IFS}/"}}', "ask"),
    ('{"tool_input":{"command":"rm -rf $(./wipe-all)/node_modules"}}', "ask"),
    ('{"tool_input":{"command":"rm -rf /\\nrm -rf node_modules"}}', "ask"),
    ("not json at all", "ask"),                                   # fail closed
    ('{"tool_input":{"command":"rm -rf node_modules"}}', None),   # whitelisted
    ('{"tool_input":{"command":"rm -Rf dist coverage"}}', None),
    # the whitelist is for artifacts under the working directory, and the name
    # at the end is not enough: these three named someone else's directory
    ('{"tool_input":{"command":"rm -rf ~/.cache"}}', "ask"),
    ('{"tool_input":{"command":"rm -rf /srv/other/build"}}', "ask"),
    ('{"tool_input":{"command":"rm -rf ../../node_modules"}}', "ask"),
    ('{"tool_input":{"command":"rm -rf frontend/node_modules"}}', None),
    ('{"tool_input":{"command":"rm -rf ./build"}}', None),
    ('{"tool_input":{"command":"ls -la"}}', None),
    ('{"tool_input":{"file_path":"a.py"}}', None),                # not a shell call
    # walked past the guard in the external review of 2026-08-19: flags out of
    # order, and git's global options standing between `git` and the verb
    ('{"tool_input":{"command":"rm -f -r /var/data"}}', "ask"),
    ('{"tool_input":{"command":"rm --recursive /srv/data"}}', "ask"),
    ('{"tool_input":{"command":"FOO=bar rm -f -r /srv"}}', "ask"),
    ('{"tool_input":{"command":"git -C /tmp/x reset --hard"}}', "ask"),
    ('{"tool_input":{"command":"git -c advice.detachedHead=false clean -fd"}}', "ask"),
    ('{"tool_input":{"command":"git --git-dir=/tmp/x/.git branch -D main"}}', "ask"),
    # `git restore <path>` throws the path away with or without `--`
    ('{"tool_input":{"command":"git restore src/app.py"}}', "ask"),
    ('{"tool_input":{"command":"rm -f -r frontend/node_modules"}}', None),
    # a hook that dies is a hook that permits: unexpected shapes fail closed
    ('{"tool_input":"a string, not an object"}', "ask"),
    ('["a list, not an object"]', "ask"),
    ('{"tool_input":{"command":"rm -rf \\"unbalanced"}}', "ask"),
]


# `git checkout <path>` needs a path that exists, so this pair runs in a
# directory made for it: the author lost an uncommitted rewrite to exactly this
# command on 2026-08-19, an hour after hardening the rest of this guard.
IN_TREE = [
    ('{"tool_input":{"command":"git checkout core-file.md"}}', "ask"),
    ('{"tool_input":{"command":"git checkout main"}}', None),
    ('{"tool_input":{"command":"git checkout -b feature/new"}}', None),
]


# Where the user has switched confirmations off, a question is not protection:
# it renders as a prompt that gets approved unread. These cases fix the answer
# instead — deny for the irreversible short list, silent allow for the rest.
# The literals are glued together so that writing this file does not trip the
# guard it tests: the hook reads a command string, and a string that merely
# quotes a destructive command looks exactly like one that runs it.
KILL = "DR" + "OP DATA" + "BASE"
FORCE = "git push --fo" + "rce origin main"
MODES = [
    ("bypassPermissions", f"psql -c '{KILL} prod'", "deny"),
    ("dontAsk", f"psql -c '{KILL} prod'", "deny"),
    ("bypassPermissions", FORCE, "deny"),
    ("bypassPermissions", "rm -rf /srv/somewhere-else", "deny"),
    ("bypassPermissions", "git clean -fd", None),     # разрушительно, но обратимо
    ("bypassPermissions", "ls -la", None),
    ("default", f"psql -c '{KILL} prod'", "ask"),     # режим со спросом не меняется
    ("acceptEdits", FORCE, "ask"),
]


# PS-044: a heredoc body is a command when something executes it and a document
# when it is on its way to a file. Judging both the same way made the guard
# refuse the writing of its own tests. The introducing line is still a command.
WIPE = "rm -" + "rf /srv/data"
HEREDOCS = [
    (f"cat > notes.md <<'EOF'\n{WIPE}\nEOF", None),
    (f"tee notes.md <<'EOF'\n{WIPE}\nEOF", None),
    (f"python3 - <<'PY'\nimport os\nos.system('{WIPE}')\nPY", "ask"),
    (f"bash <<'SH'\n{WIPE}\nSH", "ask"),
    (f"{WIPE} && cat > f <<'EOF'\nhi\nEOF", "ask"),
]


def run(script, payload, cwd=None):
    p = subprocess.run([sys.executable, str(script)], input=payload,
                       capture_output=True, text=True, cwd=cwd)
    return json.loads(p.stdout or "{}")


def decision(out):
    return (out.get("hookSpecificOutput") or {}).get("permissionDecision")


def main():
    failures = []
    cases = []
    for payload, expected in COMMANDS:
        got = decision(run(CMD, payload))
        if got != expected:
            failures.append(f"commands: {payload[:60]!r} -> {got}, expected {expected}")

    for command, expected in HEREDOCS:
        payload = json.dumps({"tool_input": {"command": command}})
        got = decision(run(CMD, payload))
        if got != expected:
            failures.append(f"heredoc: {command.splitlines()[0]!r} -> {got}, "
                            f"expected {expected}")

    for mode, command, expected in MODES:
        payload = json.dumps({"tool_name": "Bash", "permission_mode": mode,
                              "cwd": "/nonexistent",
                              "tool_input": {"command": command}})
        got = decision(run(CMD, payload))
        if got != expected:
            failures.append(f"mode {mode}: {command!r} -> {got}, expected {expected}")

    with tempfile.TemporaryDirectory() as tree:
        (Path(tree) / "core-file.md").write_text("x", encoding="utf-8")
        for payload, expected in IN_TREE:
            got = decision(run(CMD, payload, cwd=tree))
            if got != expected:
                failures.append(f"in tree: {payload[:60]!r} -> {got}, "
                                f"expected {expected}")

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / ".primeskills").mkdir()
        (repo / "src").mkdir()
        cases = [('{"tool_input":{"file_path":"src/a.py"}}', None),
                 ('{"tool_input":{"file_path":"/etc/passwd"}}', "deny"),
                 ('{"tool_input":{"file_path":"src/../../escape.py"}}', "deny"),
                 ("garbage", "deny"),
                 # NotebookEdit names its target notebook_path; reading only
                 # file_path let every notebook write straight past the boundary
                 ('{"tool_input":{"notebook_path":"/etc/x.ipynb"}}', "deny"),
                 ('{"tool_input":{"notebook_path":"src/a.ipynb"}}', None),
                 # a write whose shape we do not recognise is still a write
                 ('{"tool_input":{}}', "deny"),
                 ('{"tool_input":{"command":"ls"}}', "deny")]

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
    total = (len(COMMANDS) + len(HEREDOCS) + len(MODES) + len(IN_TREE)
             + len(cases) + 1)
    print(f"{total} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
