---
name: build
description: Use when implementing a feature or fixing a bug, before writing implementation code
budget: 700
role: write
---

# Build

## Trigger
An approved plan with acceptance criteria, or a change small enough that the
planning gate does not apply (G2). Not for exploration — that is `brief`.

## Invariants
- Write the failing test first. A test written after the code proves the code
  runs, not that it is right.
- Red, green, refactor are three phases. Never blur them: no cleanup while
  making it pass, no new behaviour while refactoring.
- Every changed line traces to the request (PRINCIPLES §3).
- A task is done when its acceptance criteria are met *and* the standing bar is
  met. They are different questions and you need both.

## Procedure
1. Restate the task as a verifiable goal → **verify:** it names a command or an
   observation that will settle it
2. Cut it into steps a single commit can carry → **verify:** each step has its
   own check, and no step needs a later one to be meaningful
3. Before a risky step — migration, bulk edit, refactor — snapshot:
   `git stash create` or a `checkpoint/...` branch, a dump for data
   → **verify:** the snapshot exists and you can name it (G14)
4. **Red.** Write the test that fails for the right reason → **verify:** run it,
   read the failure message, confirm it describes the missing behaviour
5. **Green.** Write the least code that passes → **verify:** `verify` reports PASS
6. **Refactor.** Clean only what you just wrote → **verify:** tests still PASS,
   and the diff contains no unrelated change
7. Every 2–3 steps, commit atomically. Stage intentional files only, never
   `git add -A` → **verify:** `git diff --staged` shows exactly what you meant
   to include (G11)
8. Repeat from 4 until the acceptance criteria are met → **verify:** re-read
   them line by line and mark each one

## Stop conditions
- The test will not go red for the right reason: the test is wrong, or the
  behaviour already exists. Find out which before writing code.
- The plan turns out to be wrong mid-way: stop and say so. Do not quietly
  build something else (PRINCIPLES §8).
- A step needs an abstraction "for later": that is the moment to cut, not to
  generalise (PRINCIPLES §2).
- Three failed attempts at the same step: hand to `debug`, do not improvise.

## Output
The diff, the new tests, the commits made, and the acceptance criteria with
each one marked met or not.

## References
`verify` closes every step. `debug` takes over on a failure you cannot explain.
