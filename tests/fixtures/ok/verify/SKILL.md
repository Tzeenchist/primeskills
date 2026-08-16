---
name: verify
description: Use before claiming tests pass or work is complete, and before any commit or PR
budget: 400
role: write
---

## Trigger
Before any claim of done, fixed, or passing.

## Invariants
- Absence of a crash is not a pass.
- Never edit tests or thresholds to make a build green.

## Procedure
1. Resolve the target database and print it → **verify:** name starts with `test_`
2. Run the test command → **verify:** exit code is 0
3. Read the runner summary → **verify:** the line reports 0 failed

## Stop conditions
- Three failed attempts on the same failure: roll back, report, ask.

## Output
`PASS` or `FAIL` plus command, exit code, failing test names.

## References
`ref/harness.md` when tests touch external services.
