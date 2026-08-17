---
name: land
description: Use to commit, push and open a pull request
budget: 250
role: write
---

## Trigger
Work that is verified, when the user wants it out.

## Invariants
- The change is pushed only after the suite has run green.

## Procedure
1. Call `land` → **verify:** the pull request exists
2. Call `ship` → **verify:** the environment reports the new version

## Stop conditions
- Any stage stops: the flow stops there.

## Output
What went where, and what remains reversible.

## References
`land` prepares the change.
