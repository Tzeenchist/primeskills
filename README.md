# primeskills

Набор скиллов для агентов разработки: тот же цикл, что у gstack, без раздувания
контекста и без телеметрии. Девятнадцать скиллов (из них четыре потока) плюс
общая база `core/`. Против ≈ 92 000 слов у одного прохода gstack — замер
в `bench/RESULT.md`.

**Числа и статус поддержки не набираются руками:** `python3 bin/primeskills-status`
читает их из репозитория. Документы уже расходились между собой однажды, и это
попало в ревью.

Агенты: Claude Code, Codex, Kimi Code, OpenCode — с разной глубиной ролевой
изоляции, см. `bin/primeskills-status` и `docs/ADAPTERS.md`.

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

## Инструменты

```
python3 bin/primeskills-status            # состав и статус, из репозитория
python3 bin/primeskills-lint              # формат: F1-F11, C1-C2
python3 bin/primeskills-route skills tests/routing.txt
python3 bin/primeskills-install --apply   # разложить по агентам
python3 tests/run.py                      # весь прогон
```

## Статус

Набор написан и установлен. Ревью Codex разобрано (`review/codex-2026-08-16.md`):
пять P1 и все P2, кроме сознательно отклонённого переименования `land`.
Открыто: профиль read-only в OpenCode и Kimi, честная проверка маршрутизации
на незнакомых формулировках, канонические идентификаторы инвариантов для F8.
