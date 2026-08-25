#!/usr/bin/env python3
"""The checkpoint list must show what nothing else shows: the orphans.

`core/OUTPUT.md` opens one checkpoint, the one named after the current branch.
Everything here is about the rest of them -- a file written on a branch that is
gone reads as an ordinary row unless the program says the branch is gone, and
that row is exactly the one PS-050 was raised for.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "bin" / "primeskills-handoffs"


def run(cwd, *args, home=None):
    """HOME is always set: the register lives there, and a test that reads the
    machine's own register is testing the machine, not the change."""
    env = dict(os.environ, HOME=str(home or cwd))
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, cwd=cwd, env=env)


def register(home, *tops):
    path = Path(home) / ".primeskills" / "trees.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({str(t): "2026-08-21T00:00:00+00:00"
                                for t in tops}), encoding="utf-8")
    return path


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

    # 1. Outside a repository with nothing registered: still a refusal, but it
    #    must hand the caller the way forward. The first version stopped at
    #    "not inside a git repository", and three agents stopped with it while
    #    eight checkpoints sat one directory away (2026-08-21).
    with tempfile.TemporaryDirectory() as tmp:
        done = run(tmp)
        want(done.returncode != 0,
             "пустой реестр вне репозитория — отказ, а не пустой список")
        told = done.stdout + done.stderr
        want("реестр" in told, "отказ не называет реестр")
        want("primeskills-handoffs <путь>" in told,
             f"отказ не показывает, как назвать дерево:\n{told}")

    # 2. Outside a repository, with a tree in the register: this is the case
    #    the agents actually hit, and it must answer instead of refusing.
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as home:
        top = Path(tmp)
        repo(top)
        checkpoint(top, "master", "живой чекпоинт\n")
        register(home, top)
        done = run(Path(home), home=home)
        want(done.returncode == 0,
             f"из дома с непустым реестром ждали код 0:\n{done.stdout}{done.stderr}")
        want("master" in done.stdout and str(top) in done.stdout,
             f"чекпоинт зарегистрированного дерева не показан:\n{done.stdout}")
        want("реестр" in done.stdout,
             f"не сказано, откуда взялся список:\n{done.stdout}")

        # a named tree works from anywhere, register or no register
        done = run(Path(home), str(top), home=str(Path(home) / "empty"))
        want(done.returncode == 0 and "master" in done.stdout,
             f"дерево, названное аргументом, не показано:\n{done.stdout}")

        # a named tree that never held checkpoints says so rather than lying
        done = run(Path(home), home, home=home)
        want(done.returncode == 1,
             "каталог без .primeskills/handoff должен быть отказом")

    # 3. A register entry whose tree is gone is dropped, not crashed on
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as home:
        top = Path(tmp)
        repo(top)
        checkpoint(top, "master", "живой\n")
        register(home, top, Path(home) / "снесённое-дерево")
        done = run(Path(home), home=home)
        want(done.returncode == 0 and "master" in done.stdout,
             f"пропавшее дерево в реестре уронило список:\n{done.stdout}{done.stderr}")
        want("больше нет" in done.stdout,
             f"про пропавшее дерево реестра не сказано:\n{done.stdout}")

    # 4. An empty tree refuses in a way the skill can branch on: a message and
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

    # 5. The list itself: every checkpoint, newest first, with the date it was
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

    # 5b. Numbered, in print order and across trees: the four hosts draw a list
    #     four ways — a menu in Kimi, prose in Claude and Codex, a table in
    #     OpenCode — so the number is what makes "3" an answer anywhere.
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other, \
            tempfile.TemporaryDirectory() as home:
        one, two = Path(tmp), Path(other)
        repo(one); repo(two)
        now = time.time()
        checkpoint(one, "master", "первый\n", when=now)
        checkpoint(one, "вторая-ветка", "второй\n", when=now - 10)
        checkpoint(two, "master", "третий\n", when=now - 20)
        register(home, one, two)
        done = run(Path(home), home=home)
        numbered = [l for l in done.stdout.splitlines() if l.startswith("  [")]
        want(len(numbered) == 3,
             f"ждали три пронумерованные строки:\n{done.stdout}")
        want([l.split("]")[0] for l in numbered] == ["  [1", "  [2", "  [3"],
             f"нумерация не сквозная по деревьям:\n{done.stdout}")
        want("выбор по номеру" in done.stdout,
             f"не сказано, что выбор делается номером:\n{done.stdout}")

    # 6. The orphan. A checkpoint whose branch was deleted is still a file, and
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

    # 7. A checkpoint reached through a link out of the tree is not this tree's
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

    # PS-061. One checkpoint per tree, branches as sections inside it. A file
    # per branch multiplied: 5 of the 11 checkpoints on this machine named
    # branches that no longer existed, and a tree with several live branches
    # scattered its state across as many files.
    with tempfile.TemporaryDirectory() as tmp:
        top = Path(tmp)
        repo(top)
        git(top, "branch", "feat-a")
        single = top / ".primeskills" / "handoff" / "checkpoint.md"
        single.parent.mkdir(parents=True, exist_ok=True)
        single.write_text("# checkpoint\n\n## master\nстоим тут\n\n"
                          "## feat-a\nполовина\n\n## feat-gone\nветки нет\n",
                          encoding="utf-8")
        out = run(top).stdout
        want("master" in out and "feat-a" in out and "feat-gone" in out,
             f"разделы одного файла не перечислены:\n{out}")
        want(out.count("checkpoint.md") == 0 or "master" in out,
             f"перечислен файл вместо разделов:\n{out}")
        want("сирота" in out,
             f"раздел без ветки не помечен сиротой:\n{out}")
        want(len([l for l in out.splitlines() if l.strip().startswith("[")]) == 3,
             f"ожидали три пронумерованных раздела:\n{out}")

        # a legacy per-branch file is still listed, so nothing written before
        # this change disappears from the picker
        checkpoint(top, "feat-legacy", "старый формат")
        out = run(top).stdout
        want("feat-legacy" in out,
             f"старый файл-на-ветку перестал показываться:\n{out}")

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
