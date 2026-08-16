#!/usr/bin/env python3
"""Prove each linter rule fires on a fixture that violates it, and only then."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINT = ROOT / "bin" / "primeskills-lint"
ROUTE = ROOT / "bin" / "primeskills-route"
FIXTURES = ROOT / "tests" / "fixtures"

EXPECT = {
    "ok": None,
    "f1-no-frontmatter": "F1",
    "f2-name-mismatch": "F2",
    "f3-long-description": "F3",
    "f4-over-budget": "F4",
    "f5-bad-sections": "F5",
    "f6-step-without-verify": "F6",
    "f7-ref-without-when": "F7",
    "f8-duplicate-invariant": "F8",
    "f9-bad-role": "F9",
}


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    failures = []
    for case, rule in sorted(EXPECT.items()):
        code, out = run([sys.executable, str(LINT), str(FIXTURES / case)])
        if rule is None:
            if code != 0:
                failures.append(f"{case}: expected clean, got:\n{out}")
        else:
            if rule not in out:
                failures.append(f"{case}: expected {rule}, got:\n{out}")
            elif code == 0:
                failures.append(f"{case}: {rule} reported but exit code 0")

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
    print(f"{len(EXPECT) + 2} checks, {len(failures)} failed")

    fence = subprocess.run([sys.executable, str(Path(__file__).parent / "test_fence.py")])
    return 1 if (failures or fence.returncode) else 0


if __name__ == "__main__":
    sys.exit(main())
