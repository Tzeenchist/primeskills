#!/usr/bin/env python3
"""Prove each linter rule fires on a fixture that violates it, and only then."""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINT = ROOT / "bin" / "primeskills-lint"
ROUTE = ROOT / "bin" / "primeskills-route"
FIXTURES = ROOT / "tests" / "fixtures"

# cases whose skills live in a skills/ subdir because they carry their own core/
NESTED = {"f12-paraphrase", "f12-cited", "c3-over", "c4-empty-registry",
          "c1-core-too-big", "c2-core-missing"}

EXPECT = {
    "ok": None,
    "f12-paraphrase": "F12",
    "f12-cited": None,
    "f13-unknown-call": "F13",
    "c3-over": "C3",
    "f1-no-frontmatter": "F1",
    "f2-name-mismatch": "F2",
    "f3-long-description": "F3",
    "f4-over-budget": "F4",
    "f5-bad-sections": "F5",
    "f6-step-without-verify": "F6",
    "f7-ref-without-when": "F7",
    "f8-duplicate-invariant": "F8",
    "f9-bad-role": "F9",
    "f11-ref-too-big": "F11",
    "f14-nested-frontmatter": "F14",
    "f15-exercises-no-env": "F15",
    "c4-empty-registry": "C4",
    "c1-core-too-big": "C1",
    "c2-core-missing": "C2",
    "f10-role-tools": "F10",
    "f11-ref-missing": "F11",
    "f16-readonly-mutates": "F16",
    "f17-decision-without-means": "F17",
}


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def call_budget():
    import importlib.machinery, importlib.util
    loader = importlib.machinery.SourceFileLoader("_lint", str(LINT))
    spec = importlib.util.spec_from_loader("_lint", loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CALL_BUDGET


def arm_c3_fixture(tmp):
    """The C3 case must break the ceiling, whatever the ceiling is today.

    Three times in one day a raised ceiling turned this fixture green and the
    rule stopped being tested, silently. A fixture with a number typed into it
    tests the number, not the rule — so the number is written at run time.

    Into a copy, never into the tracked fixture: a test suite that edits the
    working tree before running is the harness tampering G7 forbids, and it was
    this file doing it.
    """
    src = FIXTURES / "c3-over"
    dest = Path(tmp) / "c3-over"
    shutil.copytree(src, dest)
    path = dest / "skills" / "heavy" / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"^budget: \d+$", f"budget: {call_budget()}", text,
                           count=1, flags=re.M), encoding="utf-8")
    return dest


def main():
    failures = []
    scratch = tempfile.mkdtemp(prefix="primeskills-tests-")
    c3_dir = arm_c3_fixture(scratch)
    for case, rule in sorted(EXPECT.items()):
        base = c3_dir if case == "c3-over" else FIXTURES / case
        path = base / "skills" if case in NESTED else base
        code, out = run([sys.executable, str(LINT), str(path)])
        if rule is None:
            if code != 0:
                failures.append(f"{case}: expected clean, got:\n{out}")
        else:
            if rule not in out:
                failures.append(f"{case}: expected {rule}, got:\n{out}")
            elif code == 0:
                failures.append(f"{case}: {rule} reported but exit code 0")

    # a linted tree is data, never code. Linting a foreign clone used to load
    # and execute its bin/primeskills-install, which turned a static format
    # check into arbitrary code execution with the user's rights.
    with tempfile.TemporaryDirectory() as tmp:
        foreign = Path(tmp) / "clone"
        shutil.copytree(FIXTURES / "ok", foreign / "skills")
        shutil.copytree(ROOT / "core", foreign / "core")
        (foreign / "bin").mkdir()
        marker = foreign / "EXECUTED"
        (foreign / "bin" / "primeskills-install").write_text(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('executed')\n"
            "def bootstrap_text():\n    return 'x'\n", encoding="utf-8")
        run([sys.executable, str(LINT), str(foreign / "skills")])
        failures_before = len(failures)
        if marker.exists():
            failures.append("линтер исполнил код из проверяемого дерева")
        del failures_before

    # The linter against the real set, not only fixtures. Everything here
    # checked that the rules fire on planted cases; nothing checked that the
    # set we ship passes them, so a core file over budget (C1) was green
    # locally and would only have failed in CI.
    code, out = run([sys.executable, str(LINT)])
    if code != 0:
        failures.append(f"линтер на самом наборе: {out.strip()}")

    # routing linter: good table passes, colliding table fails
    code, out = run([sys.executable, str(ROUTE), str(FIXTURES / "ok"),
                     str(FIXTURES / "routing-ok.txt")])
    if code != 0:
        failures.append(f"routing-ok: expected clean, got:\n{out}")
    code, out = run([sys.executable, str(ROUTE), str(FIXTURES / "ok"),
                     str(FIXTURES / "routing-bad.txt")])
    if code == 0:
        failures.append("routing-bad: expected failure, got clean")

    for f in failures:
        print(f)
    print(f"{len(EXPECT) + 4} checks, {len(failures)} failed")

    fence = subprocess.run([sys.executable, str(Path(__file__).parent / "test_fence.py")])
    record = subprocess.run([sys.executable, str(Path(__file__).parent / "test_run.py")])
    adherence = subprocess.run([sys.executable, str(Path(__file__).parent / "test_adherence.py")])
    guide = subprocess.run([sys.executable, str(Path(__file__).parent / "test_help.py")])
    install = subprocess.run([sys.executable, str(Path(__file__).parent / "test_install.py")])
    docs = subprocess.run([sys.executable, str(Path(__file__).parent / "test_docs.py")])
    checkpoints = subprocess.run([sys.executable, str(Path(__file__).parent / "test_handoffs.py")])
    coverage = subprocess.run([sys.executable, str(Path(__file__).parent / "test_rule_coverage.py")])
    livecall = subprocess.run([sys.executable, str(Path(__file__).parent / "test_release_livecall.py")])
    bench = subprocess.run([sys.executable, str(Path(__file__).parent / "test_bench.py")])

    # routing over the real skill set, not just fixtures
    live = subprocess.run([sys.executable, str(ROUTE), str(ROOT / "skills"),
                           str(ROOT / "tests" / "routing.txt")])
    shutil.rmtree(scratch, ignore_errors=True)
    return 1 if (failures or fence.returncode or record.returncode
                 or adherence.returncode or guide.returncode
                 or install.returncode or docs.returncode
                 or checkpoints.returncode or coverage.returncode
                 or livecall.returncode or bench.returncode
                 or live.returncode) else 0


if __name__ == "__main__":
    sys.exit(main())
