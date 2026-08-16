#!/usr/bin/env python3
"""Model-based routing check: does a real model pick the right skill?

The lexical linter cannot answer this. On the held-out queries in
tests/routing-heldout.txt it fails 26 of 28, because those queries are written
the way a person actually asks rather than in the vocabulary of the
descriptions, and half of them are in Russian while the descriptions are in
English. That is the tool working as designed and being the wrong tool.

This script builds the prompt; the answer comes from an independent model, so
it is not run inside the test suite. Usage:

    python3 tests/routing_model.py > /tmp/prompt.txt
    codex exec "$(cat /tmp/prompt.txt)" > /tmp/answer.txt
    python3 tests/routing_model.py --check /tmp/answer.txt

Results (codex, gpt-5.6-sol): 28 of 28 on 2026-08-16 with 19 skills;
31 of 31 after merge, deploy and release were added.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "tests" / "routing-heldout.txt"


def expectations():
    out = {}
    for line in TABLE.read_text(encoding="utf-8").splitlines():
        if "->" in line and not line.strip().startswith("#"):
            q, s = line.split("->")
            out[q.strip()] = s.strip()
    return out


def prompt():
    rows = []
    for p in sorted(ROOT.glob("skills/*/SKILL.md")):
        t = p.read_text(encoding="utf-8")
        rows.append(f"{re.search(r'^name: (.+)$', t, re.M).group(1)}: "
                    f"{re.search(r'^description: (.+)$', t, re.M).group(1)}")
    queries = list(expectations())
    return (
        "You are the skill router of a coding agent. Below are the skills you can\n"
        "call, each with the description the agent sees. Then a list of user\n"
        "messages.\n\n"
        "For each message output exactly one line: the message, then \" -> \", then\n"
        "the single skill name you would invoke. Nothing else. If none fits, write\n"
        "\"none\". Messages may be in Russian; the descriptions are in English.\n\n"
        f"## Skills\n\n{chr(10).join(rows)}\n\n## Messages\n\n{chr(10).join(queries)}\n"
    )


def check(answer_path):
    want = expectations()
    got = {}
    for line in Path(answer_path).read_text(encoding="utf-8").splitlines():
        if "->" in line:
            q, s = line.rsplit("->", 1)
            got[q.strip().lstrip("- ")] = s.strip().strip("`")
    wrong = [(q, e, got.get(q)) for q, e in want.items() if got.get(q) != e]
    for q, e, g in wrong:
        print(f"{q!r}: expected {e}, got {g}")
    print(f"{len(want) - len(wrong)} of {len(want)} correct")
    return 1 if wrong else 0


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--check":
        sys.exit(check(sys.argv[2]))
    print(prompt())
