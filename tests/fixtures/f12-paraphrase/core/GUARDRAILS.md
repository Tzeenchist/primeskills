# Guardrails

- **G4 Exit-code proof.** Nothing passes until a command says so: exit code 0
  and the tool's own success signal read from its output. Absence of a crash is
  never a pass.
