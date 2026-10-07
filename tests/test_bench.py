#!/usr/bin/env python3
"""The benchmark must be reproducible from a checkout: PS-037 п.2.

Run 7's own record said the split-bill stand shipped with its solution and
fifteen tests where the task declares three -- nobody could re-run the
experiment from a clean checkout. These checks hold the rebuilt stands and the
harness to what the log promises: pristine fixtures that start green and
unsolved, graders whose exit code means what their printout says, and an arm
order that is randomised but reproducible from a seed.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "bench"


def run(cmd, **kw):
    return subprocess.run([sys.executable] + [str(c) for c in cmd],
                          capture_output=True, text=True, **kw)


def test_split_bill_pristine(failures):
    """Three green tests, no solution of the new feature, no rounding fix."""
    task = BENCH / "task-split-bill"
    src = (task / "split_bill.py").read_text(encoding="utf-8")
    tests = (task / "test_split_bill.py").read_text(encoding="utf-8")
    if "split_by_weights" in src:
        failures.append("split_bill.py содержит готовый ответ новой функции")
    if tests.count("def test_") != 3:
        failures.append(f"в тестах {tests.count('def test_')} функций, заявлено три")
    # the gate installs nothing (workflow rule), so the fixture is run by a
    # ten-line collector here, not by pytest: green must not cost a dependency
    sys.path.insert(0, str(task))
    try:
        mod = __import__("test_split_bill")
        ran = 0
        for name in dir(mod):
            if name.startswith("test_"):
                getattr(mod, name)()
                ran += 1
        if ran != 3:
            failures.append(f"запущено {ran} тестов фикстуры, а не три")
    except Exception as exc:
        failures.append(f"фикстура split-bill не зелёная: {exc!r}")
    finally:
        sys.path.pop(0)
        sys.modules.pop("test_split_bill", None)


def test_grader_exit_code_means_fail(failures):
    """A grader that prints FAIL and exits 0 trains gates to ignore it."""
    for name, args in (
        ("orders-grader.py", [str(BENCH / "task-orders" / "app.db")]),
        ("invoice-grader.py", []),
    ):
        task = BENCH / ("task-orders" if "orders" in name else "task-invoice")
        # the pristine stand ships unsolved: the grader must refuse it loudly
        p = run([BENCH / name, *args], cwd=task)
        if p.returncode == 0:
            failures.append(f"{name}: на нерешённой задаче exit 0")


def test_wilson_interval():
    """Known values, not self-consistency: the interval guards PS-009 data."""
    sys.path.insert(0, str(BENCH))
    import harness
    lo, hi = harness.wilson(passed=4, total=4)
    assert round(lo, 3) == 0.510 and round(hi, 3) == 1.0, (lo, hi)
    lo, hi = harness.wilson(passed=0, total=10)
    assert round(lo, 3) == 0.0 and round(hi, 3) == 0.278, (lo, hi)


def test_arm_order_reproducible(failures):
    """Same seed, same order; different seed may differ; every unit present."""
    sys.path.insert(0, str(BENCH))
    import harness
    a = harness.plan_arms(["set", "bare"], repeats=3, seed=7)
    b = harness.plan_arms(["set", "bare"], repeats=3, seed=7)
    c = harness.plan_arms(["set", "bare"], repeats=3, seed=8)
    if a != b:
        failures.append("одинаковый seed дал разный порядок плеч")
    if sorted(a) != sorted(b):  # same multiset regardless
        failures.append("план потерял единицы прогона")
    if len(a) != 6 or len(set(a)) < 2:
        failures.append(f"план {a} не покрывает плечи и повторы")
    # different seed: not required to differ, but the call must be legal
    if not c or any(x.split("#")[0] not in ("set", "bare") for x in c):
        failures.append(f"план содержит посторонние плечи: {c}")


def test_adherence_run(failures):
    """PS-086: the seed reproduces the order, the printout is read verdict by
    verdict, and the table counts only the skill the scenario called."""
    sys.path.insert(0, str(BENCH))
    import adherence_run as ar
    if ar.plan(["a", "b"], ["x", "y"], 3, 7) != ar.plan(["a", "b"], ["x", "y"], 3, 7):
        failures.append("adherence_run.plan: один seed дал два порядка")
    printout = (
        "/x.jsonl\n  core/ прочитан: действие #2\n"
        "  · vet (вызван #1, 3 действий в пролёте)\n"
        "      [НАРУШЕН] не пишет (G16) — #2 shell: tee x\n"
        "  · build (вызван #4, 9 действий в пролёте)\n"
        "      [ok  ] красная фаза (P7, TDD) — тест до кода\n"
        "      [н/п ] гигиена git (G14) — git не трогали\n")
    rows, core = ar.parse_report(printout)
    want = [("vet", "не пишет (G16)", "violated"),
            ("build", "красная фаза (P7, TDD)", "ok"),
            ("build", "гигиена git (G14)", "na")]
    if rows != want or not core:
        failures.append(f"adherence_run.parse_report: {rows}, core={core}")
    if ar.parse_report("  core/ прочитан: нет\n")[1]:
        failures.append("adherence_run.parse_report: «нет» прочитано как чтение core/")
    if ar.skill_called("/x/-tmp-verify-2/s.jsonl\n  вызовов скиллов: 0\n", "verify"):
        failures.append("adherence_run.skill_called: имя в пути принято за вызов")
    if not ar.skill_called("  вызовов скиллов: 2 (build, verify)\n", "verify"):
        failures.append("adherence_run.skill_called: вызов из строки счёта не виден")
    data = {"arms": ["a"], "units": [{
        "arm": "a", "scenario": "build", "session": "s", "skill_seen": True,
        "core_read": True, "status": "done",
        "verdicts": [{"skill": s, "rule": r, "verdict": v} for s, r, v in rows]}]}
    table = ar.report(data)
    if "не пишет" in table:
        failures.append("adherence_run.report: вердикт чужого навыка попал в таблицу")
    if "гигиена" in table:
        failures.append("adherence_run.report: н/п посчитано в таблице")
    if "| build | красная фаза (P7, TDD) | 1/1" not in table:
        failures.append(f"adherence_run.report: нет строки красной фазы:\n{table}")


def main():
    failures = []
    test_split_bill_pristine(failures)
    test_grader_exit_code_means_fail(failures)
    try:
        test_wilson_interval()
    except AssertionError as exc:
        failures.append(f"wilson: {exc}")
    except Exception as exc:  # harness missing entirely is also a red phase
        failures.append(f"harness: {exc!r}")
    try:
        test_arm_order_reproducible(failures)
    except Exception as exc:
        failures.append(f"plan_arms: {exc!r}")
    try:
        test_adherence_run(failures)
    except Exception as exc:
        failures.append(f"adherence_run: {exc!r}")
    print(f"{len(failures)} failed")
    for f in failures:
        print(f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
