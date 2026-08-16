---
name: debug
description: Use when a test fails, a build breaks, or behaviour surprises you, before proposing a fix
budget: 600
role: write
---

# Debug

## Trigger
Any failure you cannot already explain. Reach for this before the first fix
attempt, not after the third.

## Invariants
- Find the root before changing anything. A symptom fix is a failure, not
  partial progress.
- One hypothesis at a time. Several changes at once means you learn nothing
  from the result, whichever way it goes.
- Numbers come from one clean run. Observations stitched from several runs
  describe a system that never existed.
- The bug is in the code until proven otherwise. Blaming the framework,
  the compiler, or the machine needs the same evidence as any other claim (G15).

## Procedure
1. Reproduce it once, cleanly, from a known state → **verify:** the failure
   appears, and you can state the exact command and starting condition
2. Shrink to a minimal failing example: strip inputs, mocks, and steps until
   removing anything more makes it pass → **verify:** the MRE still fails and
   fits in a screen
3. Read the actual values at the boundary — types, nulls, empties, encodings.
   Print them, do not infer them → **verify:** you can name what the data is,
   not what it should be
4. Name the layer the fault lives in: agent behaviour, data and state, harness
   mismatch, or process gap → **verify:** the layer explains every symptom you
   observed, not just the loudest one
5. State one hypothesis and the experiment that would falsify it → **verify:**
   the experiment can come out either way
6. Run the experiment → **verify:** the result is read, not assumed
7. If it failed, write the ledger line before touching anything: "hypothesis N
   failed because X; hypothesis N+1 does Y differently" → **verify:** N+1 is
   different in kind, not in cosmetics (G13)
8. Fix at the lowest durable layer, then hand to `verify` → **verify:** the MRE
   passes and the full suite passes

## Stop conditions
- Three hypotheses, three failures: roll back and report what you tried and
  what each attempt ruled out (G9).
- You cannot reproduce it: say so. An unreproducible bug is not fixed by a
  plausible patch.
- The fix would add a null guard or an empty catch over a bad value: that is
  the symptom talking. Go back to step 4.

## Output
The MRE, the root cause and its layer, the fix, the ruled-out hypotheses, and
the verification result.

## References
`ref/harness.md` in `verify` when the failure involves shared state.
