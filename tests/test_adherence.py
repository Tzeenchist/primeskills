#!/usr/bin/env python3
"""The adherence reader must reproduce verdicts that were derived by hand.

One fixture is a real session reduced to its tool calls -- the SHOP-009 run of
2026-08-17, where `build` was invoked and its red phase was not honoured. That
verdict was established by reading the transcript manually before this tool
existed, so it is the regression that matters most.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "bin" / "primeskills-adherence"
FIX = ROOT / "tests" / "fixtures" / "transcripts"

# fixture -> substrings that must all appear in the report
EXPECT = {
    "live-build-red-phase.jsonl": [
        "вызовов скиллов: 1 (build)",
        "core/ прочитан: действие #1",
        "[НАРУШЕН] красная фаза",
        "код #68 раньше теста #82",
    ],
    "build-red-phase-ok.jsonl": [
        "[ok  ] красная фаза",
        "тест #3 раньше кода #5",
        "доля 100%",
    ],
    "readonly-violation.jsonl": [
        "[НАРУШЕН] не пишет (G7)",
        "sed -i",
    ],
    "verify-and-debug.jsonl": [
        "[НАРУШЕН] прогон состоялся (G4)",
        "[НАРУШЕН] воспроизведение до правки",
        "вызовов скиллов: 2 (debug, verify)",
    ],
    "git-hygiene-violation.jsonl": [
        "[НАРУШЕН] гигиена git (G11)",
        "git add -A",
        "[ok  ] дифф прочитан до коммита",
    ],
    "handoff-home.jsonl": [
        "[НАРУШЕН] чекпоинт в репозитории, не в доме",
        "/home/admin/.gstack",
    ],
    "flow-order-violation.jsonl": [
        "[НАРУШЕН] порядок цепочки",
        "land → deploy → merge",
    ],
    "green-by-test-edit.jsonl": [
        "[НАРУШЕН] зелень не куплена правкой теста",
        "test_totals.py",
    ],
    "g17-two-step.jsonl": [
        # resolve, print, act -- the pattern the guardrail describes
        "[ok  ] цель разрешена до разрушения (G17)",
        "цель напечатана предыдущей командой",
        # printed one target, destroyed another: the incident G17 came from
        "[НАРУШЕН] цель разрешена до разрушения (G17)",
        "dropdb prod_shop",
    ],
    "land-and-g17.jsonl": [
        "[НАРУШЕН] дифф прочитан до коммита (G6)",
        # the printed target passes, the bare one does not
        "[ok  ] цель разрешена до разрушения (G17)",
        "[НАРУШЕН] цель разрешена до разрушения (G17)",
    ],
}

# a report must never claim a verdict the fixture cannot support
FORBIDDEN = {
    "build-red-phase-ok.jsonl": ["НАРУШЕН"],
    "live-build-red-phase.jsonl": ["[ok  ] красная фаза"],
}


def main():
    failures = []
    checks = 0

    for name, wanted in sorted(EXPECT.items()):
        path = FIX / name
        if not path.is_file():
            failures.append(f"{name}: фикстуры нет")
            continue
        p = subprocess.run([sys.executable, str(TOOL), str(path)],
                           capture_output=True, text=True)
        out = p.stdout + p.stderr
        for text in wanted:
            checks += 1
            if text not in out:
                failures.append(f"{name}: нет {text!r}\n{out}")
        for text in FORBIDDEN.get(name, []):
            checks += 1
            if text in out:
                failures.append(f"{name}: не должно быть {text!r}")

    # no arguments must explain itself rather than crash
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True)
    if p.returncode != 0 or "primeskills-adherence" not in p.stdout:
        failures.append("без аргументов: ожидалась справка")

    # a file that is not a transcript must not be reported as a clean session
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), str(ROOT / "README.md")],
                       capture_output=True, text=True)
    if p.returncode != 0:
        failures.append("нежурнальный файл уронил инструмент")

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
