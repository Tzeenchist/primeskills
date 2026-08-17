---
name: release
description: Use to take merged work all the way to a running environment, merging then deploying
budget: 250
tier: flow
calls: [land, merge, deploy]
role: write
---

# Release

## Trigger
Work that is verified and reviewed, when the user wants it out rather than
handed over.

## Invariants
- Three gates, three decisions, all the user's: open, merge, deploy. This flow
  carries them out in order; it does not grant them.
- Each stage reads the previous one's evidence. Nothing here is assumed green.

## Procedure
1. Call `land` → **verify:** branch pushed, criteria listed, PR opened or its
   absence explained
2. Ask whether to merge, unless the user already said → **verify:** you have an
   answer, not an inference
3. Call `merge` → **verify:** base branch carries the change and is green on the
   base
4. Ask whether to deploy, and to where → **verify:** the environment is named by
   the user, not chosen by you
5. Call `deploy` → **verify:** health checked on the environment, rollback known
6. Report the chain → **verify:** what went where, and what remains reversible

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
