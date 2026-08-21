---
name: ui
description: Use when building an interface with empty, loading, error and success states and keyboard access
budget: 450
role: write
refs:
  - path: ref/ui-states.md
    when: implementing or changing any component a user interacts with
---

# Ui

## Trigger
Work that produces markup, styles, or interaction. Reads `plan` output like
`build` does; this is the interface half of the same job.

## Invariants
- Anything that waits or carries data ships all five states, or does not ship.
  Success alone is a demo. A static or synchronous control may mark a state
  not applicable — with the reason, not by omission.
- Hierarchy is the design decision. If everything has equal weight, nothing has
  been decided.
- Keyboard and pointer are the same feature, not two.
- Match the existing design system. A new colour or spacing value needs a reason
  a reviewer would accept.
- Motion is explanation or feedback: if removing an animation loses neither,
  remove it.
- Every visible element carries real content. Placeholder copy, decorative
  statistics, and controls that do nothing are unfinished work, not styling.

## Procedure
1. Read `ref/ui-states.md` and name the five states for this component
   → **verify:** each has intended content or a stated reason it cannot occur
2. Build the states in order: empty, loading, error, partial, success
   → **verify:** each is reachable in the running build, not only in the code
3. Set hierarchy before decoration: what should the eye reach first, second,
   third → **verify:** the order survives a squint at the screen
4. Wire the keyboard path: tab order, enter, escape, focus after actions
   → **verify:** you operated it without a pointer
5. Check contrast and target size against the system's tokens → **verify:**
   values come from tokens, not from a guess
6. Hand to `verify`, then `probe` → **verify:** tests pass and the states hold
   on a running build

## Stop conditions
- No design system exists and you are inventing one: that is a bigger decision
  than this task. Say so and ask.
- A state has no defined content: ask rather than invent copy the product does
  not have.
- You are reaching for a gradient, a third font, or even spacing everywhere to
  make it look finished: those are the tells of generated design, not a fix.

## Output
The components with their five states, the keyboard path, and any design token
added and why.

## References
`ref/ui-states.md`. `beauty` reviews the plan; `probe` checks the running build.
