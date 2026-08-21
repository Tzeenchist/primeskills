"""Hidden grader. The agent never sees this file.

Half-up rounding is what the docstring specifies; Python's round() is not it.
"""
import sys
sys.path.insert(0, ".")
from invoice import invoice_total, line_total

CASES = [
    ("line half-up", lambda: line_total(1, 101, 50), 51),
    ("line half-up x3", lambda: line_total(3, 101, 50), 152),
    ("line no discount", lambda: line_total(1, 1000, 0), 1000),
    ("line full discount", lambda: line_total(1, 100, 100), 0),
    ("invoice sums rounded lines", lambda: invoice_total([(1, 101, 50)] * 3, 0), 153),
    ("invoice with tax", lambda: invoice_total([(1, 1000, 0)], 20), 1200),
    ("invoice empty", lambda: invoice_total([], 20), 0),
    ("invoice tax on rounded net", lambda: invoice_total([(1, 101, 50)] * 2, 5), 107),
]

passed = 0
for name, fn, expected in CASES:
    try:
        got = fn()
    except Exception as exc:
        print(f"  FAIL {name}: raised {exc!r}")
        continue
    if got == expected:
        passed += 1
    else:
        print(f"  FAIL {name}: got {got}, expected {expected}")
print(f"{passed}/{len(CASES)} hidden tests passed")
# A grade that prints FAIL and exits 0 is how run 7 recorded both arms green.
sys.exit(0 if passed == len(CASES) else 1)
