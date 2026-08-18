# Attributions

primeskills is MIT (see `LICENSE`), and the notices of the work it borrows
from are in `NOTICE`, which travels with the distribution because `vendor/`
does not. It was synthesised from six sources, and
this file records what each one contributed, under which licence, so that a
reader can check the claim rather than take it on trust. What was taken from
where, in detail, is `docs/SKILL-SOURCES.md`; what is our own is marked there
too.

## Sources carrying licences

| source | licence | copyright | what is here |
|---|---|---|---|
| [superpowers](https://github.com/obra/superpowers) | MIT | Jesse Vincent, 2025 | skeletons: the iron law of root cause, the red-green-refactor cycle, the plan file structure, the right to argue with a review comment, the rationalisation tables condensed into `core/RATIONALIZATIONS.md` |
| [agent-skills](https://github.com/addyosmani/agent-skills) | MIT | Addy Osmani, 2025 | checklists and axes: `skills/ui` is built on `frontend-ui-engineering`; the five review axes in `vet`; the security checklist in `vet/ref/security.md`; the rollback plan in `deploy`; the layer breakdown in `measure` |
| [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) | «MIT» заявлен в README, файла лицензии нет | не установлен: репозиторий не Карпаты, а стороннее собрание его правил | §2 Simplicity First and §3 Surgical Changes are in `core/PRINCIPLES.md` close to verbatim; §1 and §4 condensed |
| [gstack](https://github.com/gstack-ai/gstack) | MIT | Garry Tan, 2026 | the destructive-command pattern list ported into `skills/fence/bin/check-commands.py`; the `PreToolUse` hook mechanics; the lens questions behind `ceo`, `eng`, `beauty`; the voice rules and the jargon list in `baby/ref/jargon.md`; the checkpoint file structure behind `handoff`. Telemetry was removed from everything ported |
| [stop-slop](https://github.com/hardikpandya/stop-slop) | MIT | Hardik Pandya | the pattern list behind `skills/prose`: binary contrasts, triples, punchy paragraph endings, throat-clearing openers |
| [loopx](https://github.com/loopx-ai/loopx) | Apache-2.0 | LoopX contributors | the idea of classifying a failure by layer, and repairing at the lowest durable one, in `skills/debug`. Concept only: an eight-word shingle comparison between their `self-repair` document and our `debug` plus `GUARDRAILS` finds no overlap, so no expression of theirs is reproduced here |

## Sources without a licence file

- **[prompt-eng-interactive-tutorial](https://github.com/anthropics/prompt-eng-interactive-tutorial)** (Anthropic) — techniques applied while writing. No text ships.
- **Published system prompts of claude.ai** (Anthropic) — reading them in 2026-08-17 raised four questions we had not asked: how much formatting an answer earns, how a refusal should read, whether "I can't" was ever checked, and whether edits are judged one at a time. The rules that answer them were rewritten from our own practice on 2026-08-18 and now stand on our own evidence and our own numbering: the formatting test counts bullet lines, the refusal rule explains itself by how a bulleted refusal gets argued clause by clause, the capability check is P6 leaning on G15, and the cumulative radius is part of G6, where the definition of "the change" already lived. Nothing of theirs is reproduced; the debt is that they made us look. See PS-017.
- **[i-have-adhd](https://github.com/ayghri/i-have-adhd)** (MIT, stated in the skill) — the pre-send deletion check in `core/OUTPUT.md`. See PS-019.
- **[deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)** (MIT) — three ideas: checking a new queue entry against existing ones, rejection as a first-class outcome with its reason in the line, and the test for session-vantage prose. See PS-018.

## What is not from anyone

Ten of the twenty-five rules in `core/` have no prototype in any source:
G3, G4, G8, G9, G11, G12, G13, G14, G16, G17. The tools in `bin/`, the linter
rules, the run record and the adherence reader are ours. The accounting is in
`docs/SKILL-SOURCES.md`, including the cases where an earlier version of that
count was wrong.

## Clone directory

`vendor/` holds clones of the sources for comparison. It is in `.gitignore` and
is not distributed; nothing in it is ours.
