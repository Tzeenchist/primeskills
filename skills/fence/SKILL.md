---
name: fence
description: Use to arm destructive-command warnings and restrict edits to a directory
budget: 350
role: write
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 $HOME/.claude/skills/fence/bin/check-commands.py"
          statusMessage: "fence: checking the command"
    - matcher: "Edit|Write|NotebookEdit"
      hooks:
        - type: command
          command: "python3 $HOME/.claude/skills/fence/bin/check-boundary.py"
          statusMessage: "fence: checking the boundary"
---

# Fence

## Trigger
Arm before touching production, shared systems, an unfamiliar repo, or any
unattended session. Also on request: "be careful", "lock edits here".

## Invariants
- This is a warning layer, not a boundary. The command list is a list; a shell
  cannot be closed with a denylist. It never silently allows what it could not
  parse, and that is the only guarantee it makes.
- The boundary hook sees `Edit`, `Write`, `NotebookEdit` — not the shell:
  `sed -i`, `tee`, `cp` and redirection walk past it. It is a reminder you
  cannot forget, not a wall.
- Pattern matching is necessary and never sufficient: destruction usually
  arrives through a harmless command with a misconfigured target (G17).

## Procedure
1. On Claude Code the hooks are declared in this skill's frontmatter and arm
   themselves on invocation → **verify:** `primeskills-doctor` reports the
   guards live, and a known-bad command returns `ask`
2. To scope edits, put one absolute path per line in `.primeskills/boundary`
   → **verify:** a path outside it returns `deny`
3. Report which guards are live → **verify:** the user sees the boundary paths

## Stop conditions
- Hooks unsupported by the host: say so plainly. The rules still stand, but
  nothing enforces them. Do not imply otherwise.
- Asked to widen the boundary mid-task: that is the user's call, not yours.

## Output
One line: guards armed, boundary paths, host support.

## References
`GUARDRAILS.md` G7, G10, G14, G17 hold the rules these hooks enforce.
