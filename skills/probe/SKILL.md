---
name: probe
description: Use to click through a running app and report the bugs it actually has, without fixing them
budget: 600
role: exercises
environment: disposable — a store that may be left dirty and can be reset
allowed-tools: [Read, Grep, Glob, Bash, WebFetch, WebSearch, AskUserQuestion]
refs:
  - path: ../ui/ref/ui-states.md
    when: the system under test has a user interface
---

# Probe

## Trigger
A running build, after `verify` is green. Checks behaviour of the system as it
runs; the properties of the diff are `vet`.

## Invariants
- You report. You do not fix. A found bug that you also fixed cannot be
  reproduced by the person reading your report.
- Read-only means the codebase, not the application. Producing an empty list or
  a failed payment means writing application data, so you need a disposable
  environment with a stated way to reset it. Without one, say which states you
  could not produce.
- Test against development or a staging copy. Production is touched only with
  explicit confirmation, and never with writes (G17).
- A defect report that cannot be reproduced from its own text is not a report.
- What you did not test is part of the result. Say it.

## Procedure
1. Confirm what you are pointed at: URL, branch, commit, database, and how it
   gets reset → **verify:** it is disposable — not a working store, not
   production (G17)
2. Walk the main path a real user takes, end to end — through the interface if
   you have a way to drive one, through its endpoints if you do not
   → **verify:** you performed each step, not read the code that implements it,
   and you said which of the two you did
3. At each screen or endpoint, exercise the states: nothing yet, one item,
   many, slow, failed → **verify:** each state was either produced, or named in
   the report as one you had no way to produce. Both are results; a state you
   describe without reaching is neither
4. Push the boundaries: empty input, maximum length, wrong type, duplicate
   submit, back button mid-flow → **verify:** the response is recorded verbatim
5. For interfaces, walk the keyboard path and read `../ui/ref/ui-states.md`
   → **verify:** focus never disappears and no state is missing
6. For each defect, write: what you did, what happened, what should have
   happened → **verify:** someone else could follow it and see the same thing
7. Rank by user impact, not by how easy the fix looks → **verify:** the top item
   is the one that costs the user most

## Stop conditions
- The build does not start: that is the report. Do not work around it and test
  something else.
- You are about to fix something: stop, write it down, hand to `build`.
- A defect needs production data to see: say so, do not reach for production.

## Output
A verdict first: `PASS`, `BLOCK`, or `NOT RUN` with the reason. `BLOCK` when any
defect stops a user completing the main path. Then defects ranked by impact,
each with steps, observed, expected, and what was not covered. Record the
verdict: `primeskills-run note probe "<verdict>"`.

## References
`../ui/ref/ui-states.md` for the state matrix. `vet` covers the diff.
