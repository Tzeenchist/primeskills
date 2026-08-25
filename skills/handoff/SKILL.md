---
name: handoff
description: Use to save working state so another session or agent can resume without losing the thread
budget: 550
role: write
---

# Handoff

## Trigger
Approaching a usage limit, ending a session with work unfinished, or passing
the task to another agent. Also on request: "save state", "checkpoint".

## Invariants
- The checkpoint lives beside the work, in the repository's `.primeskills/`,
  not in a home directory: it has to survive a cleared context and a different
  agent on this machine. It does not travel — it is not committed (PS-022) —
  so a hand-off to another machine needs the text itself, not a promise that
  the file will be there.
- Remaining work is assembled from the repository and the record, never copied
  from the previous checkpoint. Copying is how finished work stays open (G6).
- What was tried and failed is the most valuable section. It is the part the
  next reader cannot reconstruct.
- The queue is committed and the checkpoint is not. Done in one beside open in
  the other makes the next reader trust the wrong file.

## Procedure
1. Gather state: `git status --short`, `git diff --cached --stat`,
   `git log --oneline -10` → **verify:** the branch and the modified files are
   what you expect
2. Rebuild remaining work from that state and from the decisions recorded this
   session → **verify:** every item names an anchor — a file, a commit, or the
   message that raised it
3. Drop items the record shows as resolved → **verify:** nothing carried over
   contradicts a decision already written down
4. Write `.primeskills/handoff/<branch>.md` with: what is being worked on,
   1–3 sentences of summary, decisions and why, remaining work in priority
   order, and notes — gotchas, blockers, open questions, approaches tried that
   did not work → **verify:** a reader who was not here could act on it
5. Record it: `primeskills-run note handoff "<branch>.md written"` → **verify:**
   `.primeskills/.gitignore` exists and `git status` does not offer the file.
   The checkpoint stays in this tree. It is read automatically at the start of
   the next session, so committing it would let anyone who can push to the
   branch write that opening context — and it carries blockers and dead ends
   that were never meant for a pull request. Say where the file is and that it
   does not travel
6. Reconcile the queue with this session, checkpoint first so a spent budget
   costs one file, not two. `merge` closes what landed; finish the rest — a
   commit and date on anything closed, an entry for what was found, and on
   work still moving a stage line named for the chain:
   `**Этап:** vet — green, waiting on land (<anchor>)`. No queue file: create
   one. Then `primeskills-run may commit` and commit the queue file by itself;
   a closed rung leaves it in the tree and says so → **verify:** the rung was
   checked, nothing closed without a commit, every stage line anchored

## Stop conditions
- Tests are red: say so in the notes and do not imply the work is resumable
  without a fix.
- Uncommitted work you did not write: leave it, name it in the notes.

## Output
The checkpoint's path, two sentences on where the work stands, and which queue
entries changed.

## References
`core/OUTPUT.md` covers reading a checkpoint back at session start.
