---
name: measure
description: Use when something got slower, to set a baseline and find where the time actually goes
budget: 550
role: reports
allowed-tools: [Read, Grep, Glob, Bash, WebFetch, WebSearch, AskUserQuestion]
---

# Measure

## Trigger
Something is slower than it should be, or a change might have cost speed and
nobody knows. Not for a failure — a wrong answer is `debug`.

## Invariants
- "Slow" is a comparison. Without the other side of it there is no finding,
  only a feeling.
- The bottleneck is almost never where it feels. Measure first, and let the
  measurement pick what to look at.
- You measure and report. The fix belongs to `build`, so that the person
  reading your numbers can still disagree with the conclusion.
- A measurement that changes what it measures is not evidence: a debug build,
  a cold cache and a first-run import each cost more than the thing you meant
  to time. Name the conditions or the number means nothing.

## Procedure
1. Name the quantity and the target: what is measured, in what unit, and what
   would count as fixed → **verify:** both are numbers, not adjectives
2. Resolve where you are measuring — host, database, dataset size, build mode
   → **verify:** you printed it, and it is not production unless the user said
   so (G17)
3. Take the baseline on the current commit and record it:
   `primeskills-run note measure "<quantity>: <number> on <conditions>"`
   → **verify:** the record names the commit and the conditions
4. Repeat the baseline run → **verify:** the two agree within a spread you
   state; if they do not, the environment is too noisy to conclude anything and
   you say that instead of averaging it away
5. Break the time down by layer — query, I/O, network, render, CPU — with a
   profiler or timers, not by reading the code → **verify:** the parts add up
   to the whole, and you name the tool that produced them
6. Name the largest cost and what removing it would buy, in the unit from
   step 1 → **verify:** the estimate is a number, and you say what it assumes
7. If a change is already in hand, measure it the same way and compare against
   the recorded baseline → **verify:** same conditions, same command, both
   numbers shown

## Stop conditions
- Numbers stitched from different runs, machines or datasets: throw them out
  and start one clean series.
- The profiler needs a production database or real user data to be meaningful:
  stop and ask (G17, G12).
- You start fixing: stop. Hand the breakdown to `build`.

## Output
Quantity and target, baseline with conditions, the breakdown by layer, the
largest cost with an estimate, and what you did not measure.

## References
`debug` when the slowness is a defect rather than a cost. `build` for the fix.
