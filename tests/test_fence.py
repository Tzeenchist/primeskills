#!/usr/bin/env python3
"""The guards must block what they claim to block."""
import json
import os
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
    ("default", "printf x > /etc/hosts", "ask"),
    ("bypassPermissions", "printf x > /etc/hosts", None),
]


# A separator inside quotes is text, not a separator. Cutting there left
# fragments with unbalanced quotes, and the guard answered `ask` to `awk -F"|"`
# and to every `sed -n "$(... | ...)"` -- in a mode with confirmations off, the
# one answer that stops the work.
QUOTED = [
    ('grep -n "foo" f.py | head', None),
    ("""sed -n "$(grep -n 'X = ' f.py | cut -d: -f1),+12p" f.py""", None),
    ('echo "a | b"', None),
    ('git log --format="%h | %s" | head -5', None),
    ('awk -F"|" \'{print $1}\' file.txt', None),
    ('python3 -c "print(1 | 2)"', None),
    ('find . -name "*.py" -exec grep -l "x" {} \\;', None),
    ('psql -c "SELECT 1 WHERE name = \'a|b\'"', None),
    # and a separator outside quotes still separates
    ('ls -la; ' + "rm -" + "rf /srv/data", "ask"),
    ('echo hi | ' + "dropd" + "b ledger", "ask"),
]


# An unparseable line in a silent mode is decided, not handed back as a
# question: judged by its text, refused where the text names a recursive
# delete, and journalled where it does not.
UNREADABLE = [
    ("default", 'echo "unbalanced', "ask"),
    ("bypassPermissions", 'echo "unbalanced', None),
    ("bypassPermissions", "rm -" + "rf \"unbalanced", "deny"),
    # a catastrophic command inside a line nobody could tokenise keeps its rung
    ("bypassPermissions", "psql -c \"DR" + "OP DATA" + "BASE prod", "deny"),
]


# PS-044: a heredoc body is a command when something executes it and a document
# when it is on its way to a file. Judging both the same way made the guard
# refuse the writing of its own tests. The introducing line is still a command.
WIPE = "rm -" + "rf /srv/data"
HEREDOCS = [
    (f"cat > notes.md <<'EOF'\n{WIPE}\nEOF", None),
    (f"tee notes.md <<'EOF'\n{WIPE}\nEOF", None),
    ("cat > /etc/passwd <<'EOF'\nreplacement\nEOF", "ask"),
    (f"python3 - <<'PY'\nimport os\nos.system('{WIPE}')\nPY", "ask"),
    (f"bash <<'SH'\n{WIPE}\nSH", "ask"),
    (f"{WIPE} && cat > f <<'EOF'\nhi\nEOF", "ask"),
]


# Output redirection is judged by its destination. Writing outside the session
# tree needs a decision; descriptor plumbing, sinks, temporary files, and
# destinations inside the tree do not.
REDIRECTS = [
    ("cat > /etc/passwd", "ask"),
    ("echo key >> ~/.ssh/authorized_keys", "ask"),
    ("printf '' >/etc/hosts", "ask"),
    ("printf x >| /etc/hosts", "ask"),
    ("printf x > '/etc/a file'", "ask"),
    ("printf x 2>/dev/null", None),
    ("printf x 1>&2", None),
    ("printf x >&2", None),
    ("printf x 2>&1", None),
    ("printf x >/dev/null 2>&1", None),
    ("printf x > /tmp/fence-output", None),
    ("printf x > notes.md", None),
    ("printf x | tee /etc/hosts", "ask"),
    ("printf x | tee -a notes.md", None),
    ("printf x | tee /dev/null", None),
]


# A rungless verdict passes silently where confirmations are off, so a rule
# without a rung must never answer for a rule that has one. The redirect check
# is the first rungless rule that can match a destructive line, and checked
# first it let `rm -rf` through by the simple trick of appending a redirect.
SHADOWED = [
    ("bypassPermissions", WIPE, "deny"),
    ("bypassPermissions", f"{WIPE} > /etc/hosts", "deny"),
    ("bypassPermissions", f"{WIPE} > out.txt", "deny"),
    ("default", f"{WIPE} > /etc/hosts", "ask"),
]


# PS-041: on Claude Code the Bash hook is the gate for authority, not merely a
# place where the agent records what it chose to do. These are the RUNGS whose
# commands have one unambiguous spelling. Reading neighbours stay outside the
# gate: inspecting git or a pull request changes nothing.
AUTHORITY = [
    ("git push origin work", "push", ("push", "ветка work")),
    ("gh pr create --title x --body y", "pr", ("pr", "PR из work")),
    ("git merge feature", "merge", ("merge", "feature в work")),
    ("kubectl apply -f staging/deploy.yaml", "deploy",
     ("deploy", "--target", "staging", "выкатить в staging")),
]
READ_ONLY = ["git status", "git log -1", "git diff", "gh pr view 12",
             "gh run list"]


def run(script, payload, cwd=None, env=None):
    p = subprocess.run([sys.executable, str(script)], input=payload,
                       capture_output=True, text=True, cwd=cwd, env=env)
    return json.loads(p.stdout or "{}")


def decision(out):
    return (out.get("hookSpecificOutput") or {}).get("permissionDecision")


def reason(out):
    return (out.get("hookSpecificOutput") or {}).get("permissionDecisionReason", "")


def main():
    failures = []
    cases = []
    authority_checks = 0
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

    with tempfile.TemporaryDirectory() as tree:
        redirects = REDIRECTS + [(f"printf x > {tree}/absolute.txt", None)]
        for command, expected in redirects:
            payload = json.dumps({"cwd": tree, "tool_input": {"command": command}})
            got = decision(run(CMD, payload, cwd=tree))
            if got != expected:
                failures.append(f"redirect: {command!r} -> {got}, expected {expected}")

    for mode, command, expected in SHADOWED:
        payload = json.dumps({"tool_name": "Bash", "permission_mode": mode,
                              "tool_input": {"command": command}})
        got = decision(run(CMD, payload))
        if got != expected:
            failures.append(f"shadowed: {mode} {command!r} -> {got}, "
                            f"expected {expected}")

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "work"], cwd=repo,
                       check=True)
        (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "add", "seed.txt"], cwd=repo, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-q", "-m", "init"], cwd=repo, check=True)
        env = os.environ.copy()
        env["PATH"] = str(ROOT / "bin") + os.pathsep + env.get("PATH", "")

        for command, rung, _grant in AUTHORITY:
            payload = json.dumps({"tool_name": "Bash", "permission_mode": "default",
                                  "cwd": str(repo),
                                  "tool_input": {"command": command}})
            out = run(CMD, payload, cwd=repo, env=env)
            authority_checks += 1
            if decision(out) != "ask" or f"primeskills-run grant {rung}" not in reason(out):
                failures.append(f"authority closed+ask: {command!r} -> {out}")

            payload = json.dumps({"tool_name": "Bash",
                                  "permission_mode": "bypassPermissions",
                                  "cwd": str(repo),
                                  "tool_input": {"command": command}})
            got = decision(run(CMD, payload, cwd=repo, env=env))
            authority_checks += 1
            if got != "deny":
                failures.append(f"authority closed+deny: {command!r} -> {got}")

        # A global option sits between the program and its subcommand. `git -C
        # x push` was already normalised; `gh --repo o/r pr create` walked
        # straight past the pr rung until `gh` got the same treatment. Checked
        # here, inside the disposable repository and while the rungs are still
        # closed: run against the developer's own journal these read `allow`,
        # because the developer has push open — a test whose verdict depends on
        # that is not a test.
        for command, expected in [
                ("git -C /srv/x push origin master", "ask"),
                ("git -c user.name=x push", "ask"),
                ("gh --repo owner/repo pr create --fill", "ask"),
                ("gh -R owner/repo pr create --fill", "ask"),
                ("gh --repo owner/repo pr view 1", None)]:
            payload = json.dumps({"tool_name": "Bash", "permission_mode": "default",
                                  "cwd": str(repo),
                                  "tool_input": {"command": command}})
            got = decision(run(CMD, payload, cwd=repo, env=env))
            authority_checks += 1
            if got != expected:
                failures.append(f"глобальная опция: {command!r} -> {got}, "
                                f"ожидалось {expected}")

        for command, rung, grant in AUTHORITY:
            p = subprocess.run([sys.executable, str(ROOT / "bin" / "primeskills-run"),
                                "grant", *grant], cwd=repo, env=env,
                               capture_output=True, text=True)
            authority_checks += 1
            if p.returncode != 0:
                failures.append(f"authority grant {rung}: {p.stdout}{p.stderr}")
                continue
            for mode in ("default", "bypassPermissions"):
                payload = json.dumps({"tool_name": "Bash", "permission_mode": mode,
                                      "cwd": str(repo),
                                      "tool_input": {"command": command}})
                got = decision(run(CMD, payload, cwd=repo, env=env))
                authority_checks += 1
                if got is not None:
                    failures.append(f"authority open: {mode} {command!r} -> {got}")

        # The hook is handed the session's directory, not the one the command
        # acts on. Asked from outside a repository the ladder answers "not
        # inside a git repository", which is a non-zero code and therefore a
        # refusal — with the rung open the whole time. Both ways of naming the
        # repository on the line must find its journal. This is the failure the
        # rule shipped with: the author's own push was refused twice.
        outside = Path(tmp) / "elsewhere"
        outside.mkdir()
        for command, expected in [
                (f"cd {repo} && git push origin work", None),
                (f"git -C {repo} push origin work", None),
                ("git push origin work", "deny")]:
            payload = json.dumps({"tool_name": "Bash",
                                  "permission_mode": "bypassPermissions",
                                  "cwd": str(outside),
                                  "tool_input": {"command": command}})
            got = decision(run(CMD, payload, cwd=outside, env=env))
            authority_checks += 1
            if got != expected:
                failures.append(f"журнал не там: {command!r} -> {got}, "
                                f"ожидалось {expected}")

        shadowed_authority = [
            ("git push origin work && rm -rf /srv/data", "bypassPermissions",
             "deny", None),
            ("git push origin work && dropdb prod", "bypassPermissions",
             "deny", None),
            ("git push origin work && git restore seed.txt", "default", "ask",
             "discards uncommitted changes"),
            ("git push --force origin work", "default", "ask",
             "rewrites history others may already have"),
        ]
        for command, mode, expected, reason_part in shadowed_authority:
            payload = json.dumps({"tool_name": "Bash", "permission_mode": mode,
                                  "cwd": str(repo),
                                  "tool_input": {"command": command}})
            out = run(CMD, payload, cwd=repo, env=env)
            authority_checks += 1
            if (decision(out) != expected
                    or (reason_part and reason_part not in reason(out))):
                failures.append(f"authority shadowed: {command!r} -> {out}")

        # deploy is single-use. Seeing it twice through the hook proves that
        # the gate peeks instead of spending the user's one permitted action.
        deploy = AUTHORITY[-1][0]
        payload = json.dumps({"tool_name": "Bash", "permission_mode": "default",
                              "cwd": str(repo), "tool_input": {"command": deploy}})
        got = decision(run(CMD, payload, cwd=repo, env=env))
        authority_checks += 1
        if got is not None:
            failures.append(f"authority deploy mandate was spent by peek: {got}")

        for command in READ_ONLY:
            payload = json.dumps({"tool_name": "Bash", "permission_mode": "default",
                                  "cwd": str(repo),
                                  "tool_input": {"command": command}})
            got = decision(run(CMD, payload, cwd=repo, env=env))
            authority_checks += 1
            if got is not None:
                failures.append(f"authority read-only: {command!r} -> {got}")

        records = list((repo / ".primeskills" / "run").glob("work-*.jsonl"))
        journal = records[0].read_text(encoding="utf-8") if records else ""
        for _command, rung, _grant in AUTHORITY:
            authority_checks += 1
            if f"allowed under an open {rung}" not in journal:
                failures.append(f"authority journal: no allowed {rung} line")

    for command, expected in QUOTED:
        payload = json.dumps({"tool_input": {"command": command}})
        got = decision(run(CMD, payload))
        if got != expected:
            failures.append(f"quoted: {command!r} -> {got}, expected {expected}")

    for mode, command, expected in MODES + UNREADABLE:
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
    total = (len(COMMANDS) + len(HEREDOCS) + len(REDIRECTS) + 1
             + len(SHADOWED) + len(MODES) + len(QUOTED)
             + len(UNREADABLE) + len(IN_TREE) + len(cases) + 1
             + authority_checks)
    print(f"{total} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
