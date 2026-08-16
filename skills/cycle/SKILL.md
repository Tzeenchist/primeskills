---
name: cycle
description: Use to run the implementation loop, building and debugging until the tests are green
budget: 250
tier: flow
role: write
---

# Cycle

## Trigger
An approved plan, when you want the loop closed without stopping between steps.

## Invariants
- The round counter belongs here. A skill cannot know how many times it has
  been called; this flow can.
- No step starts before the previous one has a PASS.

## Procedure
1. Call `build` for the next step → **verify:** a diff and a new test exist
2. Call `verify` → **verify:** PASS or FAIL, with evidence
3. On FAIL, call `debug`, then return to 2, counting the round → **verify:**
   the count is recorded and below three
4. On the third failed round, stop: roll back, report what each attempt ruled
   out, ask → **verify:** the user has the ledger, not a summary of it (G9)
5. On PASS, repeat from 1 until acceptance criteria are met → **verify:** each
   criterion is marked individually

## Stop conditions
- The plan proves wrong: leave the loop and say so. Never replan silently.
- Anything on the escalation list (G12): stop the loop first, then ask.

## Output
Per step: diff, verification result, rounds taken. At the end, the acceptance
criteria with each marked.

## References
`build`, `verify`, `debug`. Round limit and ledger: `GUARDRAILS.md` G9, G13.
