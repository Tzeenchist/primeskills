---
name: autoplan
description: Use to go from a raw idea to an approved plan without stopping between steps
budget: 250
tier: flow
role: read-only
---

# Autoplan

## Trigger
A rough idea and the wish to reach an approved plan in one pass.

## Invariants
- Approval gates are not skipped because the flow is automatic. The user still
  approves the brief and the plan.
- Nothing here writes code. The chain ends at an approved plan.

## Procedure
1. Call `brief` → **verify:** the user approved the intent
2. Call `plan` → **verify:** ordered tasks with acceptance criteria exist
3. Call `teams` → **verify:** findings consolidated with a decision on each
4. Amend the plan with the accepted findings → **verify:** each accepted finding
   is visible as a change, and each declined one is absent
5. Present the plan for approval → **verify:** the user approves, or says what
   to change

## Stop conditions
- The brief shows the request is exploratory: stop and say a prototype would
  answer more than a plan.
- Any escalation trigger appears (G12): leave the chain, then ask.

## Output
The approved plan, and one line on what the panel changed in it.

## References
`brief`, `plan`, `teams`. `cycle` implements what this produces.
