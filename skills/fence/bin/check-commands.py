#!/usr/bin/env python3
"""PreToolUse guard: ask before a destructive shell command runs -- and where
the user has switched confirmations off, stop asking and start deciding.

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
import subprocess
import sys
import tempfile
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

# Modes where the user has already said "do not ask me". A question here is not
# protection: it renders as a prompt that gets approved without being read, and
# the reflex it trains is the one that matters on the day the answer should have
# been no. So in these modes the guard decides instead of asking -- deny for the
# short list below, silent allow plus a journal line for everything else.
SILENT_MODES = {"bypassPermissions", "dontAsk"}
# The irreversible short list. Losing these is not "redo the step": it is data
# gone, history rewritten for everyone, or a cluster resource deleted. Anything
# recoverable from the working tree, a branch, or a rebuild stays out on
# purpose -- a long deny list is a disabled deny list.
# Compiled once, at import: a pattern that does not compile used to raise from
# inside the decision and take the hook down with it -- and a hook that dies is
# a hook that permits. Compiling here fails in tests instead of in the field.
CATASTROPHIC = tuple((re.compile(pat), rung, why) for pat, rung, why in (
    (r"(?i)drop\s+(table|database|schema)|\bdropdb\b|\btruncate\b|manage\.py\s+flush",
     "delete", "destroys database contents"),
    (r"git\s+push\s+.*(-f\b|--force)", "push",
     "rewrites history others may already have"),
    (r"kubectl\s+delete", "delete", "removes cluster resources"),
    (r"docker\s+volume\s+rm", "delete", "destroys the data in that volume"),
    (r"(?i)\bshred\b|\bmkfs\b|\bdd\s+[^|;&]*of=/dev/", "delete",
     "overwrites a device beyond recovery"),
))

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

# The exact RUNGS-to-command correspondences defined by PS-041. This is
# deliberately not a catalogue of guesses for the remaining ladder entries.
COMMAND_RUNGS = {
    ("git", "push"): "push",
    ("gh", "pr", "create"): "pr",
    ("git", "merge"): "merge",
    ("kubectl", "apply"): "deploy",
}


def deny(reason):
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"[fence] {reason}",
        }
    })


def run_tool(args, cwd):
    """Call `primeskills-run`, and never let it change the decision.

    The guard answers on every command. If the journal is missing, outside a
    repository, or slow, that is the journal's problem: the verdict above was
    already reached without it.
    """
    try:
        p = subprocess.run(["primeskills-run", *args], cwd=cwd or None,
                           capture_output=True, text=True, timeout=5)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.SubprocessError):
        return None, ""


def first_target(tokens):
    """The thing a catastrophic command names: a database, a resource, a path."""
    for t in tokens[1:]:
        if not t.startswith("-") and "=" not in t:
            return t
    return None


def escapes(target, cwd):
    """Does this path leave the directory the session is working in?"""
    if target.startswith("~") or target == "/":
        return True
    try:
        base = Path(cwd or ".").resolve()
        return not str((base / target).resolve()).startswith(str(base))
    except OSError:
        return True


def ask(reason):
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": f"[fence] {reason}",
        }
    })


# Programs that execute what they are fed. A heredoc going into one of these is
# a command; a heredoc going into `cat > file` or `tee` is a document that
# happens to quote one. Reading them the same way made the guard refuse the
# writing of its own tests -- twice in one hour, on 2026-08-19.
INTERPRETERS = {"sh", "bash", "zsh", "dash", "ksh", "python", "python2",
                "python3", "node", "deno", "ruby", "perl", "php", "psql",
                "mysql", "sqlite3", "mongo", "redis-cli", "kubectl", "docker",
                "ssh", "env", "xargs", "eval"}
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def head_words(head):
    """The words before `<<`, read even when the quoting does not close.

    A heredoc opened inside a quoted command substitution -- the ordinary
    `git commit -m "$(cat <<'EOF'` -- leaves an unbalanced double quote in
    front of it. shlex raises there, and the exception used to travel to the
    top-level handler, which answers every crash with `ask`: twelve prompts in
    one session on 2026-08-25, all approved unread. Quoting is decoration here;
    the only word that matters is the program at the front, so on a raise the
    words are taken without it.
    """
    if not head.strip():
        return []
    try:
        return shlex.split(head, comments=False)
    except ValueError:
        return re.findall(r"[^\s|&;<>()]+", head)


COMMAND_BREAK = re.compile(r"\|\||&&|[|;&]|\$\(|`|\(")


def head_executes(head):
    """Does anything in front of `<<` run what the document says?

    The consumer is the command the heredoc hangs off, and that is neither
    always the first word of the line nor always the last. `echo x | bash
    <<'SH'` read `echo`, called a shell script a document and dropped it -- in
    every mode, not only where confirmations are off. `psql -c "$(cat <<'SQL'`
    hands its text to psql through cat, so the last word is wrong too. Every
    word standing in command position is checked, and only those: a head that
    merely mentions an interpreter -- `echo 'run bash later' > notes.md` --
    still writes a document.
    """
    for chunk in COMMAND_BREAK.split(head):
        words = head_words(chunk)
        while words and (words[0] in ("sudo", "time", "nohup") or "=" in words[0]):
            words = words[1:]
        if words and Path(words[0]).name in INTERPRETERS:
            return True
    return False


def without_inert_heredocs(command):
    """The command text to judge, with document bodies taken out of it.

    A heredoc body is scanned when the thing consuming it runs what it reads,
    and dropped when the body is on its way to a file. The introducing line is
    always kept: `cat > f <<EOF` is still a command, and a redirect over
    something precious is still a redirect.
    """
    if "<<" not in command:
        return command, 0
    lines = command.split("\n")
    kept, dropped, i = [], 0, 0
    while i < len(lines):
        line = lines[i]
        kept.append(line)
        hit = HEREDOC.search(line)
        i += 1
        if not hit:
            continue
        marker = hit.group(2)
        executes = head_executes(line.split("<<")[0])
        body = []
        while i < len(lines) and lines[i].strip() != marker:
            body.append(lines[i])
            i += 1
        if i < len(lines):
            i += 1                      # the closing marker itself
        if executes:
            kept.extend(body)
        else:
            dropped += 1
    return "\n".join(kept), dropped


def top_level_parts(command):
    """The separate commands in a line, split only where the shell splits.

    `;`, `|`, `&&` and a newline separate commands at the top level and are
    ordinary text anywhere else. A regex that did not know the difference cut
    `awk -F"|"`, `git log --format="%h | %s"` and `find ... -exec rm {} ';'` in
    half; the halves had unbalanced quotes, so the guard could not read them and
    asked. In a mode where the user has switched asking off, that question is
    the one answer the guard is not allowed to give -- so ordinary work stopped
    on a quote character.
    """
    parts, buf = [], []
    quote = None                 # inside '...' or "..."
    depth = 0                    # open $( ... ), counted
    backtick = False             # inside ` ... `, which does not nest
    i, n = 0, len(command)
    while i < n:
        ch = command[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < n:
                buf.append(command[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            buf.append(ch)
            buf.append(command[i + 1])
            i += 2
            continue
        if ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if command.startswith("$(", i):
            depth += 1
            buf.append("$(")
            i += 2
            continue
        if ch == ")" and depth:
            depth -= 1
            buf.append(ch)
            i += 1
            continue
        if ch == "`":
            backtick = not backtick
            buf.append(ch)
            i += 1
            continue
        if depth == 0 and not backtick:
            if ch in ";\n":
                parts.append("".join(buf))
                buf = []
                i += 1
                continue
            if ch == "|":
                if buf and buf[-1] == ">":
                    buf.append(ch)      # >| is one output-redirection operator
                    i += 1
                    continue
                parts.append("".join(buf))
                buf = []
                i += 2 if command.startswith("||", i) else 1
                continue
            if command.startswith("&&", i):
                parts.append("".join(buf))
                buf = []
                i += 2
                continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


# Which leading options belong to the program rather than to its subcommand,
# split into the ones that swallow the next word and the ones that do not.
GLOBAL_OPTIONS = {
    "git": (GIT_GLOBAL_WITH_VALUE, GIT_GLOBAL_FLAGS),
    "gh": ({"-R", "--repo"}, set()),
}


def segments(command):
    """Words of each command in the line, and a rebuilt string to match on.

    Returns (tokens, text) pairs. Where the line cannot be tokenised at all --
    unbalanced quotes, mostly -- the caller is told, because a guard that
    cannot read a command must not pass it.
    """
    out, unreadable = [], False
    for part in top_level_parts(command):
        if not part.strip():
            continue
        try:
            tokens = shlex.split(part, comments=True)
        except ValueError:
            unreadable = True
            continue
        while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
            tokens.pop(0)          # FOO=bar rm -rf /
        # Global options sit between the program and its subcommand, so a rule
        # keyed on the subcommand misses `git -C x push` and `gh --repo o/r pr
        # create` unless they are stripped first. `gh` was added when the
        # authority rules landed: `--repo` walked straight past the pr rung.
        if tokens and tokens[0] in GLOBAL_OPTIONS:
            with_value, flags = GLOBAL_OPTIONS[tokens[0]]
            program, rest = tokens[0], tokens[1:]
            while rest and rest[0].startswith("-"):
                head = rest[0]
                if head in with_value:
                    rest = rest[2:]
                elif head in flags or "=" in head:
                    rest = rest[1:]
                else:
                    break
            tokens = [program] + rest
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
    got past this guard and cost the author an uncommitted rewrite of G10 on
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


def journal_cwd(command, cwd):
    """Where the run journal lives for the command about to run.

    The hook is handed the session's directory, which is not always the one the
    command acts on: `cd <repo> && git push` and `git -C <repo> push` both work
    on a repository the session is not standing in. Asking the ladder from the
    wrong place got `primeskills-run: not inside a git repository`, a non-zero
    code and therefore a refusal — while the rung was open the whole time.

    Read from the raw line rather than from `segments()`, which strips `-C`
    along with the rest of git's global options before anyone sees it. Only the
    journal is looked up this way; whether a path escapes is still judged
    against the directory the session is actually in, which is the more
    cautious base of the two.
    """
    for part in top_level_parts(command):
        try:
            words = shlex.split(part, comments=True)
        except ValueError:
            continue
        candidate = None
        if words[:1] == ["cd"] and len(words) > 1 and not words[1].startswith("-"):
            candidate = words[1]
        elif words[:1] == ["git"] and "-C" in words[:4]:
            i = words.index("-C")
            candidate = words[i + 1] if i + 1 < len(words) else None
        if not candidate:
            continue
        try:
            target = (Path(cwd or ".") / candidate).resolve()
        except OSError:
            continue
        if target.is_dir():
            return str(target)
    return cwd


def command_rung(tokens):
    """Return the authority rung for an exact command prefix, if it has one."""
    for prefix, rung in COMMAND_RUNGS.items():
        if tuple(tokens[:len(prefix)]) == prefix:
            return rung
    return None


def why_not(rung, code, said, named):
    """Which of three things stopped the rung check — they need different fixes.

    One sentence covered all three, and the one it chose ("record the grant")
    is wrong advice for two of them. On 2026-08-25 it was printed twice to
    someone who had recorded the grant both times: once because the journal was
    not readable from the command's directory, once because the mandate named a
    pattern the command could not match.
    """
    text = said or ""
    if code is None or "not inside a git repository" in text:
        return ("The mandate journal is not readable from this directory, so "
                "the rung was never checked: run this from the repository "
                "whose journal holds the mandate.")
    if code == 0 and named:
        return (f"The open {rung} names {named.group(1)}, which this command "
                f"does not mention. Matching is literal: grant the target the "
                f"command itself names.")
    return f"Open the {rung} rung first: `{grant_command(rung)}`."


def grant_command(rung):
    if rung in {"deploy", "delete"}:
        return (f"primeskills-run grant {rung} --target <the path or environment> "
                f"\"<what the user allowed>\"")
    return f'primeskills-run grant {rung} "<what the user allowed>"'


OUTPUT_REDIRECTS = {">", ">>", ">|", "<>", "&>", "&>>"}


def output_verdict(command, parsed, cwd):
    """Ask when a redirect or tee names a file outside the session tree."""
    targets = []
    for part in top_level_parts(command):
        lexer = shlex.shlex(part, posix=False, punctuation_chars="<>|&")
        lexer.whitespace_split = True
        lexer.commenters = "#"
        try:
            words = list(lexer)
        except ValueError:
            continue
        for i, word in enumerate(words[:-1]):
            if word not in OUTPUT_REDIRECTS:
                continue
            try:
                target = shlex.split(words[i + 1], comments=False)
            except ValueError:
                continue
            if len(target) == 1:
                targets.append(target[0])

    for tokens, _text in parsed:
        if Path(tokens[0]).name != "tee":
            continue
        after_options = False
        for token in tokens[1:]:
            if token == "--":
                after_options = True
            elif token == "-":
                continue
            elif after_options or not token.startswith("-"):
                targets.append(token)

    try:
        temp = Path(tempfile.gettempdir()).resolve()
    except OSError:
        temp = None
    for target in targets:
        try:
            resolved = (Path(cwd or ".") / target).resolve()
        except OSError:
            resolved = None
        if resolved == Path("/dev/null"):
            continue
        if (temp is not None and Path(target).is_absolute() and resolved is not None
                and (resolved == temp or temp in resolved.parents)):
            continue
        if escapes(target, cwd):
            return f"output writes outside the working directory: {target}"
    return None


def text_only_verdict(command):
    """What can still be said about a line nobody could tokenise.

    Two callers reach this: the branch below, where the quoting does not close,
    and the crash handler, where the guard fell over before judging anything.
    They ask the same question and must not answer it twice in two places.
    """
    hit = next((why for pat, _rung, why in CATASTROPHIC if pat.search(command)),
               None)
    if hit:
        return hit
    if any(re.search(pat, command) for pat, _ in RULES if pat.startswith("rm")):
        return "names a recursive delete"
    return None


def crashed(raw, exc):
    """The verdict when the guard itself fell over.

    A crash answered `ask` in every mode, because the handler ran before the
    payload -- and the mode inside it -- had been read. Where confirmations are
    off, `ask` is the one verdict the guard may not give: it renders as a prompt
    approved unread, and it trains the reflex that answers the one that
    mattered. On 2026-08-25 a single parsing bug spent twelve of those prompts
    in one session. So a crash is now held to the rules that can be read off
    the text, and what survives passes with a line in the journal saying it
    went unchecked.
    """
    detail = (f"the guard itself failed ({type(exc).__name__}), so this "
              f"command was not checked.")
    try:
        payload = json.loads(raw) if raw and raw.strip() else None
        if not isinstance(payload, dict):
            return ask(detail)
        if payload.get("permission_mode") not in SILENT_MODES:
            return ask(detail)
        tool_input = payload.get("tool_input")
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if not isinstance(command, str) or not command:
            return ALLOW
        why = text_only_verdict(command)
        if why:
            return deny(f"{detail} Read as text it {why}, and confirmations "
                        f"are off, so it is refused rather than asked. Say "
                        f"what it will do, or fix the guard.")
        run_tool(["note", "guard",
                  f"allowed unchecked ({type(exc).__name__}): {command[:120]}"],
                 payload.get("cwd") or "")
        return ALLOW
    except Exception:  # noqa: BLE001 -- see main(): silence is consent
        return ask(detail)


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

    mode = payload.get("permission_mode")
    cwd = payload.get("cwd") or ""
    command, _inert = without_inert_heredocs(command)
    parsed, unreadable = segments(command)

    verdict = None                     # (reason, rung or None, target or None)
    # The segment that produced the verdict, not the whole line. Matching a
    # mandate's target against the line let anything else in it satisfy the
    # permission: on 2026-08-25 every push passed because the diagnostic
    # `may push --target X` stood to the left of it, never because the push
    # named X. Where no single segment produced the verdict, this stays None
    # and the line is used, as before.
    segment = None
    authority_verdict = False
    for tokens, text in parsed:
        if tokens[0] == "rm":
            reason = rm_verdict(tokens)
            if reason:
                targets = [t for t in tokens[1:] if not t.startswith("-")]
                out = [t for t in targets if escapes(t, cwd)]
                verdict = (reason, "delete" if out else None, out[0] if out else None)
                segment = text
                break
        if tokens[0] == "git":
            reason = git_verdict(tokens)
            if reason:
                verdict = (reason, None, None)
                break
        hit = next(((rung, why) for pat, rung, why in CATASTROPHIC
                    if pat.search(text)), None)
        if hit:
            rung, why = hit
            verdict = (why, rung, first_target(tokens))
            segment = text
            break
        rule = next((r for pat, r in RULES
                     if not (pat.startswith("rm") and tokens[0] == "rm")
                     and re.search(pat, text)), None)
        if rule:
            verdict = (rule, None, None)
            break

    if verdict is None:
        # A segment that could not be tokenised has no words to judge, so the
        # whole line is read as text. The catastrophic list is checked here too:
        # without it an unreadable line carried its rung away, and in a silent
        # mode a missing rung means a silent allow.
        hit = next(((rung, why) for pat, rung, why in CATASTROPHIC
                    if pat.search(command)), None)
        if hit:
            rung, why = hit
            verdict = (why, rung, None)

    if verdict is None:
        for pattern, reason in RULES:
            if not pattern.startswith("rm") and re.search(pattern, command):
                verdict = (reason, None, None)
                break

    # Authority comes after every destructive rule. If it ran in the loop
    # above, `git push && rm -rf /srv/data` would stop at push and the later rm
    # would never be judged. It stays before output redirects because this
    # verdict carries a rung and must not lose it to a rungless redirect.
    if verdict is None:
        for tokens, _text in parsed:
            rung = command_rung(tokens)
            if rung:
                verdict = (f"this command requires the {rung} rung", rung, None)
                segment = _text
                authority_verdict = True
                break

    # Last, and that position is the point. A redirect carries no rung, and a
    # rungless verdict passes silently where confirmations are off. Checked
    # first, it shadowed the rules that do carry one: `rm -rf /srv/data` was
    # refused, and `rm -rf /srv/data > /etc/hosts` was allowed silently --
    # appending a redirect bought the delete a pass.
    if verdict is None:
        reason = output_verdict(command, parsed, cwd)
        if reason:
            verdict = (reason, None, None)

    if verdict is None:
        if unreadable:
            if mode in SILENT_MODES:
                # Asking is off, so the doubt is settled instead of handed
                # over: the text is held to the `rm` rules the tokens would
                # have answered, and what survives passes with a journal line
                # saying it went unread.
                why = text_only_verdict(command)
                if why:
                    # The reason comes from the rule that matched, not from a
                    # sentence written next to one of them. Only the `rm` arm is
                    # reachable here today -- the destructive list is matched
                    # against the whole line further up -- so a message spelled
                    # `recursive delete` would start lying the day that order
                    # changes rather than fail.
                    return deny(f"part of this line could not be parsed and it "
                                f"{why}, so it is refused rather than asked. "
                                f"Rewrite it so the quoting balances, or say "
                                f"what it should remove.")
                run_tool(["note", "guard",
                          f"allowed unread (unbalanced quotes): {command[:120]}"], cwd)
                return ALLOW
            return ask("part of this line could not be parsed (unbalanced "
                       "quotes), so it was not checked.")
        return ALLOW

    reason, rung, target = verdict
    # Existing destructive verdicts keep their confirmation-mode behaviour.
    # In particular, opening push does not turn a force-push prompt into an
    # allow. Only the explicit authority mappings gain the open-rung fast path.
    if mode not in SILENT_MODES and not authority_verdict:
        return ask(reason)
    if rung:
        # Peek at the ladder without spending anything, and let the human's own
        # words settle it: a mandate counts when what they named appears in the
        # command. The guard's guess at "the target" is a first operand; theirs
        # is a database or a path they meant.
        where = journal_cwd(command, cwd)
        code, said = run_tool(["may", rung, "--peek"], where)
        named = re.search(r"target=(\S+)", said or "")
        where_named = (segment or command).lower()
        covered = code == 0 and (not named or named.group(1).lower() in where_named)
        if covered:
            run_tool(["note", "guard", f"allowed under an open {rung}: {command[:120]}"],
                     where)
            return ALLOW
        advice = why_not(rung, code, said, named)
        if mode not in SILENT_MODES:
            return ask(f"{reason}. {advice}")
        run_tool(["note", "guard", f"refused, no {rung}: {command[:120]}"], where)
        return deny(
            f"{reason}. Confirmations are off, so this is refused rather than "
            f"asked: tell the user what it will do. {advice}")
    if mode not in SILENT_MODES:
        return ask(reason)

    # The user turned confirmations off. Asking anyway trains the reflex; going
    # quiet everywhere removes the guard exactly where the agent runs unwatched.
    # So: the short irreversible list needs a permission that was actually
    # granted, and everything else passes with a line in the journal.
    run_tool(["note", "guard", f"allowed silently: {command[:120]}"], cwd)
    return ALLOW


def main(raw):
    """Decide, and answer for the guard when deciding raises.

    The catch lives here rather than under `__main__` so a test can inject a
    failure and read the verdict: the crash path is the one the user meets on a
    bad day, and it went four months without a test.
    """
    try:
        return decide(raw)
    except Exception as exc:  # noqa: BLE001 -- a crash must not become consent
        return crashed(raw, exc)


if __name__ == "__main__":
    print(main(sys.stdin.read()))
