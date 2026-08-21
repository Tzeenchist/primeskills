---
name: beauty
description: Use to review a plan for interface states, hierarchy and accessibility before building UI
budget: 400
role: read-only
allowed-tools: [Read, Grep, Glob, Bash, WebFetch, WebSearch, AskUserQuestion]
---

# Beauty

## Trigger
A plan that touches anything a person looks at or operates. Skip entirely for
backend-only work — this lens costs nothing when it does not run.

## Invariants
- Five states are not a checklist item, they are the interface: loading, empty,
  error, partial, success. A design that only describes success is a mockup.
- Accessibility is part of "works", not a later pass.
- Report only. You do not write markup here.

## Procedure
1. For each component that waits or carries data, name the five states and what
   the user sees in each; for a static control say which do not apply and why
   → **verify:** every component is answered, none is skipped in silence
2. Check the empty state teaches rather than apologises → **verify:** it says
   what to do next, not only that there is nothing
3. Check the error state says what happened and what the user can do
   → **verify:** no error text ends at "something went wrong"
4. Walk the keyboard path: tab order, enter, escape, focus after an action
   → **verify:** every interactive element is reachable and focus never
   disappears
5. Look for the tells of generated design: even spacing everywhere, no
   hierarchy, decorative gradients, three fonts → **verify:** you name specific
   places or state there are none
6. Present findings one at a time, each decided by the means named in
   OUTPUT §Asking → **verify:** each accepted or declined

## Stop conditions
- No interface in this plan: say so and stop. That is a complete review.
- The concern is aesthetic preference, not function or hierarchy: leave it out.

## Output
Findings per component with the user's decision, and the state matrix.

## References
`ui` implements; `probe` checks the states on a running system.
