#!/usr/bin/env python3
"""Static measurement for the bench task. Three comparisons, narrowest first."""
from pathlib import Path

GSTACK = Path.home() / ".claude" / "skills" / "gstack"
PRIME = Path(__file__).resolve().parent.parent
ALWAYS = ("PRINCIPLES.md", "GUARDRAILS.md", "OUTPUT.md")


def words(paths):
    return sum(len(p.read_text(encoding="utf-8", errors="ignore").split()) for p in paths)


def g(name, full=False):
    d = GSTACK / name
    return words(sorted(d.rglob("*.md")) if full else [d / "SKILL.md"])


def p(name):
    return words([PRIME / "skills" / name / "SKILL.md"])


core = words([PRIME / "core" / f for f in ALWAYS])

print("1. Like for like -- the one stage both sets have today (debugging)")
print(f"   gstack /investigate      {g('investigate'):>7}   (with its own refs: {g('investigate', True)})")
print(f"   primeskills debug + core {core + p('debug'):>7}   (debug alone: {p('debug')})")
print(f"   ratio {g('investigate') / (core + p('debug')):.1f}x on a one-stage session,"
      f" {g('investigate') / p('debug'):.1f}x once core is paid for\n")

print("2. Measured, everything built so far")
built = {n: p(n) for n in ("fence", "verify", "build", "debug", "handoff", "cycle")}
print(f"   primeskills 6 skills + core = {core + sum(built.values())}")
print(f"   {'  '.join(f'{k}:{v}' for k, v in built.items())}\n")

print("3. Projected full pipeline for this task (bug fix + small feature)")
GSTACK_PIPE = ["plan-eng-review", "investigate", "qa", "review", "ship"]
gt = sum(g(n) for n in GSTACK_PIPE)
gtf = sum(g(n, True) for n in GSTACK_PIPE)
# unbuilt skills counted at their linter-enforced budget: an upper bound
BUDGETS = {"plan": 600, "eng": 300, "vet": 800, "probe": 800, "land": 800}
pt = core + p("build") + p("debug") + p("verify") + p("cycle") + sum(BUDGETS.values())
print(f"   gstack   {gt} words (SKILL.md only) / {gtf} with references")
print(f"   prime    {pt} words, of which {sum(BUDGETS.values())} are budgets, not code yet")
print(f"   ratio    {gt / pt:.1f}x .. {gtf / pt:.1f}x")
print("\nOurs are ceilings the linter enforces; gstack's are what the files"
      "\nactually weigh -- and a session loads neither. Measured live on"
      "\n2026-08-20: 5.4x..8.3x, about half the projection, because the"
      "\nprojection overstated both sides. See bench/RUN-7-LOG.md.")
