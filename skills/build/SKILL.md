---
name: build
description: Use when implementing a feature or fixing a bug, before writing implementation code
budget: 650
role: write
---

# Build

## Trigger
An approved plan with acceptance criteria, or a change small enough that the
planning gate does not apply (G2). Not for exploration — that is `brief`.

## Invariants
- Write the failing test first for executable behaviour. Documentation,
  declarative config and generated files take the cheapest deterministic proof
  instead — say which and why.
- A test written after the code proves the code runs, not that it is right.
- Red, green, refactor are three phases. Never blur them: no cleanup while
  making it pass, no new behaviour while refactoring.
- Every changed line traces to the request (PRINCIPLES 3).
- A task is done when its acceptance criteria are met *and* the standing bar is
  met. They are different questions and you need both.

## Procedure
1. Preflight: read the repository's own agent instructions, note the branch,
   what is already dirty and whose it is, and find the project's real commands
   → **verify:** you can name the test command and you have not claimed
   someone else's uncommitted work
2. Resolve what the suite will touch before running it — database, cache,
   directories — and print each one (G17) → **verify:** every named target is a
   test target you can point at, not a working or dev store
3. Run the suite once before touching anything → **verify:** you know which
   failures were already there
4. Restate the task as a verifiable goal → **verify:** it names a command or an
   observation that will settle it
5. Cut it into steps a single commit can carry → **verify:** each step has its
   own check, and no step needs a later one to be meaningful
6. Before a risky step — migration, bulk edit, refactor — take a snapshot that
   covers untracked files too, and a dump for data (G14) → **verify:** you
   restored it somewhere disposable and saw your newest file come back
7. **Red.** Write the test that fails for the right reason → **verify:** run it,
   record the failure message verbatim — that record is the red half of the
   proof and `verify` will read it rather than re-deriving it
8. **Green.** Write the least code that passes → **verify:** `verify` reports PASS
9. **Refactor.** Clean only what you just wrote → **verify:** tests still PASS,
   and the diff contains no unrelated change
10. Every 2–3 steps, commit atomically **where the commit rung is open**:
   `primeskills-run may commit` first, and if it refuses, ask instead of
   committing. Stage intentional files only, never `git add -A` → **verify:**
   the rung was checked, and `git diff --staged` shows exactly what you meant
   to include (G11)
11. Repeat from 7 until the acceptance criteria are met → **verify:** re-read
   them line by line and mark each one

## Stop conditions
- The test will not go red for the right reason: the test is wrong, or the
  behaviour already exists. Find out which before writing code.
- The plan turns out to be wrong mid-way: stop and say so. Do not quietly
  build something else (PRINCIPLES 8).
- A step needs an abstraction "for later": that is the moment to cut, not to
  generalise (PRINCIPLES 2).
- Three failed attempts at the same step, counted on the shared counter (G9):
  hand to `debug`, do not improvise.

## Output
The diff, the new tests, the recorded red run, the commits made, the attempt
count, and the acceptance criteria with each marked met or not.

## References
`verify` closes every step. `debug` takes over on a failure you cannot explain.
