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
import shlex
import sys
from pathlib import Path

ALLOW = "{}"

# Git's global options sit between `git` and the subcommand, so `git -C /tmp/x
# reset --hard` and `git -c advice.detachedHead=false clean -fd` walked past
# rules that assumed the subcommand comes first. Both were shown doing exactly
# that by an external review on 2026-08-19. The options are stripped before
# matching instead of widening every git rule.
GIT_GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                         "--exec-path", "--config-env"}
GIT_GLOBAL_FLAGS = {"-P", "--no-pager", "--paginate", "--bare",
                    "--literal-pathspecs", "--no-replace-objects"}

# A single rm of build artifacts, matched against the WHOLE command. Parsing
# only the last rm is unsafe: `rm -rf / # rm -rf node_modules` would pass.
# Target tokens exclude ( and backtick so command substitution ending in a
# whitelisted name cannot ride the exemption.
ARTIFACTS = r"(node_modules|\.next|dist|__pycache__|\.cache|build|\.turbo|coverage)"
# The path in front of the artifact name must stay inside the working
# directory: no leading / or ~, no .. segment. Without that, `rm -rf ~/.cache`
# and `rm -rf ../../node_modules` rode the exemption -- the name at the end was
# whitelisted, and the directory it named belonged to someone else.
SAFE_PREFIX = r"((?!\.\.(/|$))[^\s;&|#(`/~][^\s;&|#(`/]*/)*"
SAFE_TARGET = re.compile(rf"{SAFE_PREFIX}{ARTIFACTS}/?$")

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
    # `git restore -- path` and `git checkout -- path` throw away uncommitted
    # work as surely as `rm`, and an external review walked all of these past
    # the guard on 2026-08-17.
    (r"git\s+(checkout|restore)\s+(\.|--\s|-f\b|--force)",
     "this discards uncommitted changes in the working tree"),
    (r"git\s+switch\s+(-f\b|--force|--discard-changes)",
     "git switch --force discards uncommitted changes"),
    (r"git\s+stash\s+(drop|clear)", "this deletes stashed work with no way back"),
    (r"git\s+branch\s+-D\b", "git branch -D deletes a branch even if unmerged"),
    (r"\bfind\b[^|;&]*\s-(delete|exec\s+rm)\b",
     "find with -delete or -exec rm removes every match, and the match is easy to widen"),
    (r"rsync[^|;&]*--delete", "rsync --delete removes files at the destination that are missing at the source"),
    (r"docker\s+volume\s+rm", "docker volume rm destroys the data in that volume"),
    (r"(?i)\bshred\b|\bmkfs\b|\bdd\s+[^|;&]*of=/dev/",
     "this overwrites a device or file beyond recovery"),
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


def segments(command):
    """Words of each command in the line, and a rebuilt string to match on.

    Returns (tokens, text) pairs. Where the line cannot be tokenised at all --
    unbalanced quotes, mostly -- the caller is told, because a guard that
    cannot read a command must not pass it.
    """
    out, unreadable = [], False
    for part in re.split(r"[;\n]|&&|\|\||\|", command):
        if not part.strip():
            continue
        try:
            tokens = shlex.split(part, comments=True)
        except ValueError:
            unreadable = True
            continue
        while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
            tokens.pop(0)          # FOO=bar rm -rf /
        if tokens and tokens[0] == "git":
            rest = tokens[1:]
            while rest and rest[0].startswith("-"):
                head = rest[0]
                if head in GIT_GLOBAL_WITH_VALUE:
                    rest = rest[2:]
                elif head in GIT_GLOBAL_FLAGS or "=" in head:
                    rest = rest[1:]
                else:
                    break
            tokens = ["git"] + rest
        if tokens:
            out.append((tokens, " ".join(tokens)))
    return out, unreadable


def rm_verdict(tokens):
    """`rm` is read by its flags and its targets, not by their order.

    `rm -f -r /var/data` passed a rule that expected the recursive flag first,
    and the artifact exemption used to be a whole-line pattern, which made the
    same mistake in the other direction.
    """
    flags = [t for t in tokens[1:] if t.startswith("-")]
    targets = [t for t in tokens[1:] if not t.startswith("-")]
    recursive = any(t == "--recursive" or re.fullmatch(r"-[a-zA-Z]*[rR][a-zA-Z]*", t)
                    for t in flags)
    if not recursive:
        return None
    if targets and all(SAFE_TARGET.fullmatch(t) for t in targets):
        return None            # build artifacts, inside the working directory
    return "recursive delete (rm -r) permanently removes files"


def git_verdict(tokens):
    """`restore` and `checkout` throw work away by naming a path, not a flag.

    `git restore <path>` discards that path with or without `--`. `git checkout
    <path>` does the same and reads like switching branches, which is how it
    got past this guard and cost the author an uncommitted rewrite of G18 on
    2026-08-19. A branch name and a path are told apart the only way a guard
    can: if the argument names something that exists on disk, it is a path.
    """
    if len(tokens) < 2:
        return None
    verb, rest = tokens[1], tokens[2:]
    if verb == "restore":
        if "--staged" in rest and "--worktree" not in rest:
            return None        # unstages only; the working tree is untouched
        return "git restore discards uncommitted changes in the paths it names"
    if verb == "checkout":
        for arg in rest:
            if arg.startswith("-"):
                continue
            try:
                if Path(arg).exists():
                    return ("git checkout <path> discards uncommitted changes "
                            "in that path")
            except OSError:
                continue
    return None


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

    if not isinstance(payload, dict):
        return ask("the tool payload was not an object, so this command could "
                   "not be checked.")
    tool_input = payload.get("tool_input")
    if tool_input is None:
        return ALLOW
    if not isinstance(tool_input, dict):
        # A payload of an unexpected shape used to raise, and a hook that dies
        # is a hook that permits: the host reads the failure as "no decision".
        return ask("the tool input was not an object, so this command could "
                   "not be checked.")

    command = tool_input.get("command")
    if not isinstance(command, str) or not command:
        return ALLOW  # not a shell call

    if OBFUSCATION.search(command):
        return ask("shell obfuscation (IFS word-splitting or base64 piped to a "
                   "shell). Read the command before approving.")

    parsed, unreadable = segments(command)
    for tokens, text in parsed:
        if tokens[0] == "rm":
            reason = rm_verdict(tokens)
            if reason:
                return ask(reason)
        if tokens[0] == "git":
            reason = git_verdict(tokens)
            if reason:
                return ask(reason)
        for pattern, reason in RULES:
            if pattern.startswith("rm") and tokens[0] == "rm":
                continue       # rm_verdict has already read this one properly
            if re.search(pattern, text):
                return ask(reason)

    for pattern, reason in RULES:
        if pattern.startswith("rm"):
            continue
        if re.search(pattern, command):
            return ask(reason)

    if unreadable:
        return ask("part of this line could not be parsed (unbalanced quotes), "
                   "so it was not checked.")
    return ALLOW


if __name__ == "__main__":
    print(decide(sys.stdin.read()))
