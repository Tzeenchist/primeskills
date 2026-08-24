#!/usr/bin/env python3
"""The live-call gate: a changed skill is released only called from each host.

PS-052 found the same defect wearing four faces because nobody had called the
skill where it lives. Twice "done" meant done-in-theory. This gate refuses a
release whose skills or core changed without recorded live calls, and the test
keeps the gate honest in both directions: it must refuse when calls are
missing or stale, and pass when every changed name is covered per host.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE = ROOT / "bin" / "primeskills-release"

import importlib.machinery
import importlib.util


def load(tmp_root):
    loader = importlib.machinery.SourceFileLoader("_rel", str(RELEASE))
    spec = importlib.util.spec_from_loader("_rel", loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ROOT = tmp_root  # after exec_module: the module re-binds its own ROOT
    return mod


def git(repo, *args):
    p = subprocess.run(("git", "-C", str(repo)) + args,
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return p.stdout.strip()


def commit(repo, message):
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t",
                    "-c", "user.email=t@t", "commit", "-q", "-m", message],
                   check=True)


def main():
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "master"], cwd=repo, check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=t",
                        "-c", "user.email=t@t", "commit", "-q", "--allow-empty",
                        "-m", "init"], check=True)
        (repo / "skills" / "old").mkdir(parents=True)
        (repo / "skills" / "old" / "SKILL.md").write_text("v1\n", encoding="utf-8")
        commit(repo, "init")
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=t",
                        "-c", "user.email=t@t", "tag", "-a", "v9.0.0",
                        "-m", "old release"], check=True)
        at = git(repo, "rev-list", "-n", "1", "v9.0.0")

        mod = load(repo)

        # the gate speaks for every host the set supports; a new agent that is
        # installed but not asked for live calls would ship unverified there
        if set(mod.HOSTS) != {"claude", "codex", "kimi", "opencode", "cline", "kilo"}:
            failures.append(f"HOSTS не покрывает шесть хостов: {mod.HOSTS}")

        # nothing changed since the tag: the gate has nothing to ask
        if mod.missing_livecalls(at) != []:
            failures.append("без изменений с тега гейт требовать ничего не должен")

        # a skill and core change; no notes yet -> eight missing pairs
        (repo / "skills" / "new").mkdir(parents=True)
        (repo / "skills" / "new" / "SKILL.md").write_text("v1\n", encoding="utf-8")
        core = repo / "core"
        core.mkdir()
        (core / "OUTPUT.md").write_text("changed\n", encoding="utf-8")
        commit(repo, "change new skill and core")

        missing = mod.missing_livecalls(at)
        expect = {("new", h) for h in mod.HOSTS} | {("core", h) for h in mod.HOSTS}
        checks = 1
        if set(missing) != expect:
            failures.append(f"ожидали 8 пар, получили {sorted(missing)}")
        # an untouched skill is nobody's business
        if any(n == "old" for n, _ in missing):
            failures.append("гейт спросил про навык, который не менялся")

        # notes cover part of the pairs; the rest stay missing
        run_dir = repo / ".primeskills" / "run"
        run_dir.mkdir(parents=True)
        name = f"master-{hashlib.sha1(b'master').hexdigest()[:8]}.jsonl"
        note = lambda n, h: {"kind": "note", "stage": "livecall",
                             "text": f"{n}: menu opened, choice lands ({h})",
                             "ts": "2099-01-01T00:00:00+00:00"}
        lines = [json.dumps(note("new", "claude")),
                 json.dumps(note("core", "claude"))]
        (run_dir / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
        missing = mod.missing_livecalls(at)
        checks += 1
        want = expect - {("new", "claude"), ("core", "claude")}
        if set(missing) != want:
            failures.append(f"после двух записей ожидали {sorted(want)}, "
                            f"получили {sorted(missing)}")

        # a stale note (older than the tag) does not satisfy the gate
        checks += 1
        stale = [json.dumps({**note("new", "codex"),
                             "ts": "2020-01-01T00:00:00+00:00"})]
        (run_dir / name).write_text("\n".join(stale), encoding="utf-8")
        missing = mod.missing_livecalls(at)
        if ("new", "codex") not in missing:
            failures.append("протухшая запись закрыла гейту глаза")

        print(f"{checks + 2} checks, {len(failures)} failed")
    for f in failures:
        print(f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
