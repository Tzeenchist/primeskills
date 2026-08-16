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
- When the unknown is someone else's tool — its format, flags, or where it looks
  for files — read its documentation before probing it. Guessing costs more
  attempts than reading, and reverse-engineering costs more than both.

## Procedure
1. Preflight: read the repository's agent instructions, note what is already
   dirty and whose it is, and find the real test command → **verify:** you can
   reproduce from a state you can describe
2. Reproduce it once, cleanly → **verify:** the failure appears, and you can
   state the exact command and starting condition
3. Shrink to a minimal failing example: strip inputs, mocks, and steps until
   removing anything more makes it pass → **verify:** the MRE still fails and
   fits in a screen
4. Read the actual values at the boundary — types, nulls, empties, encodings.
   Print them, do not infer them → **verify:** you can name what the data is,
   not what it should be
5. Name the layer the fault lives in: agent behaviour, data and state, harness
   mismatch, or process gap → **verify:** the layer explains every symptom you
   observed, not just the loudest one
6. State one hypothesis and the experiment that would falsify it → **verify:**
   the experiment can come out either way
7. Run the experiment → **verify:** the result is read, not assumed
8. If it failed, write the ledger line before touching anything: "hypothesis N
   failed because X; hypothesis N+1 does Y differently" → **verify:** N+1 is
   different in kind, not in cosmetics (G13)
9. Fix at the lowest durable layer, then hand to `verify` → **verify:** the MRE
   passes and the full suite passes

## Stop conditions
- Three failures on the shared counter (G9) — whether they happened here or in
  `build` — restore the snapshot and report what each attempt ruled out.
- You cannot reproduce it: say so. An unreproducible bug is not fixed by a
  plausible patch.
- Two guesses at a third-party format have failed: stop guessing and go read.
  A third guess is rarely the one that works.
- The fix would add a null guard or an empty catch over a bad value: that is
  the symptom talking. Go back to step 4.

## Output
The MRE, the root cause and its layer, the fix, the ruled-out hypotheses, and
the verification result.

## References
`ref/harness.md` in `verify` when the failure involves shared state.
