---
name: verify
description: Use before claiming tests pass or work is done, and before any commit or PR
budget: 550
role: write
refs:
  - path: ref/harness.md
    when: tests touch a database, an external service, or spawn processes
---

# Verify

## Trigger
Before any claim of done, fixed, working or passing, before committing or
pushing, and before handing work to another agent.

## Invariants
- Evidence before claims. Say it passes only from a run you can point at: one
  you made here, or one recorded in `.primeskills/run/` against this commit.
  Remembering a green run is not a run.
- Absence of a crash is not a pass. A pass is an exit code plus the tool's own
  success signal.
- Never edit a test, fixture, or threshold to turn a build green. If a test
  looks wrong, say so and stop.
- The cycle closes only when the new test passes and the full suite passes.

## Procedure
1. Resolve the target the run will act on — database, schema, directory — and
   print it → **verify:** it is the isolated one, not the working store (G17)
2. Name the command that would prove the claim → **verify:** it tests the claim,
   not a neighbour of it
3. Run it whole and fresh → **verify:** exit code is 0
4. Read the tool's own success signal → **verify:** 0 failed and the count you
   expected from a test runner, whatever other tools report instead — an exit
   code alone is half the proof (G4)
5. For a bug fix, pair the run with the red evidence `build` recorded
   → **verify:** the recorded failure and this pass describe the same test.
   With no record, prove it in a throwaway worktree — never by reverting the
   live tree, which can eat work that is not yours
6. Run the full suite, not only the touched file, unless a flow already ran it
   for this state → **verify:** exit code is 0, and you say which run you used
7. Kill spawned processes, remove temp artifacts → **verify:** none left behind

## Stop conditions
- Tempted to adjust the test instead of the code: stop. That impulse is the
  finding.
- No recorded red run and no worktree to prove one: the regression is unproven.
  Say that rather than calling the fix verified.
- Three runs, three failures, same error: roll back and report (G9).
- Reaching for "should" or "probably": you are about to claim without evidence.
  See RATIONALIZATIONS.

## Output
`PASS` or `FAIL`, the command, its exit code, the pass/fail counts, and the
names of failing tests. No adjectives. Record it where the next skill can
read it: `primeskills-run note verify "<command>: <counts>, exit <code>"`.

## References
`ref/harness.md` for isolation, seeds, and teardown when the run touches shared
state.
