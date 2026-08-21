#!/usr/bin/env python3
"""Every core rule is either machine-checked or honestly marked as not.

The coverage table (docs/RULE-COVERAGE.md) exists because unenforceable rules
were accreting: each one costs context in every session, and a rule nobody can
check is also a rule nobody can tell from one anybody follows. The test keeps
the table complete -- a new P- or G-rule without a row here breaks the gate,
and so does a row that claims neither mechanics nor an insurance policy.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core"
COVERAGE = ROOT / "docs" / "RULE-COVERAGE.md"


def rule_ids():
    ids = set()
    pr = (CORE / "PRINCIPLES.md").read_text(encoding="utf-8")
    ids.update("P" + m for m in re.findall(r"^## P?(\d+)\.", pr, re.M))
    g = (CORE / "GUARDRAILS.md").read_text(encoding="utf-8")
    ids.update(re.findall(r"\*\*(G\d+)", g))
    return ids


def main():
    failures = []
    text = COVERAGE.read_text(encoding="utf-8")
    rows = {m.group(1): m.group(2)
            for m in re.finditer(r"^\| ([PG]\d+) \|( .+?)\|$", text, re.M)}
    for rid in sorted(rule_ids()):
        if rid not in rows:
            failures.append(f"{rid}: нет строки в RULE-COVERAGE.md")
            continue
        row = rows[rid].lower()
        if "механика" not in row and "страховка" not in row:
            failures.append(f"{rid}: строка не называет ни механики, ни страховки")
    extra = set(rows) - rule_ids()
    if extra:
        failures.append(f"строки без правила в core/: {sorted(extra)}")
    print(f"{len(rule_ids())} rules, {len(failures)} failed")
    for f in failures:
        print(f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
