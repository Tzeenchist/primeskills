---
name: brief
description: Use before creating to find out what users actually want when unresolved product choices could change what gets built
budget: 550
role: read-only
allowed-tools: [Read, Grep, Glob, Bash, WebFetch, WebSearch, AskUserQuestion]
---

# Brief

## Trigger
Use when unresolved product choices would change what gets built. Skip when
the request and acceptance criteria already settle the intent, including small
local changes and an approved plan.

## Invariants
- No code, no files, no design decisions until the user has approved the intent.
  "Too simple to need approval" is the sentence that precedes most wasted work.
- One question at a time. A list of six questions gets three answers.
- Every question earns its place: ask only what changes what gets built.
- Hand back in pieces short enough to read. A wall of text is not agreement.
- You are extracting what the user wants, not what they think they should want.

## Procedure
1. Read the request, relevant specs, and connected code before asking. Restate
   the intended outcome and any material conflict you found → **verify:** you
   use facts the sources already establish and skip the interview if nothing
   material remains open
2. If the goal is still unknown and would change the result, ask an open
   question about it before proposing approaches → **verify:** you can state
   the outcome without naming the requested feature
3. For an unresolved choice, show a concrete case. If a business term has
   multiple meanings, compare how the current code handles that case with
   the plausible meanings. Explain what each option changes, recommend one
   when the trade-offs are clear, and ask one question via OUTPUT §Asking
   → **verify:** the answer settles a specific difference in behaviour
4. Use the evidence already available for audience, frequency, workaround
   cost, and success criteria. State reversible defaults for minor gaps.
   Ask about a missing fact only if its answer would change the result
   → **verify:** no settled question is repeated and every default is visible
5. Propose what to cut: name the smallest version a real user would accept.
   Put unresolved scope choices through OUTPUT §Asking
   → **verify:** the user accepts, shrinks, or rejects the cut explicitly
6. Hand over the brief for approval with an observable success criterion
   → **verify:** the user approves it before any planning starts

## Stop conditions
- Two readings of the request would lead to different work: stop and ask which.
  Do not pick the likelier one silently (P1).
- The user asks you to start building mid-conversation: that is their call.
  Say what is still unknown, then proceed.
- You have asked five questions and the picture is not clearer: the request may
  be exploratory. Say so and offer to prototype instead of plan.

## Output
The brief: the goal in one sentence, who it is for, what is explicitly cut,
success criteria, and open questions with the user's answers.

## References
`plan` turns an approved brief into ordered tasks.
