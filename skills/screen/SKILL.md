---
name: screen
description: Use to open a page in a browser and report measurable screen defects: overlap, overflow, contrast, focus, console errors
budget: 500
role: exercises
environment: a running dev or local app — the run navigates and focuses, and leaves whatever the page itself writes
allowed-tools: [Read, Grep, Glob, Bash, AskUserQuestion]
refs:
  - path: ../ui/ref/ui-states.md
    when: the call names a state — empty, loading, error — rather than a page
---

# Screen

## Trigger
A rendered page, when the question is what the browser shows and the test
suite cannot see it. `probe` reaches HTTP, the CLI and the logs; this reaches
the screen. Not for taste: composition, wording and beauty are not measured
here, and saying they passed would be a lie.

## Invariants
- Judgement is the runner's, not yours. No screenshot enters the conversation;
  the report is text, and a saved image is named by path only.
- Three screens a call, three minutes, twenty-five lines. More screens are
  another call, so the cost stays visible.
- An address and an anchor are both required. Without the anchor a clean
  report may belong to a login page — the run says NOT RUN and prints the URL
  it actually landed on.
- Every check ends in one of three verdicts: passed, found, or not measured
  with the reason. Contrast over a gradient is the third, never the first.
- Development or local only. Production is not a target here (G8).

## Procedure
1. Name the address, the anchor that proves it is the right screen, and the
   viewport → **verify:** the anchor is a selector you expect on that screen
   and nowhere else, and the address is not production
2. Run `skills/screen/bin/screen.py --screen <url> <anchor> [goal]`
   → **verify:** the command printed a report, and its exit code is 0 (clean),
   1 (findings), 2 (frame refused), 3 (tooling) or 4 (timed out)
3. Read the findings against the page: each names a selector and a measured
   number → **verify:** you can point at the element the runner names
4. Report what was checked and what was not, including every `НЕ ИЗМЕРЕНО`
   with its reason → **verify:** the unmeasured are listed, not dropped
5. When a finding needs the user's decision, offer it by the means in
   `core/OUTPUT.md` §Asking → **verify:** the user accepted or declined it

## Stop conditions
- The anchor is missing on the page: stop, report NOT RUN with the final URL.
  A screen you did not reach is never a pass.
- The frame refuses the call (no address, no anchor, a fourth screen): fix the
  call, never widen the frame.
- The browser or the package is missing: the report names the install command;
  run it once, then retry. Twice failing is a blocker, not a third guess (P6).

## Output
One block per screen: the address it landed on, findings first with selector
and measured value, then what could not be measured and why, then a counter of
the checks that passed. If the report was truncated, say how many lines went.

## References
`core/OUTPUT.md` §Asking for offering a decision; `probe` for everything the
browser is not needed for; `ui` for the states a call may name.
