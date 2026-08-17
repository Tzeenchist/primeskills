---
name: plan
description: Use when requirements are clear and work needs breaking into ordered tasks, before touching code
budget: 500
role: read-only
allowed-tools: [Read, Grep, Glob, Bash, WebFetch, WebSearch, AskUserQuestion]
---

# Plan

## Trigger
An intent with success criteria, from `brief` or from the user directly. Skip
for a change that fits in one file and alters no contract — that gate is G2.

## Invariants
- Write for an implementer with no context, no judgement, and an aversion to
  testing. If such a reader could go wrong, the plan is not finished.
- Every task carries its own acceptance criterion. "Implement X" is not a task.
- No placeholders. "TBD", "handle appropriately", "add tests as needed" are how
  a plan looks when the thinking has not happened yet.
- A task fits one commit. If it needs three, it is three tasks.
- You do not write code here. This skill reads and plans.

## Procedure
1. Restate the goal in one sentence and name what is explicitly out of scope
   → **verify:** the exclusions are specific things, not "everything else"
2. List the tasks in dependency order → **verify:** each one can start when the
   ones above it are done, and none needs a later task to make sense
3. Give each task an acceptance criterion that names a command or an
   observation → **verify:** you could hand the criterion to someone else and
   they would agree on whether it is met
4. Mark the standing bar separately from the per-task criteria: tests green, no
   regressions, docs current → **verify:** both lists exist and neither
   swallows the other
5. Decide the gate by blast radius: one file and no contract change proceeds;
   a new module, a migration, or a public API waits for approval → **verify:**
   the decision is stated, not assumed (G2)
6. Re-read as the implementer described above → **verify:** name the first place
   they would guess, and remove the guess

## Stop conditions
- The goal cannot be stated in one sentence: it is more than one goal. Split it
  or go back to `brief`.
- A task has no observable criterion: you do not yet understand it well enough
  to plan it.
- The plan is growing past what the request asked for: cut (PRINCIPLES §4).

## Output
The goal, what is out of scope, ordered tasks with acceptance criteria, the
standing bar, and whether approval is required before implementation.

## References
Lenses `ceo`, `eng`, `beauty` review this plan; `teams` runs all three.
