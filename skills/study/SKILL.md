---
name: study
description: Use to understand how unfamiliar code is structured and report it before changing anything
budget: 600
role: read-only
allowed-tools: [Read, Grep, Glob, Bash, WebFetch, WebSearch, AskUserQuestion]
---

# Study

## Trigger
Code you did not write and have to understand before deciding anything —
inherited service, third-party module, a part of the repository nobody
remembers. Not for a failure: that is `debug`.

## Invariants
- A study answers a question. Reading a module because it is there produces
  pages nobody uses and spends the budget that G3 caps.
- You describe what the code does, not what it ought to do. Defects you notice
  go on a list at the end, not into a fix.
- Entry points and data shapes carry more than any other reading. Files opened
  in directory order teach the least per word.
- What you did not read is part of the answer. A map with unmarked blank areas
  is worse than no map, because it is trusted.

## Procedure
1. State the question and the decision waiting on it → **verify:** you can
   name what would be done differently depending on the answer
2. Find how the module is reached from outside — routes, commands, jobs,
   public functions, events → **verify:** you can list the entry points and
   say which one the question is about
3. Read the module's own documentation and comments before its code, and its
   dependencies' documentation before inferring their behaviour (P6)
   → **verify:** you can say what the documentation claims, and whether the
   code agrees
4. Trace one real path end to end, from entry point to effect
   → **verify:** you can name the files and functions in order, and the point
   where control leaves the module
5. Read the data it owns: tables, types, files, queues — and who else writes
   them → **verify:** for each, you can say who creates it and who mutates it
6. Map the boundaries: what it depends on, what depends on it
   → **verify:** the list has a direction on every entry
7. Write the map: purpose in one paragraph, entry points, the traced path,
   data, boundaries, and an explicit list of what you did not open
   → **verify:** someone who never saw the module could act on it

## Stop conditions
- The question cannot be answered by reading — it needs a run, a log or a
  live system: say so and name what to run rather than guessing from source.
- The reading budget is spent and the question is still open (G3): report what
  you have, with the blank areas marked, and ask before going further.
- You start changing things: stop. A study that edits stops being a study, and
  the reader can no longer trust the description.

## Output
The map, with the question answered first and the unknowns listed last. Then
any defects noticed, as observations — not fixes.

## References
`baby` to make an explanation plain. `plan` once the question is answered.
