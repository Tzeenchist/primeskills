#!/usr/bin/env python3
"""The adherence reader must reproduce verdicts that were derived by hand.

One fixture is a real session reduced to its tool calls -- the SHOP-009 run of
2026-08-17, where `build` was invoked and its red phase was not honoured. That
verdict was established by reading the transcript manually before this tool
existed, so it is the regression that matters most.
"""
import subprocess
import sys
import tempfile
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
        ".gstack/checkpoints",  # the fragment, not one account's home
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
    tmp_dir = tempfile.TemporaryDirectory()
    tmp = tmp_dir.name

    for name, wanted in sorted(EXPECT.items()):
        path = FIX / name
        if not path.is_file():
            failures.append(f"{name}: фикстуры нет")
            continue
        # A fixture about writing outside the repository has to name the home of
        # whoever is running it. Hard-coding one account made the fixture pass
        # on one machine and silently stop testing anything on any other, so the
        # path is a placeholder and is filled in here.
        raw = path.read_text(encoding="utf-8")
        if "{HOME}" in raw:
            path = Path(tmp) / name
            path.write_text(raw.replace("{HOME}", str(Path.home())), encoding="utf-8")
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

    # --all must read every session, not one per project. The defect it guards
    # against read 3 files out of 44 and reported the result as "--all".
    home = Path(tmp) / "home"
    project = home / ".claude" / "projects" / "-srv-two-sessions"
    project.mkdir(parents=True)
    call = ('{"type": "assistant", "message": {"content": [{"type": "tool_use", '
            '"name": "Bash", "input": {"command": "ls"}}]}}\n')
    for n in ("older.jsonl", "newer.jsonl"):
        (project / n).write_text(call, encoding="utf-8")
    import os
    older, newer = project / "older.jsonl", project / "newer.jsonl"
    os.utime(older, (1, 1))

    env = dict(os.environ, HOME=str(home))
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), "--all"],
                       capture_output=True, text=True, env=env)
    if "сессий: 2" not in p.stdout:
        failures.append(f"--all прочитал не все сессии:\n{p.stdout}")

    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), "--all", "--newest"],
                       capture_output=True, text=True, env=env)
    if "сессий: 1" not in p.stdout:
        failures.append(f"--newest должен оставить одну сессию:\n{p.stdout}")

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
