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
        if run([], home).stdout.count("how to use this set") != 1:
            failures.append("без выбора язык по умолчанию должен быть английским")

        for lang, marker in (("ru", "как этим пользоваться"), ("en", "how to use this set")):
            checks += 1
            out = run(["--lang", lang], home).stdout
            if marker not in out:
                failures.append(f"--lang {lang}: нет заголовка {marker!r}")

        checks += 1
        if run(["--which-lang"], home).stdout.strip() != "unset":
            failures.append("--lang не должен запоминать выбор")

        checks += 1
        run(["--set-lang", "ru"], home)
        if run(["--which-lang"], home).stdout.strip() != "ru":
            failures.append("--set-lang не запомнил язык")

        checks += 1
        if "как этим пользоваться" not in run([], home).stdout:
            failures.append("запомненный язык не применяется без флага")

        checks += 1
        if run(["--set-lang", "de"], home).returncode == 0:
            failures.append("неизвестный язык должен отвергаться")

        # every skill appears, in both languages: a guide that silently drops a
        # skill is worse than no guide
        for lang in ("en", "ru"):
            out = run(["--lang", lang], home).stdout
            missing = [n for n in names if f"`/{n}`" not in out]
            checks += 1
            if missing:
                failures.append(f"{lang}: в справке нет навыков {missing}")

        checks += 1
        if "primeskills-help --set-lang en" not in run(["--lang", "ru"], home).stdout:
            failures.append("русская справка не говорит, как сменить язык")

        checks += 1
        ru = run(["--lang", "ru"], home).stdout
        if "skills" in ru.rsplit("---", 1)[-1]:
            failures.append("подпись русской справки осталась английской")

        # the fallback bucket is a safety net, not a place skills live
        checks += 1
        for lang in ("en", "ru"):
            out = run(["--lang", lang], home).stdout
            bucket = "Not yet placed" if lang == "en" else "Ещё не поставлены"
            if bucket in out:
                failures.append(f"{lang}: навыки попали в запасной раздел")

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
