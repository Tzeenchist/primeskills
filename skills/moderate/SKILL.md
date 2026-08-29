---
name: moderate
description: Use to order a queue of tasks so the next wave runs without rework or blocked starts
budget: 600
tier: flow
calls: [eng]
calls_optional: [eng]
role: write
---

# Moderate

## Trigger
A queue with more than a handful of live entries: before a wave of work goes
out, and after one, when part of it has gone stale. Not for picking the next
task alone — that is one read, not a skill.

## Invariants
- The order is a claim. Every move names its reason and an anchor — a file, a
  commit, a PR, the message that raised it (G6). "Reads better this way" is not
  a reason.
- The entry's text belongs to whoever wrote it. This skill moves entries and
  updates their state; what a task *is* it never rewrites (G1).
- Blocked never outranks ready: a blocked task at the head costs the day it was
  meant to open.
- Closing, cutting or merging a task is the user's (P8): you report the
  disagreement, not settle it.
- The queue's own conventions beat yours: two queues on one machine are kept
  two different ways, and the file in front of you says which.

## Procedure
1. Read the queue whole, including the part that says how it is kept
   → **verify:** you can name its sections and how it marks an entry live, in
   its words and not yours
2. Check every live entry against the repository: the anchor it names exists
   and still says what the entry claims (G6) → **verify:** each entry ends up
   anchored, unanchored or in conflict, and none is merely believed
3. Sort into blocked, dependent, ready. A blocked entry names its condition and
   who lifts it; a dependent one names what it waits on, by id
   → **verify:** nothing sits in ready while its own text names a condition
4. Resolve the dependency graph. A cycle, or an id no entry carries, is
   reported and never silently broken → **verify:** the report names every edge
   you could not resolve
5. Group by contact surface — the files a task opens, not the theme it belongs
   to. Entries sharing one go adjacent, so it opens once
   → **verify:** every group names paths
6. Order: ready first, dependencies before dependents, surface groups kept
   whole. An entry whose requirements are unsettled gets `brief` in front of
   it, not a place at the head. Run `eng` over the first two or three; its
   wrong-at-root verdict takes that entry off the head
   → **verify:** the top three carry no open dependency and no external
   condition
7. Write the order back, each move carrying its reason in one clause
   → **verify:** the diff moves entries and updates state and reasons, and
   rewrites no entry's own text

## Stop conditions
- The queue file already has uncommitted changes: stop. Rollback here is
  `git checkout -- <queue>`, true only if it was clean when you started.
- Everything is blocked: say so, and name what lifts each block. Promoting a
  blocked task to make the list look workable is the failure this skill exists
  to prevent.
- An entry contradicts the repository: report it, leave it where it is, and let
  the user decide (P8).
- More than a third of the live entries carry no anchor: the file is a wish
  list, and ordering wishes yields a confident wrong answer. Say so first.

## Output
The order, each position with its reason and anchor; the blocked list with what
lifts each; entries that disagree with the repository; unresolved dependency
edges; and the diff written to the queue.

## References
`eng` reviews the head; `brief` settles an entry whose requirements are open;
`plan` turns one entry into tasks; `handoff` records where the wave stopped.
