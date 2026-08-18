---
name: revise
description: Use when a reviewer requested changes, to answer every comment and rework the branch
budget: 550
role: write
---

# Revise

## Trigger
An open pull request with comments on it. `vet` reviewed the diff before it was
opened; this handles what someone else said after.

## Invariants
- A comment is a claim about the code, not an instruction. You may decline one,
  and the reason is owed in writing.
- Every comment gets an answer, including the declined ones. Silence reads as
  agreement, and the reviewer re-reads the diff to find out what happened.
- Rework is a change like any other: smallest radius that answers the comment
  (P3), and the suite runs before the push.
- If the change moved, the pull request description that no longer describes it
  is a second defect, not a formality.

## Procedure
1. Collect every unresolved thread — review comments, line comments, the
   description → **verify:** you can state the count and which were already
   resolved by earlier pushes
2. Classify each: accept, needs the reviewer's answer, or decline
   → **verify:** none is left unclassified, and you can say why for each
3. Reply to the declined and the uncertain ones **before** touching code
   → **verify:** the reviewer can respond before you have spent work on it
4. Rework the accepted ones, grouped by theme, one commit per theme, each
   behind `primeskills-run may commit` → **verify:** the rung is open, and
   every changed line traces to a comment you can name
5. Call `verify` on the full suite → **verify:** PASS, recorded with
   `primeskills-run note revise "<result>"`
6. `primeskills-run may push`, then push and answer each thread with the
   commit that addresses it. An open pull request does not carry a standing
   permission to add to it → **verify:** the rung is open, and every thread
   carries either a commit or a stated reason
7. Update the description and the acceptance criteria if the change moved
   → **verify:** someone reading only the description gets the current diff

## Stop conditions
- A comment asks for a different design, not a fix: that is `plan`, and the
  user decides whether to do it here or in another branch.
- Comments contradict each other: report both and ask. Picking one silently
  makes you the author of a decision that was not yours.
- You disagree with a blocking comment and the reviewer holds: present both
  positions and hand it to the user (P8). Do not merge around it.
- The suite was already red before you started: say so, fix that first.

## Output
Per comment: what it asked, what you did or why not, and the commit. Then the
verification result and whether the pull request is ready for `merge`.

## References
`vet` is your own review before opening; `merge` puts it in afterwards.
