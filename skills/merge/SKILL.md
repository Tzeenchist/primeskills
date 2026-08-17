---
name: merge
description: Use to merge an approved change into the base branch once CI is green
budget: 500
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
   read `.primeskills/run/` for the `vet` and `probe` verdicts → **verify:**
   you list who approved, or say the project requires none
4. Check the branch is current with the base → **verify:** either it merges
   cleanly, or you report the conflict and stop rather than resolving it blind
5. Merge in the project's own style — merge commit, squash, or rebase of your
   own unpushed branch onto the base, whichever the repository uses. Rewriting
   history anyone else has pulled is outside your authority whatever the style → **verify:** the history after matches the shape
   of the history before
6. Confirm the result → **verify:** the base branch contains the change and its
   tests are green on the base, not only on the branch
7. Offer to delete the merged branch if the project does that, and delete it
   only on a yes → **verify:** you asked, and nothing unmerged was deleted

## Stop conditions
- CI is red, missing, or ran on a different commit: stop and report.
- A conflict: bring it back to the user. Resolving someone else's conflict
  blind is how work disappears.
- The base is protected and the merge needs rights you were not given: say so.
- You wrote the change and nobody reviewed it: that is not ready to merge.

## Output
What merged where, the commit on the base, the CI evidence you read, and
whether the branch was deleted.

## References
`land` prepares the change; `deploy` takes the base branch onward.
