---
name: prose
description: Use before text leaves the building, to strip machine tells without flattening the writing
budget: 600
role: write
refs:
  - path: ref/tells.md
    when: running the mechanical pass, or the text is in Russian
---

# Prose

## Trigger
Text a stranger will read: a cover letter, a README, a landing page, a pull
request description, anything published. Not for chat, not for commit messages,
not for code comments.

## Invariants
- This strips tells, never authorship. Where a text carries a declaration of
  who wrote it — an application, coursework, a review, anything a reader will
  judge as a person's own — say so and stop: making machine-written text read
  as human is exactly what such a declaration exists to prevent. Editing your
  own writing, a README, release notes or a report is the case this is for.
- The frequencies in `ref/tells.md` are the author's rules of thumb, not
  measured human norms. Use them to notice a pattern, never to certify that a
  text passes as human.
- This is a filter, not a rewrite. Remove the tic and leave the argument, the
  voice and the rhythm exactly as they were. A pass that also improves the
  writing has destroyed the evidence of what was wrong with it.
- **Frequency is the tell, not presence.** One "not X, but Y" is a rhetorical
  device; six in a page is machinery. Count before you cut, and cut down to a
  human rate rather than to zero.
- Tells are language-specific. A rule imported from English prose applied to
  Russian text removes correct writing — see `ref/tells.md`, and the em dash
  above all.
- What you cannot check by reading, do not claim. The mechanical pass finds
  patterns; whether the text sounds like a person is a judgement, and you say
  which of the two produced each edit.

## Procedure
1. Read the whole text once before touching anything → **verify:** you can
   state its argument in one sentence, and you know who reads it
2. Identify the language and load the matching column of `ref/tells.md`
   → **verify:** you say which language rules you are applying
3. Mechanical pass: grep each pattern, count hits, record the rate per
   thousand words, the unit `ref/tells.md` uses → **verify:** you have counts, not impressions
4. Cut only what exceeds a human rate, keeping the strongest instance of each
   pattern → **verify:** for every cut you can name the pattern and the count
   that justified it
5. Structural pass by eye: paragraphs of equal length, every section ending on
   a punchy line, triples everywhere, headings that announce instead of naming
   → **verify:** you quote the passage, not the category
6. Read the result aloud against the original → **verify:** the argument is
   unchanged, and you can point to nothing you improved beyond the brief
7. Report: what was cut, at what count, and what you deliberately left
   → **verify:** the list of what you left is not empty, or you say why

## Stop conditions
- The text is not yours and the author has not asked for edits: report the
  counts and hand them over.
- Cutting a pattern would change the meaning: stop, report, let the author
  choose. A tell that carries an argument is no longer only a tell.
- The whole draft is machine-shaped, not a few patterns: say so plainly. This
  skill files off serial numbers; it does not write a new draft.

## Output
Counts per pattern before and after, the edited text, and an explicit list of
patterns you left in place with the reason.

## References
`ref/tells.md` — the patterns, per language, with the counts that matter.
