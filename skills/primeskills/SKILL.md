---
name: primeskills
description: Use to print the guide to this set of skills
budget: 300
role: write
---

# Primeskills

## Trigger
"What can this set do", "which skill do I use for that", or a first session
with the set installed. Also on request: `/primeskills`.

## Invariants
- This skill calls no other skill, and no other skill calls it. It answers a
  question *about* the set; it does not do work *in* it.
- The guide is generated from the set, never retyped. A guide written by hand
  describes the set as it was on the day it was written.
- Hand the guide over whole. Summarising it replaces the reader's reading with
  yours, and the guide is what they asked for.
- The language is the reader's, asked once and remembered.

## Procedure
1. Read the remembered language: `primeskills-help --which-lang`
   → **verify:** it printed a language, or `unset`
2. If `unset`, ask which language to use — English or Russian — and take
   English if the user has no preference → **verify:** you have an answer and
   did not guess silently
3. Remember it: `primeskills-help --set-lang <en|ru>` → **verify:**
   `--which-lang` now returns that language
4. Print it: `primeskills-help` → **verify:** the output ends with the line
   counting skills and sequences
5. Give the output unchanged → **verify:** you added no summary, no ranking
   and no advice on top

## Stop conditions
- `primeskills-help` is not on PATH: say so and point at `primeskills-doctor`.
  Never describe the set from memory; that is how a wrong guide gets written.
- The question is about one skill, not the set: answer it from that skill's own
  text instead of printing everything.

## Output
The guide, as printed, in the reader's language. Then one line: how to change
the language, and that the choice is remembered.

## References
None. This skill deliberately stands alone.
