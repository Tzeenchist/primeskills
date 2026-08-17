---
name: release
description: Use to take merged work all the way to a running environment
budget: 250
tier: flow
calls: [land, ship]
role: write
---

## Trigger
Work that is verified, when the user wants it out.

## Invariants
- Every gate is the user's decision, carried out here in order.

## Procedure
1. Call `land` → **verify:** the pull request exists
2. Call `ship` → **verify:** the environment reports the new version

## Stop conditions
- Any stage stops: the flow stops there.

## Output
What went where, and what remains reversible.

## References
`land` prepares the change.
