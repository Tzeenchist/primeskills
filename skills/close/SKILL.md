---
name: close
description: Use to take verified work through review and testing to a pull request
budget: 350
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
1. If the change came from someone else, read before running: the diff of test
   files, build scripts, CI config and dependency manifests → **verify:** you
   can say what a test run would execute, and nothing in it reaches the network
   or the filesystem outside the checkout. Running a suite is executing the
   change, and the review that would have caught a hostile test comes after it
2. Call `verify` → **verify:** PASS with exit code and counts
3. Call `vet` → **verify:** findings sorted, verdict stated
4. On a blocking finding, return to `build`, then restart at 1 → **verify:** the
   finding is struck once fixed, not carried (G16)
5. Call `probe` if the change touches a running interface → **verify:** it
   returned PASS; BLOCK returns to step 4, and NOT RUN on a change
   that touches an interface is not a pass — it is an unknown
6. Call `handoff` if work remains, before landing → **verify:** the checkpoint
   names what is left and stays in this tree — it is local and does not go
   into the pull request
7. Call `land` → **verify:** PR exists, criteria marked, secrets pass done, and
   no file from `.primeskills/` is in the diff

## Stop conditions
- Three trips back to `build` on the same finding: stop and ask (G9).
- `vet` says rework rather than merge: leave the flow, do not patch around it.

## Output
The verification result, the review verdict, the PR URL, and what remains.

## References
`verify`, `vet`, `probe`, `land`, `handoff`.
