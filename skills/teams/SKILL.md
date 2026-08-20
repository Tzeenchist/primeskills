---
name: teams
description: Use to run the full review panel over an existing plan and consolidate what it finds
budget: 350
tier: flow
calls: [ceo, eng, beauty]
calls_optional: [beauty]
role: read-only
allowed-tools: [Read, Grep, Glob, Bash, WebFetch, WebSearch, AskUserQuestion]
---

# Teams

## Trigger
A written plan that needs looking at from more than one side, before work
starts.

## Invariants
- This flow knows the order and nothing else. It does not restate what the
  lenses say, and it does not review on their behalf.
- A finding resolved during the panel is struck, not carried (G6).

## Procedure
1. Call `ceo` → **verify:** findings returned, or "no objections"
2. Call `eng` → **verify:** the same
3. Call `beauty` only if the plan touches an interface → **verify:** it ran, or
   you state why it did not
4. Consolidate: drop duplicates, drop anything already resolved, and put the
   ones that change scope first → **verify:** every surviving finding names its
   lens and the user's decision
5. Hand the amended plan back → **verify:** the user sees what changed, not a
   list of what was said

## Stop conditions
- Two lenses contradict each other: present both positions and let the user
  choose. Do not average them.
- The panel finds the plan is the wrong work: stop and return to `brief`.

## Output
Amended plan plus the findings table: lens, finding, decision.

## References
`ceo`, `eng`, `beauty`. `autoplan` runs this as part of a longer chain.
