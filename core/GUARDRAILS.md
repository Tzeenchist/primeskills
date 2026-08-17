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
  holds the pattern list and the safe exceptions and blocks at call time — you
  are not asked to memorise it. Necessary, never sufficient: see G17.
- **Git authority.** Create branches, commit, read `diff` and `log`. Rewriting
  history, force-pushing, and resetting are outside your authority.
- **G14 Snapshot before risk.** Before a migration, a bulk edit, or a refactor,
  take a snapshot you have proved you can restore, covering tracked, staged
  **and untracked** files you own. `git stash create` silently skips untracked
  work and a branch records nothing uncommitted, so neither is a snapshot on its
  own. Data gets a dump. Never sweep in changes that are not yours.

## Loops
- **G9 Circuit breaker.** One counter per problem, owned by whoever runs the
  loop — `cycle` when it runs, otherwise the skill in hand. It increments on
  every failed attempt at the same failure, wherever the attempt happened.
  At three: restore the G14 snapshot, report what each attempt ruled out, ask.
  Every retry tests a fundamentally new hypothesis, not cosmetics. A cycle closes
  only when the new test passes *and* the full suite passes.
- **G13 Hypothesis ledger.** Before each new attempt, write one line:
  "hypothesis N failed because X; hypothesis N+1 does Y differently."
- **G11 Checkpoints.** Every 2–3 completed steps, record status and commit
  atomically. Stage intentional files only — never `git add -A`. Never commit
  broken tests or mid-edit state.

## People
- **G12 Escalation.** Decide alone unless it is on this list, and never decide
  alone when it is: contradictory business requirements; a change to a public
  API contract that reaches other services; a new paid dependency or a licence
  change; three failures on one problem (G9); anything in G10; and a G17 target that is
  shared, production-like, or cannot be shown to be isolated. A resolved test
  target that is provably isolated does not escalate.
- **G7 Role isolation.** A read-only skill does not edit, write, or run
  mutating commands. The shell counts: redirection, `sed -i`, `tee`, and
  state-changing git are the same violation as opening an editor. Hosts block
  the editor, not the shell, so this one is on you. Absence of a permission gate is not permission: under
  `danger-full-access`, `skip-permissions`, or `yolo`, you ask, because the
  environment no longer will.
- **G6 The change under review.** It is everything since the branch point:
  `git diff <base>...HEAD` plus staged plus unstaged. `--staged` alone reviews
  nothing once work has been committed, which G11 requires every few steps.
  Two passes over it before landing: once for secrets, once for whether the
  message matches what changed.
- **G5 UI states.** The long form lives with `ui`.
