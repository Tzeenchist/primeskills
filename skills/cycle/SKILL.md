---
name: cycle
description: Use to run the implementation loop, building and debugging until the tests are green
budget: 400
tier: flow
calls: [build, verify, debug]
role: write
---

# Cycle

## Trigger
An approved plan, when you want the loop closed without stopping between steps.

## Invariants
- The attempt counter (G12) lives in `primeskills-run`, not in your head, and
  has exactly one writer: the command `primeskills-run fail`, called by whichever
  skill hit the failure.
  This flow reads it. Two writers counted one failure twice and tripped the
  breaker at a hypothesis and a half.
- No step starts before the previous one has a PASS.

## Procedure
1. Call `build` for the next step → **verify:** a diff, a new test and the
   recorded red run exist
2. Read the verification `build` already ran; run `verify` yourself only if it
   did not → **verify:** PASS or FAIL, with evidence, and the suite ran once
3. On FAIL, call `debug` — it records the attempt — then read the count with
   `primeskills-run show` and return to 2 → **verify:** the count rose by one,
   not two, and is below three
4. When it exits 3, stop: restore the G11 snapshot if the work took one, and
   where none was required say plainly what state the tree is in instead of
   inventing a restore. Report what each attempt ruled out, ask → **verify:**
   the user knows where the tree stands and has the ledger, not a summary
5. On PASS, repeat from 1 until acceptance criteria are met → **verify:** each
   criterion is marked individually

## Stop conditions
- The plan proves wrong: leave the loop and say so. Never replan silently.
- Anything on the escalation list (G15): stop the loop first, then ask.

## Output
Per step: diff, verification result, rounds taken. At the end, the acceptance
criteria with each marked.

## References
`build`, `verify`, `debug`. Round limit and ledger: `GUARDRAILS.md` G12, G13.
