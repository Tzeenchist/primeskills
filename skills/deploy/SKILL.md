---
name: deploy
description: Use to put merged work into an environment, with a rollback ready before it starts
budget: 700
role: write
---

# Deploy

## Trigger
The base branch carries the change and the user has asked for it to go out.
Never on your own initiative, and never as the tail end of merging.

## Invariants
- The rung is checked before the first write, not before the last one. The
  migration is a write.
- Name the environment out loud before touching it. The worst outcome here is
  not a failed deploy, it is a successful one somewhere unintended (G8).
- The rollback exists before the deploy starts, and you have said how long it
  takes. A plan to "revert the commit" is not a rollback.
- Deployed is not working. Until something observed says the new version serves
  real traffic correctly, it has not been proved.
- Production changes are the user's call each time. Prior permission for one
  deploy is not permission for the next.

## Procedure
1. Resolve the target: which environment, which host, which database, which
   branch or tag → **verify:** print it and have the user confirm it is what
   they meant, when it is production
2. State the rollback, its cost in minutes, and whether it is possible at all
   after the migrations in this release. Where there is a way back, ask whether
   you may use it without asking again, and record only the answer you were
   given: `primeskills-run grant rollback --target <the target> "<what the user
   allowed>"`. Writing that line before the question is granting yourself a
   permission, which the ladder forbids and the journal cannot detect. Where
   there is no way back, record only that the user heard it —
   `primeskills-run note deploy "forward only, heard and accepted"` — because
   understanding that a release cannot be undone is not permission to release
   it → **verify:** a concrete procedure with its prerequisites checked, or an
   explicit "forward only" the user has heard before you start, and the record
   says which
3. Back up what the deploy can destroy — data, uploaded files, configuration
   → **verify:** the backup exists and you can name how to restore from it (G11)
4. Check what ships: the commit going out and how it differs from what runs now
   → **verify:** you can list migrations, config changes, and new dependencies
5. `primeskills-run may migrate --target <the target from step 1> --peek`,
   then the same call without `--peek` as you run it — that one spends the
   single use. Migrations are their own rung because
   they are usually the half you cannot undo → **verify:** the rung is open for
   this target, and the migration ran against the target you resolved, not
   against the one your shell happened to point at
6. `may deploy --target <the same target> --peek`, then without `--peek` as
   you release
   → **verify:** the rung is open for this target, the process reports success,
   and the running version is the commit you intended, read from the
   environment rather than assumed
7. Check health on the real thing: the main path a user takes, plus error rate
   and logs → **verify:** you exercised it, and you say what you exercised
8. Report → **verify:** the user knows what went out, where, and how to undo it

## Stop conditions
- No rollback and no forward-only decision in the record: stop. A deploy you
  cannot undo is the user's decision, not your task — but once they have made
  it knowingly, it is a plan, not a blocker.
- The target cannot be proved to be the intended one: stop (G8, G15).
- Health check fails: `primeskills-run may rollback --target <the target>`,
  then carry out the rollback decided in step 2, and if that decision was "forward only" —
  because a migration made the old version incompatible — say so and ask. Debugging a live environment while users sit
  on the broken version is the wrong order; rolling into a schema the old code
  cannot read is the wrong direction.
- Migrations are irreversible and the backup is missing or untested: stop.

## Output
Environment, commit deployed, migrations run, backup location, health check
result, and the rollback command with its cost.

## References
`merge` puts the change on the base; `release` runs the three in order.
