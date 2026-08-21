#!/usr/bin/env python3
"""The checkpoint list must show what nothing else shows: the orphans.

`core/OUTPUT.md` opens one checkpoint, the one named after the current branch.
Everything here is about the rest of them -- a file written on a branch that is
gone reads as an ordinary row unless the program says the branch is gone, and
that row is exactly the one PS-050 was raised for.
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "bin" / "primeskills-handoffs"


def run(cwd):
    return subprocess.run([sys.executable, str(TOOL)], capture_output=True,
                          text=True, cwd=cwd)


def git(cwd, *args):
    return subprocess.run(("git", *args), capture_output=True, text=True,
                          cwd=cwd)


def repo(top):
    """A git repository with one commit, so branches can exist."""
    git(top, "init", "-b", "master")
    git(top, "config", "user.email", "test@example.invalid")
    git(top, "config", "user.name", "test")
    (top / "README.md").write_text("x\n", encoding="utf-8")
    git(top, "add", "README.md")
    git(top, "commit", "-m", "первый")


def checkpoint(top, branch, text, when=None):
    path = top / ".primeskills" / "handoff" / f"{branch}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if when is not None:
        os.utime(path, (when, when))
    return path


def main():
    failures, checks = [], 0

    def want(condition, complaint):
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(complaint)

    # 1. Outside a repository there is no tree to list, and saying "no
    #    checkpoints" there would be a claim about a place we never looked.
    with tempfile.TemporaryDirectory() as tmp:
        done = run(tmp)
        want(done.returncode != 0,
             "вне репозитория программа должна отказывать, а не печатать пустой список")
        want("репозит" in done.stdout + done.stderr,
             "отказ вне репозитория не называет причину")

    # 2. An empty tree refuses in a way the skill can branch on: a message and
    #    a non-zero code. "Nothing to show" printed with success is how a
    #    caller learns to ignore the answer.
    with tempfile.TemporaryDirectory() as tmp:
        top = Path(tmp)
        repo(top)
        done = run(top)
        want(done.returncode == 1,
             f"пустое дерево: ждали код 1, получили {done.returncode}")
        want(".primeskills/handoff" in done.stdout,
             "отказ на пустом дереве не называет каталог, куда пишутся чекпоинты")

        # a directory that exists but holds nothing readable is the same answer
        (top / ".primeskills" / "handoff").mkdir(parents=True)
        (top / ".primeskills" / "handoff" / "заметка.txt").write_text(
            "не чекпоинт\n", encoding="utf-8")
        done = run(top)
        want(done.returncode == 1,
             "каталог без .md — тоже отказ")
        want("заметка" not in done.stdout,
             "в список попал файл, который не чекпоинт")

    # 3. The list itself: every checkpoint, newest first, with the date it was
    #    last touched and the branch it belongs to.
    with tempfile.TemporaryDirectory() as tmp:
        top = Path(tmp)
        repo(top)
        now = time.time()
        checkpoint(top, "master", "старый чекпоинт\n" * 3, when=now - 86400)
        checkpoint(top, "feature", "свежий чекпоинт\n" * 5, when=now)
        git(top, "branch", "feature")
        done = run(top)
        want(done.returncode == 0,
             f"список: ждали код 0, получили {done.returncode}\n{done.stdout}")
        # padded so a program that printed nothing fails the check it broke,
        # instead of taking the test down with an IndexError and reporting
        # neither this one nor the ones after it
        lines = [l for l in done.stdout.splitlines() if l.startswith("  ")] + ["", ""]
        want(len(lines) == 4, f"ждали две строки списка, вышло {len(lines) - 2}:\n{done.stdout}")
        want("feature" in lines[0],
             f"свежий чекпоинт должен стоять первым:\n{done.stdout}")
        want("master" in lines[1],
             f"старый чекпоинт должен стоять вторым:\n{done.stdout}")
        want(time.strftime("%Y-%m-%d", time.localtime(now)) in lines[0],
             f"строка без даты последнего обновления:\n{done.stdout}")

        # the current branch is named, so the reader can see which one the
        # session would have opened by itself
        want("текущая ветка" in done.stdout,
             f"чекпоинт текущей ветки не помечен:\n{done.stdout}")

    # 4. The orphan. A checkpoint whose branch was deleted is still a file, and
    #    without a mark it is indistinguishable from a live one.
    with tempfile.TemporaryDirectory() as tmp:
        top = Path(tmp)
        repo(top)
        checkpoint(top, "master", "живой\n")
        checkpoint(top, "смерженная-ветка", "сирота\n")
        done = run(top)
        want("сирота" in done.stdout,
             f"чекпоинт без ветки не помечен как сирота:\n{done.stdout}")
        want(done.stdout.count("←") == 2,
             f"пометок должно быть две — текущая и сирота:\n{done.stdout}")

    # 5. A checkpoint reached through a link out of the tree is not this tree's
    #    checkpoint. It becomes the next agent's opening context, so it is
    #    skipped and named, never listed as one of ours (`primeskills-run` uses
    #    the same rule for the run journal).
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
        top = Path(tmp)
        repo(top)
        checkpoint(top, "master", "свой\n")
        planted = Path(outside) / "чужой.md"
        planted.write_text("подложенный текст\n", encoding="utf-8")
        link = top / ".primeskills" / "handoff" / "чужой.md"
        link.symlink_to(planted)
        done = run(top)
        want("пропущен" in done.stdout,
             f"ссылка наружу должна быть названа пропущенной:\n{done.stdout}")
        rows = [l for l in done.stdout.splitlines()
                if l.startswith("  ") and "пропущен" not in l]
        want(len(rows) == 1,
             f"в списке должен остаться один свой чекпоинт:\n{done.stdout}")

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
