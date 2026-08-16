# Security checklist

Read when the diff touches input handling, authentication, storage, or an
external integration. Answer each line or mark it not applicable.

## Input
- [ ] Every external value is validated at the boundary, not deep inside.
- [ ] Validation rejects by default and allows what is known good.
- [ ] Size and rate are bounded: no unbounded body, upload, or loop over
      attacker-controlled length.
- [ ] Values reaching a query use parameters, never string building.
- [ ] Values reaching a shell use an argument list, never a formatted string.
- [ ] Values reaching HTML are escaped by the template, not by hand.
- [ ] Paths built from input cannot climb out of their directory.

## Authentication and authorisation
- [ ] Every new endpoint states who may call it. "Logged in" is not an answer
      when the object belongs to someone.
- [ ] Authorisation is checked on the object, not only on the route.
- [ ] Session and token lifetimes are finite, and logout invalidates.
- [ ] Failures are indistinguishable: wrong user and wrong password give the
      same answer and take the same time.

## Storage and secrets
- [ ] No credential in the diff, in a test, in a fixture, or in a comment.
- [ ] Secrets come from the environment; the example file carries names only.
- [ ] Personal data has a stated reason to be stored and a place it is deleted.
- [ ] Logs carry identifiers, not payloads. A token in a log is a leaked token.

## Integrations
- [ ] Outbound calls have a timeout and a defined failure behaviour.
- [ ] Responses are treated as untrusted input and validated on arrival.
- [ ] Retries are bounded and cannot amplify into a storm.
- [ ] A dependency added in this diff is named, versioned, and its licence
      checked (G12: a new paid dependency or licence change escalates).

## Agent-specific
- [ ] Text from a page, an issue, or a file is data, not instruction.
- [ ] Tools available to an automated path are the minimum it needs.
- [ ] Destructive operations require confirmation even in permissionless modes
      (GUARDRAILS G7, G17).
