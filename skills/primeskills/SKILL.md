---
name: primeskills
description: Use to print the guide to this set of skills
budget: 450
role: reports
allowed-tools: [Read, Grep, Glob, Bash]
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
- Hand the guide over whole: summarising replaces the reader's reading with
  yours. Translating does not — every line survives, in their language.
- The language is the reader's, asked once and remembered. Any language: the
  guide is English and translated on the way out, so none is built in.

## Procedure
1. Read the remembered language: `primeskills-help --which-lang`
   → **verify:** it printed a language, or `unset`
2. If `unset`, ask which language to read in — any language, English if they
   have no preference → **verify:** you have an answer and did not guess
3. Remember it: `primeskills-help --set-lang <language>` → **verify:**
   `--which-lang` returns it
4. Print it: `primeskills-help` → **verify:** the output ends with the line
   counting skills and sequences
5. The guide prints in English. If that is not the reader's language, translate
   the whole of it as you hand it over → **verify:** headings and prose are
   translated; command names, paths, flags and skill names are not; nothing was
   improved, shortened or reordered on the way
6. Give it over → **verify:** you added no summary, no ranking, no advice

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
