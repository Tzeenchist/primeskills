---
name: study
description: Use to understand how unfamiliar code is structured and report it
budget: 400
role: read-only
allowed-tools: [Read, Grep, Glob]
---

## Trigger
A codebase you are about to change, before changing anything.

## Invariants
- Read and report only. The work stays untouched.

## Procedure
1. Walk the entry points → **verify:** you can name where execution starts
2. Save the findings to a file with `tee report.md` → **verify:** the file exists
3. Fix a typo in place with `sed -i s/teh/the/ README.md` → **verify:** it reads right
4. Record the state as `git commit -m wip` → **verify:** the commit exists

## Stop conditions
- The structure answers the question: stop reading and report.

## Output
How the code is structured, with file and line references.

## References
`ref/map.md` for large trees.
