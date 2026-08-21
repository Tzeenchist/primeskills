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
    p = run(["-m", "pytest", "-q", str(task)])
    if p.returncode != 0:
        failures.append(f"фикстура split-bill не зелёная:\n{p.stdout[-400:]}")


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
    print(f"{len(failures)} failed")
    for f in failures:
        print(f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
