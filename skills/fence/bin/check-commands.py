#!/usr/bin/env python3
"""PreToolUse guard: ask before a destructive shell command runs.

Ported from gstack's check-careful.sh. Kept: fail-closed parsing, the
obfuscation tripwire, the anchored build-artifact whitelist, and the reasons
those exist -- each one records a real bypass. Dropped: the telemetry write
that fired on every match. Added: killall, dropdb, DROP SCHEMA, manage.py
flush, git clean -fd.

Reads the hook payload on stdin, prints a PreToolUse decision on stdout.
The decision must sit under hookSpecificOutput; a top-level permissionDecision
is ignored and silently no-ops the guard.
"""
import json
import re
import sys

ALLOW = "{}"

# A single rm of build artifacts, matched against the WHOLE command. Parsing
# only the last rm is unsafe: `rm -rf / # rm -rf node_modules` would pass.
# Target tokens exclude ( and backtick so command substitution ending in a
# whitelisted name cannot ride the exemption.
ARTIFACTS = r"(node_modules|\.next|dist|__pycache__|\.cache|build|\.turbo|coverage)"
SAFE_RM = re.compile(
    r"^\s*rm\s+(-[a-zA-Z]*[rR][a-zA-Z]*\s+|--recursive\s+)"
    rf"(([^\s;&|#(`]*/)?{ARTIFACTS}\s*)+$"
)

OBFUSCATION = re.compile(
    r"\$\{IFS\}|\$IFS|\$\(echo[^)]*base64[^)]*\)"
    r"|base64\s+(-d|--decode)[^|]*\|\s*(sh|bash)"
)

RULES = [
    (r"rm\s+(-[a-zA-Z]*[rR]|--recursive)", "recursive delete (rm -r) permanently removes files"),
    (r"(?i)drop\s+(table|database|schema)", "SQL DROP permanently deletes database objects"),
    (r"(?i)\bdropdb\b", "dropdb destroys an entire database"),
    (r"(?i)\btruncate\b", "SQL TRUNCATE deletes every row in a table"),
    (r"manage\.py\s+flush", "manage.py flush empties the database"),
    (r"git\s+push\s+.*(-f\b|--force)", "force-push rewrites remote history; others may lose work"),
    (r"git\s+reset\s+--hard", "git reset --hard discards all uncommitted changes"),
    (r"git\s+(checkout|restore)\s+\.", "this discards all uncommitted changes in the working tree"),
    (r"git\s+clean\s+-[a-zA-Z]*[fd]", "git clean deletes untracked files, including new work never staged"),
    (r"\bkillall\b", "killall terminates every matching process, not just yours"),
    (r"kubectl\s+delete", "kubectl delete removes cluster resources and may hit production"),
    (r"docker\s+(rm\s+-f|system\s+prune)", "Docker force-remove or prune deletes containers and images"),
]


def ask(reason):
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": f"[fence] {reason}",
        }
    })


def decide(raw):
    if not raw.strip():
        return ALLOW
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        # Unreadable payload. A guard that allows what it cannot read is not a
        # guard: fail closed.
        return ask("could not read the tool payload to check this command. "
                   "Approve only if you know what it does.")

    command = (payload.get("tool_input") or {}).get("command")
    if not isinstance(command, str) or not command:
        return ALLOW  # not a shell call

    if OBFUSCATION.search(command):
        return ask("shell obfuscation (IFS word-splitting or base64 piped to a "
                   "shell). Read the command before approving.")

    if "\n" not in command and SAFE_RM.match(command):
        return ALLOW

    for pattern, reason in RULES:
        if re.search(pattern, command):
            return ask(reason)
    return ALLOW


if __name__ == "__main__":
    print(decide(sys.stdin.read()))
