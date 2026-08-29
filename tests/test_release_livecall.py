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


def commit(repo, message, when=None):
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    env = dict(os.environ)
    if when:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t",
                    "-c", "user.email=t@t", "commit", "-q", "-m", message],
                   check=True, env=env)


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

        # PS-054. Timestamps are instants, not strings. `primeskills-run` writes
        # UTC and git writes the committer's local offset, so a note made after
        # the tag can still sort before it character by character -- 06:45+00:00
        # against 09:21+03:00 is 24 minutes later and lexicographically earlier.
        # The fixture above never caught it: year 2099 is far enough ahead that
        # string order and time order happen to agree.
        checks += 1
        tag_at = git(repo, "show", "-s", "--format=%cI", at)
        from datetime import datetime, timedelta
        later = (datetime.fromisoformat(tag_at) + timedelta(minutes=25))
        utc = later.astimezone(__import__("datetime").timezone.utc).isoformat()
        fresh = [json.dumps({**note("new", "codex"), "ts": utc})]
        (run_dir / name).write_text("\n".join(fresh) + "\n", encoding="utf-8")
        if ("new", "codex") in mod.missing_livecalls(at):
            failures.append(
                f"запись {utc} сделана позже тега {tag_at}, а гейт счёл её "
                f"протухшей — время сравнивается строками")

        # PS-059, first facet. Matching was a substring search over the whole
        # note, so a note about one host closed another host's pair merely by
        # naming it -- and explaining a call in one host by reference to
        # another is the natural thing to write. Structured fields settle it.
        checks += 1
        one = [json.dumps({"kind": "note", "stage": "livecall",
                           "text": "new: checked in kilo; only Claude Code arms hooks",
                           "ts": "2099-01-01T00:00:00+00:00"})]
        (run_dir / name).write_text("\n".join(one) + "\n", encoding="utf-8")
        missing = mod.missing_livecalls(at)
        if ("new", "claude") not in missing:
            failures.append("заметка про kilo закрыла пару (new, claude), "
                            "просто упомянув Claude Code")
        # a note naming two hosts is ambiguous and closes neither: which one
        # it is about is exactly what the text cannot say
        checks += 1
        if ("new", "kilo") not in missing:
            failures.append("двусмысленная заметка закрыла пару по первому "
                            "попавшемуся имени хоста")

        # a fieldless note naming one host still counts: the notes written
        # before the fields existed were not ambiguous
        checks += 1
        plain = [json.dumps({"kind": "note", "stage": "livecall",
                             "text": "new: menu opened in kimi, choice lands",
                             "ts": "2099-01-01T00:00:00+00:00"})]
        (run_dir / name).write_text("\n".join(plain) + "\n", encoding="utf-8")
        if ("new", "kimi") in mod.missing_livecalls(at):
            failures.append("однозначная старая заметка перестала считаться")

        # fields win over text: the same note, addressed properly
        checks += 1
        field = [json.dumps({"kind": "note", "stage": "livecall",
                             "skill": "new", "host": "claude",
                             "text": "only Claude Code arms hooks",
                             "ts": "2099-01-01T00:00:00+00:00"})]
        (run_dir / name).write_text("\n".join(field) + "\n", encoding="utf-8")
        missing = mod.missing_livecalls(at)
        if ("new", "claude") in missing:
            failures.append("запись с полями skill/host не закрыла свою пару")
        checks += 1
        if ("new", "kilo") not in missing:
            failures.append("запись с полями закрыла чужую пару")

        # PS-059, second facet. `since` came from the tag, so a call made
        # after the tag but before the change counted as proof of the change.
        # It happened for real on 2026-08-25: the checkpoint written early in
        # the session covered a pair while testing the text as it stood before
        # two later fixes.
        tag_at = git(repo, "show", "-s", "--format=%cI", at)
        later = (repo / "skills" / "new" / "SKILL.md")
        later.write_text("v3\n", encoding="utf-8")
        commit(repo, "change new again, an hour after the tag",
               when="2099-06-01T12:00:00+00:00")
        stale_note = [json.dumps({"kind": "note", "stage": "livecall",
                                  "skill": "new", "host": "claude",
                                  "text": "called before the change landed",
                                  "ts": "2099-06-01T11:00:00+00:00"})]
        (run_dir / name).write_text("\n".join(stale_note) + "\n", encoding="utf-8")
        checks += 1
        if ("new", "claude") not in mod.missing_livecalls(at):
            failures.append(f"вызов до правки (11:00) закрыл пару, хотя скилл "
                            f"менялся в 12:00; тег стоит на {tag_at}")
        fresh_note = [json.dumps({"kind": "note", "stage": "livecall",
                                  "skill": "new", "host": "claude",
                                  "text": "called after the change landed",
                                  "ts": "2099-06-01T13:00:00+00:00"})]
        (run_dir / name).write_text("\n".join(fresh_note) + "\n", encoding="utf-8")
        checks += 1
        if ("new", "claude") in mod.missing_livecalls(at):
            failures.append("вызов после правки (13:00) не закрыл пару")

        # PS-072. The gate measured from the tag being released, and that tag
        # sits on HEAD by the program's own requirement -- so the range was
        # always empty and no pair was ever asked for. This is PS-054 facing
        # the other way: then every note was refused, then every release was
        # waved through. Both times green meant "did not ask".
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=t",
                        "-c", "user.email=t@t", "tag", "-a", "v9.1.0",
                        "-m", "release being cut"], check=True)
        checks += 1
        if mod.previous_tag("v9.1.0") != "v9.0.0":
            failures.append(f"предыдущим тегом сочли "
                            f"{mod.previous_tag('v9.1.0')!r}, а не v9.0.0")
        checks += 1
        if mod.missing_livecalls("v9.1.0") != []:
            failures.append("от выпускаемого тега диапазон обязан быть пуст — "
                            "иначе фикстура не воспроизводит дефект")
        checks += 1
        from_previous = mod.missing_livecalls(mod.previous_tag("v9.1.0"))
        if not any(n == "new" for n, _ in from_previous):
            failures.append("от предыдущего тега гейт обязан увидеть навык "
                            f"new, а увидел {sorted(from_previous)}")
        checks += 1
        if mod.previous_tag("v9.0.0") is not None:
            failures.append("у первого тега предыдущего быть не может, "
                            f"а нашли {mod.previous_tag('v9.0.0')!r}")

        print(f"{checks + 2} checks, {len(failures)} failed")
    for f in failures:
        print(f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
