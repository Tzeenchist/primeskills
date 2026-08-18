#!/usr/bin/env python3
"""The run record must survive the thing it exists to survive: a lost session.

Every check here runs the tool as a fresh process against a scratch repository,
because that is the failure being fixed — state that only existed while one
agent was still running.
"""
import subprocess
import sys
import tempfile
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
        record = repo / ".primeskills" / "run" / "work.jsonl"
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

        checks += 1
        run(repo, "clear", "flaky export")
        code, out = run(repo, "fail", "flaky export")
        if "1 of 3" not in out:
            failures.append(f"clear: counter not reset, said {out.strip()!r}")

        checks += 1
        text = record.read_text(encoding="utf-8")
        if text.count('"kind": "fail"') < 4 or "12 passed" not in text:
            failures.append("журнал переписан вместо дописывания")

        # a branch with a slash must not become a directory
        subprocess.run(["git", "checkout", "-q", "-b", "feat/thing"], cwd=repo, check=True)
        checks += 1
        code, out = run(repo, "start")
        if code != 0 or not (repo / ".primeskills" / "run" / "feat-thing.jsonl").is_file():
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
        if "## Authority" not in out or "до PR" not in out:
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
        if code != 1:
            failures.append(f"истёкший мандат всё ещё действует:\n{out}")

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
