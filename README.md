# primeskills

Набор скиллов для агентов разработки: тот же цикл, что у gstack, без раздувания
контекста и без телеметрии. Вес печатает `python3 bin/primeskills-status`, и
цифры там разные по смыслу: постоянно в контексте лежат только описания и
указатель на `core/` (411 слов), сам `core/` читается один раз за сессию при
первом вызове, тело скилла — при его вызове. **Потолок одного вызова — 3 000 слов** (правило C3), сейчас
используется 2 325–2 687. Против ≈ 92 000 слов у одного прохода gstack —
замер в `bench/RESULT.md`.

**Числа и статус поддержки не набираются руками:** `python3 bin/primeskills-status`
читает их из репозитория. Документы уже расходились между собой однажды, и это
попало в ревью.

Агенты: Claude Code, Codex, Kimi Code, OpenCode — с разной глубиной ролевой
изоляции, см. `bin/primeskills-status` и `docs/ADAPTERS.md`.

## Документы

| файл | о чём |
|---|---|
| [TODOS.md](TODOS.md) | очередь `PS-NNN`: что открыто, с якорями |
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
python3 bin/primeskills-doctor            # подключено ли всё у каждого агента
python3 bin/primeskills-status            # состав и статус, из репозитория
python3 bin/primeskills-lint              # формат: F1-F11, C1-C2
python3 bin/primeskills-run show          # запись прогона текущей ветки
python3 bin/primeskills-adherence --all   # соблюдались ли инварианты вызванных скиллов
python3 bin/primeskills-route skills tests/routing.txt
python3 bin/primeskills-install --apply   # разложить по агентам
python3 tests/run.py                      # весь прогон
```

## Запись прогона

`.primeskills/run/<branch>.md` в репозитории, с которым идёт работа. Туда
`verify` кладёт результат прогона, `vet` и `probe` — вердикты, `cycle` держит
счётчик G9; `merge` читает это перед слиянием. Заведено после двух внешних
разборов: счётчик и «evidence» жили в памяти агента и умирали вместе с сессией.
Программа, а не ещё один абзац инструкций — помнить абзацы и было тем, что
не работало.

## Статус

Набор написан и установлен. Ревью Codex разобрано (`review/codex-2026-08-16.md`):
пять P1 и все P2, кроме сознательно отклонённого переименования `land`.
Открыто: обкатка диалоговой половины — `brief`, `ceo`, `eng`, `beauty`,
`teams`, `autoplan` состоят из вопросов пользователю и в одиночку
не проверяются.
