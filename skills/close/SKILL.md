---
name: close
description: Use to take verified work through review and testing to a pull request
budget: 250
tier: flow
role: write
---

# Close

## Trigger
Implementation is finished and the tests are green. Everything between "it
works" and "it is someone else's turn".

## Invariants
- Order is not negotiable: nothing is reviewed before it passes, and nothing
  lands before it is reviewed.
- A blocking finding sends the work back to `build`; it does not become a note
  on the pull request.

## Procedure
1. Call `verify` → **verify:** PASS with exit code and counts
2. Call `vet` → **verify:** findings sorted, verdict stated
3. On a blocking finding, return to `build`, then restart at 1 → **verify:** the
   finding is struck once fixed, not carried (G16)
4. Call `probe` if the change touches a running interface → **verify:** it ran,
   or you state why it did not
5. Call `land` → **verify:** PR exists, criteria marked, secrets pass done
6. Call `handoff` if work remains → **verify:** the checkpoint names what is left

## Stop conditions
- Three trips back to `build` on the same finding: stop and ask (G9).
- `vet` says rework rather than merge: leave the flow, do not patch around it.

## Output
The verification result, the review verdict, the PR URL, and what remains.

## References
`verify`, `vet`, `probe`, `land`, `handoff`.
