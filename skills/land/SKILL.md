---
name: land
description: Use to commit, push and open a pull request once work is verified and reviewed
budget: 750
role: write
---

# Land

## Trigger
`verify` reports PASS, `vet` returns no blocking findings, and `probe` returned
PASS. Not before all three. `NOT RUN` counts only when the change touches no
running interface; when it does, an interface nobody could bring up is an
unknown, and landing on an unknown is the thing this order exists to prevent.

## Invariants
- The commit message describes what the diff does. If you cannot write the
  message from the diff, the commit contains more than one change.
- Two passes over the whole change (G6): once for secrets, once for whether the
  message matches. Neither substitutes for the other.
- Integration is the user's decision. You prepare it; merging, releasing, and
  deploying are theirs to choose (PRINCIPLES 8).
- Never force-push, never rewrite history, never `git add -A`.
- Commit, push and pull request are three rungs, not one gesture. Each is
  checked against the run record before it happens, never remembered afterwards.

## Procedure
1. Ask the record whether the proof is still about this tree:
   `primeskills-run check verify`. Stale or missing means run the full suite
   again on the final state → **verify:** exit 0, counts match, and `check`
   answers `current`
2. First pass over the whole change (G6): scan for keys, tokens, passwords,
   `.env` changes, real identifiers, absolute paths from your machine
   → **verify:** you name each hit or state there are none
3. Second pass over the same range: read it and write the message from it → **verify:** every
   claim in the message appears in the diff, and every change in the diff is
   covered by the message
4. Check the branch: not the default branch → **verify:** you are on a working
   branch, or you create one before committing
5. `primeskills-run may commit`. If it refuses, ask and record the answer
   before going on → **verify:** the rung is open and its scope covers this
   branch
6. Commit in conventional form: type, scope, one-line summary, then why
   → **verify:** the summary reads as what changed, not as what you did today
7. `primeskills-run may push`, then push. Push is its own rung and a commit
   mandate never implies it → **verify:** the rung is open, then the branch is
   on the remote
8. `primeskills-run may pr`, then open a PR if the remote is hosted; if it is a
   bare or local remote, there is nothing to open — say so and put the
   acceptance criteria in the report instead → **verify:** the rung is open, and
   the criteria are visible either in the PR or in what you hand back
9. If memory is enabled, record what the code and history do not: a decision and
   its reason, a rare bug with its root, an option rejected and why
   → **verify:** nothing recorded is already derivable from `git log`
10. Report the PR URL and what remains → **verify:** you state plainly that
   merging and deploying are the user's next call, and no file from
   `.primeskills/` went up with the change

## Stop conditions
- Tests are red: stop. There is no version of this step that starts here.
- The diff contains a change nobody asked for: remove it or say why it stays.
- The push is rejected: read why. A rejected push is information about the
  remote, and force is not the answer to it.
- No hosting for a pull request: that is not a failure, it is a different
  handover. Never report a PR you did not create.
- You are on the default branch with uncommitted work: say so and ask. Creating
  a branch is cheap, but choosing where the user's work lives is theirs.

## Output
Branch, commit, PR URL, the acceptance criteria with each marked, and one line
on what is left for the user to decide.

## References
`GUARDRAILS.md` G6 for the commit audit, G12 for what escalates.
