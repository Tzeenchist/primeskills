#!/usr/bin/env python3
"""The guide must be generated, bilingual, and honest about the language."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "bin" / "primeskills-help"


def run(args, home):
    env = dict(os.environ, HOME=home)
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, env=env)


def main():
    failures, checks = [], 0
    names = sorted(p.parent.name for p in ROOT.glob("skills/*/SKILL.md"))

    with tempfile.TemporaryDirectory() as home:
        checks += 1
        if run(["--which-lang"], home).stdout.strip() != "unset":
            failures.append("свежий дом: язык должен быть 'unset'")

        checks += 1
        body = run([], home).stdout
        if "how to use this set" not in body:
            failures.append("справка должна печататься по-английски")

        checks += 1
        if "No language is remembered yet" not in body:
            failures.append("без выбора справка не сообщает, что язык не задан")

        # any language, not a list of two: a fixed list is what limited this
        for value in ("ru", "日本語", "Português"):
            checks += 1
            run(["--set-lang", value], home)
            if run(["--which-lang"], home).stdout.strip() != value:
                failures.append(f"язык {value!r} не запомнился")

        checks += 1
        if f"remembered as: Português" not in run([], home).stdout:
            failures.append("справка не называет запомненный язык")

        checks += 1
        if run(["--set-lang"], home).returncode == 0:
            failures.append("--set-lang без значения должен падать")
        checks += 1
        if run(["--set-lang", "x" * 40], home).returncode == 0:
            failures.append("абзац вместо языка должен отвергаться")

        # every skill appears: a guide that silently drops one is worse than none
        checks += 1
        out = run([], home).stdout
        missing = [n for n in names if f"`/{n}`" not in out]
        if missing:
            failures.append(f"в справке нет навыков {missing}")

        checks += 1
        if "Not yet placed" in out:
            failures.append("навыки попали в запасной раздел")

        # both directions of the relation
        checks += 1
        # the declared order is the order the procedure runs, conditionals in place
        if "runs: `/verify` → `/vet` → `/probe` (if needed)" not in out:
            failures.append("последовательность не показывает цепочку в списке")
        checks += 1
        if "part of: `/close`, `/release`" not in out:
            failures.append("навык не показывает, куда входит")
        checks += 1
        if "(if needed)" not in out:
            failures.append("условное звено не помечено")
        checks += 1
        if "<br>" in out:
            failures.append("в тексте осталась разметка HTML")
        checks += 1
        if "primeskills-help --set-lang" not in out:
            failures.append("справка не говорит, как сменить язык")

    # the preference must never be written outside the given HOME
    with tempfile.TemporaryDirectory() as home:
        checks += 1
        real = Path.home() / ".primeskills" / "lang"
        before = real.read_text(encoding="utf-8") if real.is_file() else None
        run(["--set-lang", "test-isolation"], home)
        after = real.read_text(encoding="utf-8") if real.is_file() else None
        if before != after:
            failures.append("настройка утекла из временного HOME в настоящий")

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
