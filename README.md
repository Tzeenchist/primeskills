# primeskills

Набор скиллов для агентов разработки: тот же цикл, что у gstack, без раздувания
контекста и без телеметрии. Пятнадцать скиллов, четыре потока, общая база
`core/`. Бюджет всего набора ≈ 9 400 слов против ≈ 92 000 у одного прохода gstack.

Агенты первого этапа: Claude Code, Codex, Kimi Code, OpenCode.

## Документы

| файл | о чём |
|---|---|
| [PLAN.md](PLAN.md) | замысел, принципы, ограничители, состав, порядок работ |
| [docs/BUILD-PLAN.md](docs/BUILD-PLAN.md) | имена, контракты, спецификация каждого скилла, этапы приёмки |
| [docs/SKILL-FORMAT.md](docs/SKILL-FORMAT.md) | формат `SKILL.md`, шесть разделов, правила линтера |
| [docs/SKILL-SOURCES.md](docs/SKILL-SOURCES.md) | построчно: какой скилл из каких источников |
| [docs/SYNTHESIS-MAP.md](docs/SYNTHESIS-MAP.md) | одиннадцать кластеров: кто где решает ту же задачу |
| [docs/GSTACK-ETHOS.md](docs/GSTACK-ETHOS.md) | философия gstack: девять пунктов берём, четыре отвергаем |
| [docs/DONOR-PHILOSOPHY.md](docs/DONOR-PHILOSOPHY.md) | философия остальных доноров |

## Источники

Клоны в `vendor/` (в `.gitignore`): gstack, superpowers, andrej-karpathy-skills,
agent-skills, prompt-eng-interactive-tutorial, loopx. Там же
`vendor/gstack-installed/` — хуки `careful`/`freeze` и список жаргона,
сохранённые до удаления gstack.

## Статус

План зафиксирован. Следующий шаг — этап A: линтер формата и маршрутизации.
