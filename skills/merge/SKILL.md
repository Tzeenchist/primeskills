---
name: merge
description: Use to merge an approved change into the base branch once CI is green
budget: 650
role: write
---

# Merge

## Trigger
A pull request that is approved and green, or a local branch the user has told
you to integrate. `land` prepared it; this puts it in.

## Invariants
- The user decides that a change merges. You decide nothing here — you check
  that it is safe to carry out the decision they already made.
- Green means read, not assumed. A stale CI run describes an older commit.
- The base branch is the one the project uses, not the one you would pick.
- Never force, never rewrite, never merge your own unreviewed work.

## Procedure
1. Confirm the decision is the user's and name what you are merging: branch,
   target, commit → **verify:** you can quote where the user asked for it
2. Fetch and read the latest CI result for **this** head commit → **verify:**
   the run's commit matches `git rev-parse HEAD`, and it passed
3. Check review state: approvals present, no unresolved blocking comments, and
   `primeskills-run check vet` for the review verdict → **verify:** you list
   who approved, or say the project requires none, and no verdict you rely on
   came back stale
4. Check the branch is current with the base → **verify:** either it merges
   cleanly, or you report the conflict and stop rather than resolving it blind
5. Merge it somewhere disposable first: a scratch worktree off the base, the
   merge done there, the suite run there → **verify:** the result is green
   away from the base, so a red suite costs a temporary directory instead of
   the branch everyone works on
6. `primeskills-run may merge`, then merge in the project's own style — merge
   commit, squash, or rebase of your own unpushed branch onto the base,
   whichever the repository uses. Rewriting history anyone else has pulled is
   outside your authority whatever the style → **verify:** the history after
   matches the shape of the history before
7. Confirm the result → **verify:** the base branch contains the change and its
   tests are green on the base, not only on the branch
8. Offer to delete the merged branch if the project does that, and delete it
   only on a yes → **verify:** you asked, and nothing unmerged was deleted

## Stop conditions
- CI is red, missing, or ran on a different commit: stop and report.
- The trial merge in step 5 is red: stop there. The base is untouched, which is
  the whole point of doing it away from the base — report what failed and hand
  it back to `build`.
- The base is red *after* the merge: say so immediately and plainly, before
  anything else. Undoing a merge on a shared base is its own rung and its own
  decision — offer the revert, name what it will do, and wait.
- A conflict: bring it back to the user. Resolving someone else's conflict
  blind is how work disappears.
- The base is protected and the merge needs rights you were not given: say so.
- You wrote the change and nobody reviewed it: that is not ready to merge.

## Output
What merged where, the commit on the base, the CI evidence you read, and
whether the branch was deleted.

## References
`land` prepares the change; `deploy` takes the base branch onward.
