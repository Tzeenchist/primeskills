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
- Write for a capable implementer new to this code: given the interface and
  the test, they write idiomatic code. They cannot know what you decided —
  files, signatures, the values the request pins, the test for each task. The
  plan carries that.
- Every task carries its own acceptance criterion. "Implement X" is not a task.
- A step lets the implementer write one reasonable thing. "TBD" or "handle
  appropriately" decides nothing; a body the signature and test already fix is
  code written early.
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
4. Name up to five inputs the goal implies but no criterion exercises,
   likeliest to bite first, each with what a reasonable user expects
   → **verify:** each is pinned to the task owning that code, or you say none
   after checking
5. Mark the standing bar separately from the per-task criteria: tests green, no
   regressions, docs current → **verify:** both lists exist and neither
   swallows the other
6. Decide the gate by reversibility (G2) → **verify:** the decision is stated,
   not assumed, and the criteria you hand over name checkable outcomes rather
   than the shape of the code
7. Re-read as that implementer; a plan several times the request's length, or
   mostly code, is the program written early → **verify:** name the first place
   they would guess and remove it; bodies become signatures and assertions

## Stop conditions
- The goal cannot be stated in one sentence: it is more than one goal. Split it
  or go back to `brief`.
- A task has no observable criterion: you do not yet understand it well enough
  to plan it.
- The plan is growing past what the request asked for: cut (P4).

## Output
The goal, what is out of scope, ordered tasks with acceptance criteria, the
review focus, the standing bar, and whether approval is required before implementation.

## References
Lenses `ceo`, `money`, `eng`, `beauty` review this plan; `teams` runs the panel.
