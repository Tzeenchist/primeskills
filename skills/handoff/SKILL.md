---
name: handoff
description: Use to save working state so another session or agent can resume without losing the thread
budget: 500
role: write
---

# Handoff

## Trigger
Approaching a usage limit, ending a session with work unfinished, or passing
the task to another agent. Also on request: "save state", "checkpoint".

## Invariants
- The checkpoint lives in the repository, not in a home directory. It has to
  survive a different machine, a different agent, and a cleared context.
- Remaining work is assembled from the repository and the record, never copied
  from the previous checkpoint. Copying is how finished work stays open (G16).
- What was tried and failed is the most valuable section. It is the part the
  next reader cannot reconstruct.

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
5. The file is written; committing and pushing are separate permissions and
   neither follows from a session ending. Say the file exists, say whether the
   branch has a remote, and ask for each → **verify:** the file is in
   the diff, tests were green before the commit, and you say pushed, declined,
   or not asked for

## Stop conditions
- Tests are red: say so in the notes and do not imply the work is resumable
  without a fix.
- Uncommitted work you did not write: leave it, name it in the notes.

## Output
The path to the checkpoint file and a two-sentence statement of where the work
stands.

## References
`core/OUTPUT.md` covers reading a checkpoint back at session start.
