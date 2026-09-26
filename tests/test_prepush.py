#!/usr/bin/env python3
"""The pre-push guard blocks known secrets and vendor tokens, and nothing else.

PS-092: a sudo password sat in the history of two repositories for half a
year as `PROD_SUDO_PASS="…"`; the review rule G17 only ever read text. The
guard is a git hook, so it holds for every host and for a person, and it has
to leave the repository's own hooks running -- a global core.hooksPath would
otherwise switch every one of them off.

Every case runs under a scratch HOME: the global git config written here is a
scratch one, never the user's.
"""
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "bin" / "primeskills-install"
SECRETS = ROOT / "bin" / "primeskills-secrets"
PREPUSH = ROOT / "bin" / "primeskills-prepush"
KNOWN = "correct-horse-7391"
# glued so that this file does not itself look like a token to any scanner
TOKEN = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"


def env_for(home):
    return dict(os.environ, HOME=str(home), GIT_CONFIG_NOSYSTEM="1",
                GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def sh(args, cwd, env, stdin=None):
    return subprocess.run(args, cwd=cwd, env=env, input=stdin,
                          capture_output=True, text=True)


def repo_with_remote(base, env):
    remote = base / "remote.git"
    work = base / "work"
    sh(["git", "init", "-q", "--bare", "-b", "main", str(remote)], base, env)
    sh(["git", "init", "-q", "-b", "main", str(work)], base, env)
    sh(["git", "remote", "add", "origin", str(remote)], work, env)
    (work / "a.txt").write_text("start\n", encoding="utf-8")
    sh(["git", "add", "-A"], work, env)
    sh(["git", "commit", "-q", "-m", "start"], work, env)
    return work


def commit(work, env, name, text, msg):
    (work / name).write_text(text, encoding="utf-8")
    sh(["git", "add", "-A"], work, env)
    return sh(["git", "commit", "-q", "-m", msg], work, env)


def main():
    failures, checks = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        home = base / "home"
        home.mkdir()
        env = env_for(home)

        out = sh([sys.executable, str(INSTALL), "--apply", "--live"], base, env)
        hooks_dir = home / ".primeskills" / "git-hooks"
        got = sh(["git", "config", "--global", "--get", "core.hooksPath"],
                 base, env).stdout.strip()
        checks += 1
        if got != str(hooks_dir):
            failures.append(f"install: core.hooksPath={got!r}, expected {hooks_dir}"
                            f" ({out.stdout[-300:]!r})")
        for name in ("pre-push", "pre-commit", "commit-msg"):
            checks += 1
            p = hooks_dir / name
            if not (p.is_file() and os.access(p, os.X_OK)):
                failures.append(f"install: hook shim {name} missing or not executable")

        # the secret goes in hidden and is stored as a hash, never as text
        checks += 1
        r = sh([sys.executable, str(SECRETS), "add", "--stdin"], base, env,
               stdin=KNOWN + "\n")
        store = home / ".primeskills" / "secrets"
        if r.returncode != 0 or not store.is_file():
            failures.append(f"secrets add failed: {r.stdout}{r.stderr}")
        else:
            checks += 1
            if KNOWN in store.read_text(encoding="utf-8") or KNOWN in r.stdout:
                failures.append("secrets: the value itself was stored or printed")
            checks += 1
            if stat.S_IMODE(store.stat().st_mode) != 0o600:
                failures.append(f"secrets: mode {oct(store.stat().st_mode)}, expected 600")

        # a clean push goes through, and the repository's own hook still runs
        work = repo_with_remote(base, env)
        marker = base / "own-hook-ran"
        own = work / ".git" / "hooks" / "pre-push"
        own.write_text(f"#!/bin/sh\ntouch {marker}\nexit 0\n", encoding="utf-8")
        own.chmod(0o755)
        commit(work, env, "b.txt", "plain text\n", "clean")
        r = sh(["git", "push", "-q", "origin", "main"], work, env)
        checks += 1
        if r.returncode != 0:
            failures.append(f"clean push blocked: {r.stderr[-300:]}")
        checks += 1
        if not marker.exists():
            failures.append("the repository's own pre-push did not run")

        # a repository hook that refuses still refuses
        own.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        commit(work, env, "c.txt", "more\n", "more")
        r = sh(["git", "push", "-q", "origin", "main"], work, env)
        checks += 1
        if r.returncode == 0:
            failures.append("a refusing repository hook was overridden")
        own.unlink()

        # other hook types reach the repository's own hook through the shim
        pc_marker = base / "own-pre-commit-ran"
        pc = work / ".git" / "hooks" / "pre-commit"
        pc.write_text(f"#!/bin/sh\ntouch {pc_marker}\n", encoding="utf-8")
        pc.chmod(0o755)
        commit(work, env, "d.txt", "x\n", "with pre-commit")
        checks += 1
        if not pc_marker.exists():
            failures.append("the repository's own pre-commit went silent")
        pc.unlink()
        sh(["git", "push", "-q", "origin", "main"], work, env)

        # a known secret is blocked, and the refusal does not print it
        commit(work, env, "db-sync.sh", f'PROD_SUDO_PASS="{KNOWN}"\n', "leak")
        r = sh(["git", "push", "-q", "origin", "main"], work, env)
        checks += 1
        if r.returncode == 0:
            failures.append("a known secret was pushed")
        checks += 1
        if KNOWN in r.stdout + r.stderr:
            failures.append("the refusal printed the secret")
        checks += 1
        if "db-sync.sh" not in r.stdout + r.stderr:
            failures.append(f"the refusal did not name the file: {r.stderr[-300:]!r}")

        # removing it in a later commit does not help: history is pushed too
        commit(work, env, "db-sync.sh", "PROD_SUDO_PASS=\"$PASS\"\n", "hide it")
        r = sh(["git", "push", "-q", "origin", "main"], work, env)
        checks += 1
        if r.returncode == 0:
            failures.append("a secret removed in a later commit was pushed")
        sh(["git", "reset", "-q", "--hard", "HEAD~2"], work, env)

        # a vendor token is blocked without being registered anywhere
        commit(work, env, "ci.env", f"GITHUB={TOKEN}\n", "token")
        r = sh(["git", "push", "-q", "origin", "main"], work, env)
        checks += 1
        if r.returncode == 0:
            failures.append("a GitHub token was pushed")
        sh(["git", "reset", "-q", "--hard", "HEAD~1"], work, env)

        # a secret added only while resolving a merge travels in the merge
        # commit, which `git log -p` leaves out unless asked
        sh(["git", "switch", "-q", "-c", "side"], work, env)
        commit(work, env, "side.txt", "side\n", "side")
        sh(["git", "switch", "-q", "main"], work, env)
        commit(work, env, "main2.txt", "main\n", "main moves")
        sh(["git", "merge", "-q", "--no-ff", "--no-commit", "side"], work, env)
        (work / "resolved.txt").write_text(f"token={KNOWN}\n", encoding="utf-8")
        sh(["git", "add", "-A"], work, env)
        sh(["git", "commit", "-q", "-m", "merge side"], work, env)
        r = sh(["git", "push", "-q", "origin", "main"], work, env)
        checks += 1
        if r.returncode == 0:
            failures.append("a secret introduced in a merge commit was pushed")
        sh(["git", "reset", "-q", "--hard", "HEAD~1"], work, env)
        sh(["git", "reset", "-q", "--hard", "origin/main"], work, env)

        # a range the guard cannot read is refused, not waved through
        head = sh(["git", "rev-parse", "HEAD"], work, env).stdout.strip()
        bogus = "f" * 40
        r = sh([sys.executable, str(PREPUSH), "origin", "x"], work, env,
               stdin=f"refs/heads/main {bogus} refs/heads/main {head}\n")
        checks += 1
        if r.returncode == 0:
            failures.append("an unreadable range was allowed")

        # deleting a branch pushes no content
        sh(["git", "push", "-q", "origin", "main:gone"], work, env)
        r = sh(["git", "push", "-q", "origin", ":gone"], work, env)
        checks += 1
        if r.returncode != 0:
            failures.append(f"branch delete blocked: {r.stderr[-200:]}")

        # uninstall gives core.hooksPath back
        sh([sys.executable, str(INSTALL), "--apply", "--live", "--uninstall"], base, env)
        got = sh(["git", "config", "--global", "--get", "core.hooksPath"],
                 base, env).stdout.strip()
        checks += 1
        if got:
            failures.append(f"uninstall left core.hooksPath={got!r}")

    # someone else's global hooksPath is not taken over
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        home = base / "home"
        home.mkdir()
        env = env_for(home)
        sh(["git", "config", "--global", "core.hooksPath", "/opt/their-hooks"], base, env)
        out = sh([sys.executable, str(INSTALL), "--apply", "--live"], base, env)
        got = sh(["git", "config", "--global", "--get", "core.hooksPath"],
                 base, env).stdout.strip()
        checks += 1
        if got != "/opt/their-hooks":
            failures.append(f"install replaced someone else's hooksPath: {got!r}")
        checks += 1
        if "hooksPath" not in out.stdout:
            failures.append("install did not report the foreign hooksPath")

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
