#!/usr/bin/env python3
"""The run record must survive the thing it exists to survive: a lost session.

Every check here runs the tool as a fresh process against a scratch repository,
because that is the failure being fixed — state that only existed while one
agent was still running.
"""
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / "bin" / "primeskills-run"


def run(repo, *args):
    p = subprocess.run([sys.executable, str(RUN), *args],
                       capture_output=True, text=True, cwd=repo)
    return p.returncode, p.stdout + p.stderr


def main():
    failures = []
    checks = 0
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "work"], cwd=repo, check=True)
        (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-q", "-m", "init"],
                       cwd=repo, check=True)

        code, out = run(repo, "start")
        checks += 1
        # the name carries a hash of the full branch name, so `feature/a` and
        # `feature-a` cannot share a journal — and its permissions
        records = list((repo / ".primeskills" / "run").glob("work-*.jsonl"))
        record = records[0] if records else repo / ".primeskills" / "run" / "missing"
        if code != 0 or not record.is_file():
            failures.append(f"start: exit {code}, no record at {record}\n{out}")

        # the log is local by construction: its own .gitignore hides it, so a
        # command line never reaches a commit by accident
        checks += 1
        ignored = subprocess.run(["git", "status", "--porcelain"], cwd=repo,
                                 capture_output=True, text=True).stdout
        if ".primeskills" in ignored:
            failures.append("журнал прогона виден для git — он должен быть локальным")

        checks += 1
        run(repo, "note", "verify", "pytest -q: 12 passed, exit 0")
        if "12 passed" not in record.read_text(encoding="utf-8"):
            failures.append("note: запись не попала в журнал")

        # evidence is bound to the tree: one byte and it is no longer about it
        checks += 1
        code, out = run(repo, "check", "verify")
        if code != 0 or "current" not in out:
            failures.append(f"check сразу после записи: exit {code}, {out.strip()!r}")
        (repo / "seed.txt").write_text("changed\n", encoding="utf-8")
        checks += 1
        code, out = run(repo, "check", "verify")
        if code != 2 or "STALE" not in out:
            failures.append(f"один байт не сделал свидетельство протухшим: {out.strip()!r}")
        checks += 1
        (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
        code, out = run(repo, "check", "verify")
        if code != 0:
            failures.append("возврат дерева не вернул свидетельство в силу")
        checks += 1
        code, out = run(repo, "check", "vet")
        if code != 1:
            failures.append("check по незаписанной стадии должен отличаться от протухшей")

        # G9: the counter belongs to the file, so a new process keeps counting
        for expected in (1, 2):
            code, out = run(repo, "fail", "flaky export")
            checks += 1
            if code != 0 or f"{expected} of 3" not in out:
                failures.append(f"fail #{expected}: exit {code}, said {out.strip()!r}")
        code, out = run(repo, "fail", "flaky export")
        checks += 1
        if code != 3:
            failures.append(f"fail #3: exit {code}, expected 3 (breaker)")

        code, out = run(repo, "fail", "slow query")
        checks += 1
        if code != 0 or "1 of 3" not in out:
            failures.append(f"second problem shares a counter: {out.strip()!r}")

        # A breaker its own subject can lift is a reminder, not a breaker, so
        # `clear` sits on the ladder: refused without a grant, spent by use.
        checks += 1
        code, out = run(repo, "clear", "flaky export")
        if code == 0 or "not granted" not in out:
            failures.append(f"clear без гранта прошёл: exit {code}, {out.strip()!r}")
        checks += 1
        code, out = run(repo, "fail", "flaky export")
        if code != 3:
            failures.append(f"отказанный clear всё же обнулил счётчик: {out.strip()!r}")

        checks += 1
        run(repo, "grant", "clear", "--target", "flaky export",
            "владелец разрешил сбросить счётчик по этой проблеме")
        code, out = run(repo, "clear", "flaky export")
        if code != 0 or "cleared" not in out:
            failures.append(f"clear с грантом не сработал: exit {code}, {out.strip()!r}")
        checks += 1
        code, out = run(repo, "fail", "flaky export")
        if "1 of 3" not in out:
            failures.append(f"clear: counter not reset, said {out.strip()!r}")

        # the grant is single-use: the same yes must not clear a second time
        checks += 1
        run(repo, "fail", "flaky export")
        run(repo, "fail", "flaky export")
        code, out = run(repo, "clear", "flaky export")
        if code == 0:
            failures.append(f"одноразовый грант потратился дважды: {out.strip()!r}")

        # and a yes for one problem is not a yes for another
        checks += 1
        run(repo, "grant", "clear", "--target", "flaky export", "снова разрешил")
        code, out = run(repo, "clear", "slow query")
        if code == 0 or "not a permission for another" not in out:
            failures.append(f"грант на одну проблему снял чужой счётчик: {out.strip()!r}")

        checks += 1
        text = record.read_text(encoding="utf-8")
        if text.count('"kind": "fail"') < 4 or "12 passed" not in text:
            failures.append("журнал переписан вместо дописывания")

        # A cloned repository can ship `.primeskills` as a link and take both
        # halves of the journal: the writes land where it chose, and the grants
        # it planted there are read as the user's own.
        outside = Path(tmp) / "outside"
        outside.mkdir(exist_ok=True)
        record.rename(record.with_suffix(".kept"))
        record.symlink_to(outside / "planted.jsonl")
        checks += 1
        code, out = run(repo, "grant", "deploy", "--target", "prod", "подложено")
        if code == 0 or "symlink" not in out:
            failures.append(f"журнал-симлинк принят: exit {code}, {out.strip()!r}")
        checks += 1
        if (outside / "planted.jsonl").exists():
            failures.append("запись ушла наружу по симлинку")
        record.unlink()
        record.with_suffix(".kept").rename(record)

        # a branch with a slash must not become a directory
        subprocess.run(["git", "checkout", "-q", "-b", "feat/thing"], cwd=repo, check=True)
        checks += 1
        code, out = run(repo, "start")
        if code != 0 or not list((repo / ".primeskills" / "run").glob("feat-thing-*.jsonl")):
            failures.append(f"branch with a slash: exit {code}\n{out}")

    # evidence must expire when an untracked file's CONTENT changes, not only
    # when one appears: the digest used to carry names from `git status` and a
    # rewritten new module left an old PASS looking current
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "work"], cwd=repo, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "--allow-empty", "-m", "seed"],
                       cwd=repo, check=True)
        (repo / "new.py").write_text("first\n", encoding="utf-8")
        run(repo, "note", "verify", "green")
        checks += 1
        code, out = run(repo, "check", "verify")
        if code != 0:
            failures.append(f"свежая запись прочиталась как протухшая:\n{out}")
        (repo / "new.py").write_text("second\n", encoding="utf-8")
        checks += 1
        code, out = run(repo, "check", "verify")
        if code != 2 or "STALE" not in out:
            failures.append(f"правка untracked-файла не протухила запись: {code}\n{out}")

    # the G9 breaker counts a problem, not a phrasing of it
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "work"], cwd=repo, check=True)
        run(repo, "fail", "login returns 500")
        checks += 1
        code, out = run(repo, "fail", "The login  RETURNS 500!")
        if "2 of 3" not in out:
            failures.append(f"переформулировка обнулила счётчик G9:\n{out}")
        checks += 1
        code, out = run(repo, "fail", "css margin is wrong")
        if "1 of 3" not in out:
            failures.append(f"другая проблема попала в чужой счётчик:\n{out}")
        # и обратная ошибка: близкие по словам, но разные баги должны считаться
        # порознь — склейка тормозит работу на полутора настоящих попытках
        checks += 1
        run(repo, "fail", "export renders 4 pages")
        code, out = run(repo, "fail", "export fails on 4 pages")
        if "1 of 3" not in out:
            failures.append(f"разные баги склеены в один счётчик:\n{out}")

    # the authority ladder: a rung is open only while the record says so
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "work"], cwd=repo, check=True)
        checks += 1
        code, out = run(repo, "may", "commit")
        if code != 1:
            failures.append(f"незапрошенный commit разрешён: {code}\n{out}")
        checks += 1
        code, out = run(repo, "grant", "commit")
        if code == 0:
            failures.append("мандат без области принят")
        run(repo, "grant", "commit", "ветка feature/x, до PR")
        checks += 1
        code, out = run(repo, "may", "commit")
        if code != 0 or "feature/x" not in out:
            failures.append(f"выданный мандат не читается: {code}\n{out}")
        checks += 1
        code, out = run(repo, "may", "push")
        if code != 1:
            failures.append("commit открыл push — ступень подразумевает следующую")
        run(repo, "revoke", "commit")
        checks += 1
        code, out = run(repo, "may", "commit")
        if code != 1:
            failures.append("отозванный мандат всё ещё действует")
        checks += 1
        code, out = run(repo, "grant", "deploy-everything", "всё")
        if code == 0:
            failures.append("выдуманная ступень принята")
        checks += 1
        run(repo, "grant", "push", "до PR")
        code, out = run(repo, "show")
        if "Заявленные полномочия" not in out or "до PR" not in out:
            failures.append(f"открытые ступени не видны в записи:\n{out}")

        # чувствительная ступень обязана называть цель, действует один раз и
        # не открывает дверь соседнему окружению
        checks += 1
        code, out = run(repo, "grant", "deploy", "выкатить")
        if code == 0:
            failures.append("deploy выдан без --target")
        run(repo, "grant", "deploy", "--target", "staging", "выкатить релиз")
        checks += 1
        code, out = run(repo, "may", "deploy", "--target", "production")
        if code != 1:
            failures.append(f"мандат на staging пропустил production:\n{out}")
        checks += 1
        code, out = run(repo, "may", "deploy", "--target", "staging")
        if code != 0:
            failures.append(f"мандат на свою цель не сработал:\n{out}")
        checks += 1
        code, out = run(repo, "may", "deploy", "--target", "staging")
        if code != 1:
            failures.append("одноразовый мандат сработал дважды")
        checks += 1
        run(repo, "grant", "commit", "--for", "0", "истёкший")
        code, out = run(repo, "may", "commit")
        # истёкший мандат называет причину, а не читается как «не выдан»:
        # иначе пользователя отправляют искать разрешение, которое он уже давал
        if code != 1 or "истёк" not in out:
            failures.append(f"истёкший мандат не назвал причину: {code}\n{out}")

    # grants live in one record per repository (PS-047): written on one branch,
    # visible from another — land and merge cross branches by design. Evidence
    # journals stay per branch: slug() alone used to map feature/a and
    # feature-a to one file
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "feature/a"], cwd=repo, check=True)
        # без коммита имя ветки не разрешается и обе читаются как detached
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "--allow-empty", "-m", "seed"],
                       cwd=repo, check=True)
        run(repo, "note", "verify", "первая ветка")
        run(repo, "grant", "push", "выписан на feature/a")
        subprocess.run(["git", "checkout", "-q", "-b", "feature-a"], cwd=repo, check=True)
        checks += 1
        code, out = run(repo, "may", "push")
        if code != 0:
            failures.append(f"грант не виден с соседней ветки того же репозитория:\n{out}")
        run(repo, "note", "verify", "вторая ветка")
        checks += 1
        names = sorted(p.name for p in (repo / ".primeskills" / "run").glob("*.jsonl")
                       if p.name != "repo.jsonl")
        if len(names) != 2:
            failures.append(f"две ветки делят журнал доказательств: {names}")

        # переходный период: грант, дописанный старой версией в журнал ветки,
        # читается — обновление посреди работы не гасит открытые ярусы
        code, out = run(repo, "start")
        branch_record = Path(out.strip())
        legacy = {"kind": "grant", "rung": "merge", "scope": "записан старой версией",
                  "target": None, "lifetime": 480, "branch": "feature/a", "once": False,
                  "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "commit": "x", "state": "y"}
        with branch_record.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(legacy, ensure_ascii=False) + "\n")
        checks += 1
        code, out = run(repo, "may", "merge")
        if code != 0 or "старой версией" not in out:
            failures.append(f"грант из записи ветки не читается в переходный период:\n{out}")

    # --peek asks without spending: the pre-step check must not burn the
    # one-use mandate it only confirms (PS-047), and a plain `may` still spends
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "work"], cwd=repo, check=True)
        run(repo, "grant", "deploy", "--target", "staging", "выкатить релиз")
        checks += 1
        code, out = run(repo, "may", "deploy", "--target", "staging", "--peek")
        if code != 0 or "spent" in out:
            failures.append(f"--peek потратил мандат: {code}\n{out}")
        checks += 1
        code, out = run(repo, "may", "deploy", "--target", "staging")
        if code != 0 or "spent by this check" not in out:
            failures.append(f"мандат не дожил до шага после --peek: {code}\n{out}")

    # an unreadable line is a refusal naming the line, not a silent skip:
    # a truncated `spent` would resurrect a one-use mandate, and the fence
    # hook declines a command when the journal does not answer
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "work"], cwd=repo, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "--allow-empty", "-m", "seed"],
                       cwd=repo, check=True)
        run(repo, "grant", "deploy", "--target", "staging", "выкатить")
        run(repo, "may", "deploy", "--target", "staging")  # строка 2 repo.jsonl — spent
        ledger = repo / ".primeskills" / "run" / "repo.jsonl"
        lines = ledger.read_text(encoding="utf-8").splitlines()
        lines[1] = "{оборвано"
        ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
        checks += 1
        code, out = run(repo, "may", "deploy", "--target", "staging", "--peek")
        if code == 0 or "строка 2" not in out:
            failures.append(f"битая строка spent воскресила мандат: {code}\n{out}")
        run(repo, "note", "verify", "green")
        record = next((repo / ".primeskills" / "run").glob("work-*.jsonl"))
        with record.open("a", encoding="utf-8") as fh:
            fh.write("не json\n")
        for args in (("check", "verify"), ("show",)):
            checks += 1
            code, out = run(repo, *args)
            if code == 0 or "строка 2" not in out:
                failures.append(f"{args[0]}: битая строка не дала отказ с номером: {code}\n{out}")

    # outside a repository it must refuse, not write somewhere surprising
    with tempfile.TemporaryDirectory() as bare:
        checks += 1
        code, out = run(bare, "start")
        if code == 0:
            failures.append("start outside a git repository did not fail")

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
