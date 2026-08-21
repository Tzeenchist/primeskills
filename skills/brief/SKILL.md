---
name: brief
description: Use before creating anything, to find out what is actually wanted and what to cut
budget: 550
role: read-only
allowed-tools: [Read, Grep, Glob, Bash, WebFetch, WebSearch, AskUserQuestion]
---

# Brief

## Trigger
Any request to build, add, or change behaviour, before design or code. Skip
only when the change is mechanical and the user has already said exactly what
they want.

## Invariants
- No code, no files, no design decisions until the user has approved the intent.
  "Too simple to need approval" is the sentence that precedes most wasted work.
- One question at a time. A list of six questions gets three answers.
- Every question earns its place: ask only what changes what gets built.
- Hand back in pieces short enough to read. A wall of text is not agreement.
- You are extracting what the user wants, not what they think they should want.

## Procedure
1. Restate the request in one sentence and say what you take it to mean
   → **verify:** the user corrects it or confirms it before you go on
2. Ask what the user is trying to achieve behind the request → **verify:** you
   can state the outcome without naming the requested feature
3. Ask who hits this and how often → **verify:** the answer is a real situation,
   not a persona
4. State your hypothesis for the answer before asking the next question
   → **verify:** it is specific enough to be visibly wrong
5. Ask what happens today without it, and what the workaround costs
   → **verify:** the cost is concrete
6. Propose what to cut: name the smallest version a real user would accept;
   the choice goes by the means named in OUTPUT §Asking
   → **verify:** the user accepts, shrinks, or rejects the cut explicitly
7. Ask how you will both know it worked → **verify:** the criterion is
   observable after shipping
8. Write the brief and hand it over for approval → **verify:** the user
   approves it before any planning starts

## Stop conditions
- Two readings of the request would lead to different work: stop and ask which.
  Do not pick the likelier one silently (PRINCIPLES 1).
- The user asks you to start building mid-conversation: that is their call.
  Say what is still unknown, then proceed.
- You have asked five questions and the picture is not clearer: the request may
  be exploratory. Say so and offer to prototype instead of plan.

## Output
The brief: the goal in one sentence, who it is for, what is explicitly cut,
success criteria, and open questions with the user's answers.

## References
`plan` turns an approved brief into ordered tasks.
