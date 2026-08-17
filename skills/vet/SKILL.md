---
name: vet
description: Use to review a diff before it merges, for correctness, security and scope
budget: 800
role: reports
allowed-tools: [Read, Grep, Glob, Bash, WebFetch, WebSearch, AskUserQuestion]
refs:
  - path: ref/security.md
    when: the diff touches input handling, authentication, storage, or an external integration
---

# Vet

## Trigger
A diff that is ready to merge, after `verify` reports PASS. Reviews the change,
not the running system — that is `probe`.

## Invariants
- Approve a change that improves the health of the codebase, even if it is not
  how you would have written it. Perfect is not the bar; better is.
- Every axis gets an answer. "Nothing found" is an answer; silence is not.
- A finding names a file and a line. "Consider improving error handling" is not
  a review comment, it is a mood.
- You read and report. Fixing is `build`.

## Procedure
1. Read the whole change — `git diff <base>...HEAD` plus staged and unstaged
   (G6) — and state what it is meant to do
   → **verify:** your statement matches the plan or the commit message, and you
   say so when it does not
2. Scan for secrets first: keys, tokens, passwords, `.env` files, real
   identifiers in tests → **verify:** you name each hit or state there are none
   (G6)
3. Correctness: for each changed path, what happens on nil, empty, and error
   input → **verify:** each has an answer drawn from the code, not assumed
4. Scope: does every changed line trace to the request → **verify:** you name
   any line that does not, including formatting and comment churn (G1)
5. Security: read `ref/security.md` if the diff touches input, auth, storage, or
   an integration → **verify:** the checklist is answered or explicitly not
   applicable
6. Tests: does a new test fail without this change → **verify:** you can point
   at the test, or you say coverage is missing
7. Readability: would someone unfamiliar understand this in six months
   → **verify:** you name the place they would stumble, or state there is none
8. Sort findings: blocking, worth fixing, optional → **verify:** each blocking
   finding says what breaks, with the input that breaks it

## Stop conditions
- The diff does something the plan did not ask for: that is a blocking finding,
  not a nice-to-have.
- You disagree with a decision the user already made: say it once as an
  optional finding and move on. Re-litigating is not reviewing.
- A finding you raised earlier is already fixed in this diff: strike it, do not
  carry it (G16).
- The change is too large to review honestly: say so and ask for it in parts.

## Output
Findings grouped blocking / worth fixing / optional, each with file, line, and
the failure it causes. Then a verdict: merge, merge after the blocking ones, or
rework — recorded with `primeskills-run note vet "<verdict>"`.

## References
`ref/security.md` for the input, auth, storage and integration checklist.
