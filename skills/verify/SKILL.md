---
name: verify
description: Use before claiming tests pass or work is done, and before any commit or PR
budget: 400
role: write
refs:
  - path: ref/harness.md
    when: tests touch a database, an external service, or spawn processes
---

# Verify

## Trigger
Before any claim of done, fixed, working, or passing — and before committing,
pushing, or opening a PR. Also before handing work to another agent.

## Invariants
- Evidence before claims. If you have not run the command in this message, you
  cannot say it passes.
- Absence of a crash is not a pass. A pass is an exit code plus a count.
- Never edit a test, fixture, or threshold to turn a build green. If a test
  looks wrong, say so and stop.
- The cycle closes only when the new test passes and the full suite passes.

## Procedure
1. Resolve the target the run will act on — database, schema, directory — and
   print it → **verify:** it is the isolated one, not the working store (G17)
2. Name the command that would prove the claim → **verify:** it tests the claim,
   not a neighbour of it
3. Run it whole and fresh → **verify:** exit code is 0
4. Read the summary line → **verify:** it reports 0 failed and 0 errors, and the
   count is the count you expected
5. For a bug fix, confirm the red-green cycle: revert the fix, run, see it fail;
   restore, run, see it pass → **verify:** both observed in this session
6. Run the full suite, not only the touched file → **verify:** exit code is 0
7. Kill spawned processes, remove temp artifacts → **verify:** none left behind

## Stop conditions
- Tempted to adjust the test instead of the code: stop. That impulse is the
  finding.
- Three runs, three failures, same error: roll back and report (G9).
- Reaching for "should", "probably", "looks right": you are about to claim
  without evidence. See RATIONALIZATIONS.

## Output
`PASS` or `FAIL`, the command, its exit code, the pass/fail counts, and the
names of failing tests. No adjectives.

## References
`ref/harness.md` for isolation, seeds, and teardown when the run touches shared
state.
