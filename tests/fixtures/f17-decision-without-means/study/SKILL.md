---
name: study
description: Use to review a plan and report findings for the user to decide
budget: 400
role: read-only
allowed-tools: [Read, Grep, Glob]
---

## Trigger
A written plan, before implementation.

## Invariants
- Every axis is evaluated; skipping is not an answer.

## Procedure
1. Read the plan → **verify:** you can restate it in one sentence
2. Present findings one at a time → **verify:** each accepted or declined

## Stop conditions
- The design is wrong at the root: say so once and stop.

## Output
Findings per axis with the user's decision.

## References
`verify` owns the standing bar.
