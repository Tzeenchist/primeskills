---
name: lazy
description: Use to carry an idea through planning, implementation and review to a deployed change, stopping once
budget: 350
tier: flow
calls: [autoplan, cycle, close, merge, deploy]
role: write
---

# Lazy

## Trigger
A rough idea the user wants carried to a running change without being asked
again at every stage.

## Invariants
- One stop, and it is deliberate: the plan and every rung the run needs are
  settled there, before any code. A rung discovered later is another stop.
- Mandates quote the user. A flow that writes its own permission has proved
  nothing (G9).
- The chain carries the ladder, it does not shorten it.

## Procedure
1. Call `autoplan` → **verify:** the user approved the plan, and the acceptance
   criteria are written down
2. In the same stop, ask which rungs this run may open and against which
   target, naming each: commit, push, pr, merge, deploy, and migrate if the
   change carries one (`OUTPUT §Asking`). Write each as its own
   `primeskills-run grant <rung> --target <what> --for <minutes>`, quoting the
   answer → **verify:** `primeskills-run show` lists the rungs the user named
   and no other
3. Call `cycle` → **verify:** every acceptance criterion is marked individually
   and the suite is green
4. Call `close` → **verify:** the PR exists, or the flow stopped and said why
5. Read `primeskills-run may merge --peek`, then call `merge` → **verify:** the
   base branch carries the change and is green on the base
6. Read `may deploy --target <named> --peek`, then call `deploy` → **verify:**
   health checked on the environment named in step 2, rollback known
7. Report, then `primeskills-run revoke` what is still open → **verify:** no
   mandate outlives the run that asked for it

## Stop conditions
- A stage stops: the flow stops there. Never open a rung to get past it.
- A mandate is missing or expired: ask again. Re-granting it yourself is the
  defect this flow avoids.
- Escalation (G15) or the breaker at three (G12): leave the chain, then ask.

## Output
Per stage: what it did and its evidence. At the end, what is live, how to undo
it, and which mandates were revoked.

## References
`autoplan`, `cycle`, `close`, `merge`, `deploy`. `release` is the tail alone,
`close` the chain that stops at handover.
