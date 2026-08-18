---
name: close
description: Use to take verified work through review and testing to a pull request
budget: 450
tier: flow
calls: [verify, vet, probe, handoff, land]
calls_optional: [probe, handoff]
role: write
---

# Close

## Trigger
The user asked for the work to reach a pull request. Finished implementation is
the precondition, not the trigger: commit, push and PR are changes other people
see, and nobody asked for them just because the code compiles.

## Invariants
- Order is not negotiable: nothing is reviewed before it passes, and nothing
  lands before it is reviewed.
- A blocking finding sends the work back to `build`; it does not become a note
  on the pull request.

## Procedure
1. If the change came from someone else, `vet` runs **first** and the suite
   waits for it → **verify:** the diff is reviewed before anything from it is
   executed. Collecting tests imports the application, so a payload in any
   imported module runs before a single test does; reading test files is not
   enough
2. Still someone else's code after review, and no sandbox to run it in: stop
   and say so → **verify:** you name what you did not run and why. A suite
   without a sandbox is trust, and trust is the user's to give
3. Call `verify` → **verify:** PASS with exit code and counts
4. Call `vet`, unless step 1 already did → **verify:** findings sorted, verdict
   stated
5. On a blocking finding, return to `build`, then restart at 1 → **verify:** the
   finding is struck once fixed, not carried (G16)
6. Call `probe` if the change touches a running interface → **verify:** it
   returned PASS; BLOCK returns to step 5, and NOT RUN on a change
   that touches an interface is not a pass — it is an unknown
7. Call `handoff` if work remains, before landing → **verify:** the checkpoint
   names what is left and stays in this tree — it is local and does not go
   into the pull request
8. Call `land` → **verify:** PR exists, criteria marked, secrets pass done, and
   no file from `.primeskills/` is in the diff

## Stop conditions
- Three trips back to `build` on the same finding: stop and ask (G9).
- `vet` says rework rather than merge: leave the flow, do not patch around it.

## Output
The verification result, the review verdict, the PR URL, and what remains.

## References
`verify`, `vet`, `probe`, `land`, `handoff`.
