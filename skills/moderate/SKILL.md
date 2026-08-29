---
name: moderate
description: Use to order a queue of tasks so the next wave runs without rework or blocked starts
budget: 850
tier: flow
calls: [eng]
calls_optional: [eng]
role: write
---

# Moderate

## Trigger
A queue with more than a handful of live entries: before a wave goes out, and
after one, when part of it has gone stale. Not for picking the next task —
that is a read, not a skill.

## Invariants
- The order is a claim: every move names its reason and an anchor — a file, a
  commit, a PR, the message that raised it (G6). "Reads better" is not one.
- The entry's text belongs to whoever wrote it: this skill moves entries and
  updates state, and never rewrites what a task *is* (G1).
- Blocked never outranks ready: one at the head costs the day it was meant to
  open.
- Closing or cutting a task is the user's (P8): you report the disagreement,
  not settle it.
- The queue's own conventions beat yours: two queues on one machine are kept
  two ways, and the file says which.

## Procedure
1. Read the queue whole, including the part saying how it is kept
   → **verify:** you can name its sections and how it marks an entry live, in
   its words not yours
2. Check every live entry against the repository: the anchor it names exists
   and still says what the entry claims (G6) → **verify:** each ends up
   anchored, unanchored or in conflict, none merely believed
3. Sort into ready, dependent, blocked, owner-deferred and owner-only. Blocked
   names its condition and who lifts it; dependent, what it waits on, by id;
   owner-deferred is a decision that closing the dependency does not lift;
   owner-only needs a credential or an act no agent here has. Unanchored and
   conflicting entries go last, and are said to → **verify:** nothing sits
   in ready whose own text names a condition, a decision, or a step only the
   user can take
4. Resolve the dependency graph. A cycle, an id no entry carries, or an edge
   into a rejected entry is reported, never silently broken → **verify:** the
   report names every edge you left unresolved
5. Group by contact surface — the files a task opens, not its theme. Entries
   sharing one go adjacent, so it opens once. An entry naming no paths still
   has a surface — land-stage work opens a branch, a PR and CI. Group by that
   and say so; never invent paths
   → **verify:** every group names its surface, or you said why you refused
6. Order: ready first, dependencies before dependents, surface groups whole.
   Tied on every constraint, the earlier entry stays earlier: two runs agree.
   An entry whose requirements are unsettled gets `brief` in front of it, not a
   place at the head — and not `eng`, which reviews a plan nobody wrote yet.
   Over a head that has one, `eng` runs; its verdict is reported, and demoting
   on it is the user's (P8)
   → **verify:** the top three carry no open dependency and no external
   condition
7. Snapshot what you move, untracked included (G11): `git checkout` restores
   only what was committed, and other agents write this file too. Re-read it
   immediately before the patch — a base that moved since step 1 means a second
   writer is in it, so stop and say so. Then write, each move carrying its
   reason in one clause. A file that mirrors itself — a summary table beside
   the cards — moves every mirror together or none. Leave the result
   uncommitted and say so: committing a file several agents share is its own
   rung, and the next run stops on the dirty file
   → **verify:** the diff is move-only, the ids before and after are one
   multiset, and no entry's text is rewritten

## Stop conditions
- The queue file already has uncommitted changes: stop, at the start and again
  before writing. A clean check that ran only once is how a second writer's
  work disappears.
- Two live entries share an id: stop before ordering. Ordering by id merges
  them and loses one; the file has to tell them apart first.
- More live entries than the reading budget allows (G3): work in batches,
  never hand back an
  unchecked tail as a finished order, and name what you did not reach.
- Everything is blocked: say so and name what lifts each. Promoting a
  blocked task to make the list look workable is the failure this skill exists
  to prevent.
- An entry contradicts the repository: report it, leave it where it is, and let
  the user decide (P8).
- More than a third of the live entries carry no anchor: the file is a wish
  list, and ordering wishes yields a confident wrong answer.


## Output
The order, each position with its reason and anchor; what lifts each block;
entries that disagree with the repository; unresolved edges; and the diff.

## References
`eng` reviews a head that has a plan; `brief` settles an entry whose
requirements are open;
`plan` turns one into tasks; `handoff` records where the wave stopped.
