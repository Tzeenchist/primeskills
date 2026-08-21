# Attributions

primeskills is MIT (see `LICENSE`), and the notices of the work it borrows
from are in `NOTICE`, which travels with the distribution because `vendor/`
does not. It was synthesised from seven sources, and
this file records what each one contributed, under which licence, so that a
reader can check the claim rather than take it on trust. What was taken from
where, in detail, is `docs/SKILL-SOURCES.md`; what is our own is marked there
too.

## Sources carrying licences

| source | licence | copyright | what is here |
|---|---|---|---|
| [superpowers](https://github.com/obra/superpowers) | MIT | Jesse Vincent, 2025 | skeletons: the iron law of root cause, the red-green-refactor cycle, the plan file structure, the right to argue with a review comment, the rationalisation tables condensed into `core/RATIONALIZATIONS.md` |
| [agent-skills](https://github.com/addyosmani/agent-skills) | MIT | Addy Osmani, 2025 | checklists and axes: `skills/ui` is built on `frontend-ui-engineering`; the five review axes in `vet`; the security checklist in `vet/ref/security.md`; the rollback plan in `deploy`; the layer breakdown in `measure` |
| [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) | MIT, заявлен строкой в README; файла лицензии в репозитории нет | владелец репозитория multica-ai; собрание составлено из публичных высказываний Андрея Карпаты | ideas only, as of 2026-08-19: four sections of theirs (§1–§4) shaped P1, P2, P3 and P7, and the wording of all four was rewritten that day. `bin/primeskills-shingle` reports the longest run shared with them as four words, and that run is a heading |
| [gstack](https://github.com/gstack-ai/gstack) | MIT | Garry Tan, 2026 | the destructive-command pattern list ported into `skills/fence/bin/check-commands.py`; the `PreToolUse` hook mechanics; the lens questions behind `ceo`, `eng`, `beauty`; the voice rules and the jargon list in `baby/ref/jargon.md`; the checkpoint file structure behind `handoff`. Telemetry was removed from everything ported |
| [stop-slop](https://github.com/hardikpandya/stop-slop) | MIT | Hardik Pandya | the pattern list behind `skills/prose`: binary contrasts, triples, punchy paragraph endings, throat-clearing openers |
| [ai-copywriter](https://github.com/mikiarlo3/ai-copywriter) | MIT | Siqi Chen 2025 (the humanizer), Mickey Haslavsky 2026 (the additions) | two lists in `skills/prose/ref/keep.md`: what must not be read as a tell, and what to leave alone. Their copywriting half is not here. Their "cut every em dash" rule is refused on purpose — it deletes correct Russian punctuation. The patterns are credited by them upstream to [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) (CC BY-SA 4.0) |
| [loopx](https://github.com/loopx-ai/loopx) | Apache-2.0 | LoopX contributors | the idea of classifying a failure by layer, and repairing at the lowest durable one, in `skills/debug`. Concept only: an eight-word shingle comparison between their `self-repair` document and our `debug` plus `GUARDRAILS` finds no overlap, so no expression of theirs is reproduced here |
| [llm-as-a-verifier](https://github.com/llm-as-a-verifier/llm-as-a-verifier) | MIT | llm-as-a-verifier contributors, 2026 | concepts only, 2026-08-21: the rule that an edit after the last successful check voids the proof (`verify` invariant), and the rubric discipline that a criterion names what it ignores so axes do not leak (`vet`, `eng`). Their runtime framework — Best-of-N selection, logprob scoring — is not used |
| [effective-html](https://github.com/plannotator/effective-html) | MIT | plannotator, 2026 | concepts only, 2026-08-21: motion as explanation or feedback; visible elements carry real content (placeholder copy and decorative statistics are unfinished work) in `ui`; the authority order (user → project design system → subject → taste) and the subject-swap originality test in `beauty`. The HTML-artifact generation itself and its router/specialist packaging are not used |

**Про `andrej-karpathy-skills` отдельно.** Из семи доноров это единственный без
файла лицензии: грант — строка «MIT» в README репозитория multica-ai, и
2026-08-19 он там всё ещё стоит, а GitHub по-прежнему не показывает лицензии
(`gh api` отдаёт `license: null`, `contents/LICENSE` — 404). Строка в README
есть грант владельца репозитория, но как доказательство она слабее файла, и
проверить цепочку прав на сборник публичных высказываний Карпаты нечем. Поэтому
2026-08-19 набор перестал на неё опираться: P2 — единственное место, где текст
был копией выражения (23 слова подряд, 55% восьмисловных окон), — переписан
своими словами, вместе с более короткими совпадениями в P1, P3 и P7. Идеи
остаются заимствованными и названы здесь; выражение — нет. Проверяется командой
`bin/primeskills-shingle` (нужен `vendor/`).

Сообщение владельца проекта о том, что сам Карпаты против сборника не возражал,
остаётся записанным как контекст: это не лицензия и не подтверждение прав. На
подмену контекста основанием указал разбор Codex 2026-08-18 — раньше эта фраза
стояла в колонке правообладателя.

**Три числа здесь раньше были неверны**, и все три исправлены измерением
2026-08-19. P3 значился как «совпадений ноль, текст наш» — ноль был у
восьмисловного окна, а заголовок с первой фразой совпадал дословно (7 слов).
P1 и P7 в учёте не значились вовсе, хотя несли дословные куски в 9 и 10 слов.
`docs/SKILL-SOURCES.md` называл G1 дословным портом §3 — у G1 нет с §3 ни одного
общего четырёхсловного окна, текст наш целиком.

## Sources without a licence file

- **[prompt-eng-interactive-tutorial](https://github.com/anthropics/prompt-eng-interactive-tutorial)** (Anthropic) — techniques applied while writing. No text ships.
- **Published system prompts of claude.ai** (Anthropic) — reading them in 2026-08-17 raised four questions we had not asked: how much formatting an answer earns, how a refusal should read, whether "I can't" was ever checked, and whether edits are judged one at a time. The rules that answer them were rewritten from our own practice on 2026-08-18 and now stand on our own evidence and our own numbering: the formatting test counts bullet lines, the refusal rule explains itself by how a bulleted refusal gets argued clause by clause, the capability check is P6 leaning on G5, and the cumulative radius is part of G17, where the definition of "the change" already lived. Nothing of theirs is reproduced; the debt is that they made us look. See PS-017.
- **[i-have-adhd](https://github.com/ayghri/i-have-adhd)** (MIT, stated in the skill) — the pre-send deletion check in `core/OUTPUT.md`. See PS-019.
- **[deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)** (MIT) — three ideas: checking a new queue entry against existing ones, rejection as a first-class outcome with its reason in the line, and the test for session-vantage prose. See PS-018.

## What is not from anyone

Ten of the twenty-five rules in `core/` have no prototype in any source:
G3, G4, G7, G12, G14, G15, G13, G11, G6, G8. The tools in `bin/`, the linter
rules, the run record and the adherence reader are ours. The accounting is in
`docs/SKILL-SOURCES.md`, including the cases where an earlier version of that
count was wrong.

## Clone directory

`vendor/` holds clones of the sources for comparison. It is in `.gitignore` and
is not distributed; nothing in it is ours.
