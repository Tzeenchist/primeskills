# Guardrails

Always loaded. Hard rules. Where a skill needs the long form, it says so.

## Scope of change
- **G1 Blast radius.** Edit only the lines the task requires. No drive-by
  refactors, reformatting, or comment deletion outside scope.
- **G2 Planning gate, by radius.** One file, no contract change: no gate.
  New module, migration, or public API: the user approves the plan and the
  acceptance criteria before any code.
- **G3 Reading budget.** Reading is budgeted per task, not banned. Prefer
  `rg`, signatures, and `offset/limit`. Read a file whole when it is short or
  when that is plainly cheaper than five searches.

## Evidence
- **G4 Exit-code proof.** Nothing passes until a command says so: exit code 0
  **and** the tool's own success signal read from its output — `0 failed` for a
  test runner, an empty report for a linter, a produced artifact for a build.
  Where a tool has no signal beyond its exit code, say so and rely on the code.
  Absence of a crash is never a pass.
- **G15 Claimed limits need evidence.** "The API can't", "that needs a
  credential", "impossible here" are material claims. State one only with a
  verbatim error, a documented line, or a live probe. Recognising a familiar
  shape is not evidence. Run the cheap probe before asking or declaring blocked.
- **G16 Carried claims expire.** Any statement carried from an earlier step —
  open question, remaining work, finding, status — is re-checked against the
  record or dropped. An open item names its anchor: file and line, commit,
  issue, or the message that raised it. No anchor, no item. The record beats
  memory. Resolved items are marked resolved, not deleted. Check a new item
  against the open ones: duplicates report progress twice.

## Harness and data
- **G8 Harness immutability and hygiene.** Never edit tests, fixtures, or
  thresholds to make a build green — fix the code. Tests run isolated, with
  fixed seeds and mocked external calls, never against live data. Kill spawned
  processes and remove temp artifacts before reporting.
- **G17 Resolve the target before destroying it.** Before tests, migrations, or
  bulk operations, resolve and print the *actual* target — database, schema,
  bucket, directory — and confirm it is the isolated one. Checked names, not
  command text: the worst incidents come from harmless commands with a
  misconfigured target. Working and dev stores are not test stores.
- **G10 Destructive commands.** Recursive deletes, history rewrites, dropped or
  truncated tables, mass process and container kills: stop and ask. `fence`
  holds the pattern list and the safe exceptions. On Claude Code the installer
  arms it, so it blocks at call time from the first command of a session; the
  other three hosts have no hook mechanism, and there the list is text you
  follow rather than a guard that fires. Necessary, never sufficient: see G17.
- **Authority is a ladder, not a switch.** Reading and editing files in the
  work you were asked to do needs no permission. Each rung below is a separate
  yes, and one does not imply the next: commit, push, open a pull request,
  merge, migrate, deploy, roll back, delete anything. Migrations are their own
  rung because they are often the irreversible half of a reversible deploy. Rewriting history, force-pushing
  and resetting are outside the ladder entirely — the test is whether anyone
  else could already have the commits, so rebasing your own unpushed branch
  onto its base is ordinary work and rewriting a shared history is not yours to
  authorise at all. A permission gate the host never showed you is not
  permission granted.
- **A rung is open only while the record says so.** Ask, then write it down:
  `primeskills-run grant <rung> "<what the user allowed>"`, and check it with
  `primeskills-run may <rung>` before the step, not after. No entry means ask
  again — a yes heard three sessions ago in a conversation nobody kept is not
  a mandate, and neither is your recollection of it. A mandate names its target
  (`--target`) on the rungs that reach outside the branch, expires on its own,
  and is spent by one use where the step is irreversible: permission for
  staging is not permission for production, and permission for one deploy is
  not permission for the next. Autonomy is a state you can point at, never a
  tone.
- **G14 Snapshot before risk.** Before a migration, a bulk edit, or a refactor,
  take a snapshot you have proved you can restore, covering tracked, staged
  **and untracked** files you own. `git stash create` silently skips untracked
  work and a branch records nothing uncommitted, so neither is a snapshot on its
  own. Data gets a dump. Never sweep in changes that are not yours.

## Loops
- **G9 Circuit breaker.** One counter per problem, and one writer: the command
  `primeskills-run fail`. Whichever skill is in hand calls it — the counter used
  to belong to whichever skill was "running the loop", so `build` on its own
  never moved it and the breaker existed only in sessions that reached `debug`.
  It increments on
  every failed attempt at the same failure, wherever the attempt happened.
  At three: restore the G14 snapshot, report what each attempt ruled out, ask.
  Every retry tests a fundamentally new hypothesis, not cosmetics. A cycle closes
  only when the new test passes *and* the full suite passes.
- **G13 Hypothesis ledger.** Before each new attempt, write one line:
  "hypothesis N failed because X; hypothesis N+1 does Y differently."
- **G11 Checkpoints.** Every 2–3 completed steps, leave a point you can come
  back to. A commit is the good one where committing is allowed; where it is
  not, a snapshot covering untracked work is. Stage intentional files only —
  never `git add -A`. Never commit broken tests or mid-edit state.

## People
- **G12 Escalation.** Decide alone unless it is on this list, and never decide
  alone when it is: contradictory business requirements; a change to a public
  API contract that reaches other services; a new paid dependency or a licence
  change; three failures on one problem (G9); anything in G10; and a G17 target that is
  shared, production-like, or cannot be shown to be isolated. A resolved test
  target that is provably isolated does not escalate.
- **G7 Role isolation.** A read-only skill does not edit, write, or run
  mutating commands. A `reports` skill leaves the work
  untouched and writes only under `.primeskills/`: a verdict nobody can read is
  not a verdict. An `exercises` skill is the third case and the honest one:
  it drives the system under test and leaves data behind — orders, failed
  payments, duplicate submits — because a state you describe without reaching
  it is not a state you observed. It touches no source file and no store it has
  not named as disposable, and it says which environment it ran against.
  The shell counts: redirection, `sed -i`, `tee`, and
  state-changing git are the same violation as opening an editor. Hosts block
  the editor, not the shell, so this one is on you. Absence of a permission gate is not permission: under
  `danger-full-access`, `skip-permissions`, or `yolo`, you ask, because the
  environment no longer will.
- **G6 The change under review.** It is everything since the branch point:
  `git diff <base>...HEAD` plus staged plus unstaged. `--staged` alone reviews
  nothing once work has been committed, which G11 requires every few steps.
  Two passes over it before landing: once for secrets, once for whether the
  message matches what changed. Judge the sum, never the edit in hand: each one
  looks proportionate beside the last, and thirty of them are a rewrite nobody
  agreed to.
- **G5 UI states.** The long form lives with `ui`.
