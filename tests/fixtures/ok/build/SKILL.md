---
name: build
description: Use when implementing a feature or fixing a bug in code
budget: 400
role: write
---

## Trigger
Before any claim of done, fixed, or passing.

## Invariants
- Every changed line traces to the request.
- No abstractions for single-use code.

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
