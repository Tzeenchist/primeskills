---
name: deploy
description: Use to put merged work into an environment, with a rollback ready before it starts
budget: 550
role: write
---

# Deploy

## Trigger
The base branch carries the change and the user has asked for it to go out.
Never on your own initiative, and never as the tail end of merging.

## Invariants
- Name the environment out loud before touching it. The worst outcome here is
  not a failed deploy, it is a successful one somewhere unintended (G17).
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
2. State the rollback and its cost in minutes → **verify:** it is a concrete
   command or procedure, and you have checked its prerequisites exist
3. Back up what the deploy can destroy — data, uploaded files, configuration
   → **verify:** the backup exists and you can name how to restore from it (G14)
4. Check what ships: the commit going out and how it differs from what runs now
   → **verify:** you can list migrations, config changes, and new dependencies
5. Run migrations before or with the release as the project requires
   → **verify:** the migration ran against the target you resolved in step 1,
   not against the one your shell happened to point at
6. Release → **verify:** the process reports success and the running version is
   the commit you intended, read from the environment rather than assumed
7. Check health on the real thing: the main path a user takes, plus error rate
   and logs → **verify:** you exercised it, and you say what you exercised
8. Report → **verify:** the user knows what went out, where, and how to undo it

## Stop conditions
- No rollback: stop. A deploy you cannot undo is a decision, not a task.
- The target cannot be proved to be the intended one: stop (G17, G12).
- Health check fails: roll back first, diagnose after. Debugging a live
  environment while users sit on the broken version is the wrong order.
- Migrations are irreversible and the backup is missing or untested: stop.

## Output
Environment, commit deployed, migrations run, backup location, health check
result, and the rollback command with its cost.

## References
`merge` puts the change on the base; `release` runs the three in order.
