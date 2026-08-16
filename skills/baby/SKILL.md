---
name: baby
description: Use to explain a term or the previous answer in plain language, without assumed expertise
budget: 400
role: read-only
allowed-tools: [Read, Grep, Glob, Bash, WebFetch, WebSearch, AskUserQuestion]
refs:
  - path: ref/jargon.md
    when: the passage being explained contains a term of art
---

# Baby

## Trigger
"What does that mean", "explain that again", "what is X" — or any sign the last
answer assumed knowledge the reader does not have.

## Invariants
- Simplify the language, never the claim. An explanation that became false is
  worse than the jargon it replaced.
- Where something genuinely cannot be made simple without breaking, say that,
  and say what makes it hard.
- An analogy earns its place by letting the reader predict the next fact
  correctly. One that only decorates gets cut.
- Explain what blocked understanding, not everything. A full restatement is a
  second answer of the same length.
- This adds no new claims. If the previous answer was wrong, say so and stop.

## Procedure
1. Find the specific places that blocked understanding: terms, leaps, implied
   background → **verify:** you can point at the words, not "the whole thing"
2. Check each against `ref/jargon.md` → **verify:** every term of art in the
   passage is either explained or deliberately left
3. Explain each in one or two sentences, in the words of the thing itself
   → **verify:** the explanation would still be true to someone who knows the
   subject
4. Add an analogy only where it predicts something → **verify:** you can state
   what the reader can now correctly guess
5. Close with what this changes for the decision in front of the user
   → **verify:** the line names an actual choice, not a summary

## Stop conditions
- The previous answer was wrong, not unclear: say that instead of explaining it.
- The user wants depth, not simplicity: this is the wrong skill, answer directly.

## Output
The unclear parts explained in order, then one line on what it changes for the
decision at hand.

## References
`ref/jargon.md` holds the terms worth glossing on first use.
