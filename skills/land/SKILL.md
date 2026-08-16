---
name: land
description: Use to commit, push and open a pull request once work is verified and reviewed
budget: 800
role: write
---

# Land

## Trigger
`verify` reports PASS and `vet` returns no blocking findings. Not before both.

## Invariants
- The commit message describes what the diff does. If you cannot write the
  message from the diff, the commit contains more than one change.
- Two passes over `git diff --staged`: once for secrets, once for whether the
  message matches. Neither substitutes for the other (G6).
- Integration is the user's decision. You prepare it; merging, releasing, and
  deploying are theirs to choose (PRINCIPLES §8).
- Never force-push, never rewrite history, never `git add -A`.

## Procedure
1. Run the full suite one more time on the final state → **verify:** exit 0 and
   the counts match what `verify` reported
2. First pass over `git diff --staged`: scan for keys, tokens, passwords,
   `.env` changes, real identifiers, absolute paths from your machine
   → **verify:** you name each hit or state there are none
3. Second pass: read the diff and write the message from it → **verify:** every
   claim in the message appears in the diff, and every change in the diff is
   covered by the message
4. Check the branch: not the default branch → **verify:** you are on a working
   branch, or you create one before committing
5. Commit in conventional form: type, scope, one-line summary, then why
   → **verify:** the summary reads as what changed, not as what you did today
6. Push and open the PR with the plan's acceptance criteria as the description
   → **verify:** the PR shows each criterion and how it was met
7. If memory is enabled, record what the code and history do not: a decision and
   its reason, a rare bug with its root, an option rejected and why
   → **verify:** nothing recorded is already derivable from `git log`
8. Report the PR URL and what remains → **verify:** you state plainly that
   merging and deploying are the user's next call

## Stop conditions
- Tests are red: stop. There is no version of this step that starts here.
- The diff contains a change nobody asked for: remove it or say why it stays.
- The push is rejected: read why. A rejected push is information about the
  remote, and force is not the answer to it.
- You are on the default branch with uncommitted work: branch first, ask second.

## Output
Branch, commit, PR URL, the acceptance criteria with each marked, and one line
on what is left for the user to decide.

## References
`GUARDRAILS.md` G6 for the commit audit, G12 for what escalates.
