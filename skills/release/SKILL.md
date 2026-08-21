---
name: release
description: Use to take merged work all the way to a running environment, merging then deploying
budget: 350
tier: flow
calls: [land, merge, deploy]
role: write
---

# Release

## Trigger
Work that is verified and reviewed, when the user wants it out rather than
handed over.

## Invariants
- Every rung it crosses is the user's: commit, push and pull request inside
  `land`, then merge, then migrate and deploy. Five decisions at least, not the
  three this flow is named after; it carries them out in order and grants
  none of them. One-use rungs are checked ahead with `--peek`, which spends
  nothing; the plain `may` at the moment of the act is what spends the use.
- Each stage reads the previous one's evidence. Nothing here is assumed green.

## Procedure
1. Call `land` → **verify:** branch pushed, criteria listed, PR opened or its
   absence explained
2. Ask whether to merge, unless the user already said → **verify:** you have an
   answer, not an inference
3. Call `merge` → **verify:** base branch carries the change and is green on the
   base
4. Call the changed skills live in every host and record each with
   `primeskills-run note livecall` → **verify:** `bin/primeskills-release`
   finds no missing pair
5. Ask whether to deploy, and to where → **verify:** the environment is named by
   the user, not chosen by you
6. Call `deploy` → **verify:** health checked on the environment, rollback known
7. Report the chain → **verify:** what went where, and what remains reversible

## Stop conditions
- Any stage stops: the flow stops there. Never skip forward to the next stage
  to salvage progress.
- The user wants only part of it: run that part. This flow is a convenience,
  not an obligation.

## Output
Per stage: what it did and its evidence. At the end, what is live and how to
undo it.

## References
`land`, `merge`, `deploy`. `close` is the shorter chain that ends at handover.
