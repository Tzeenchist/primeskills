```
      █▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀█                                    
      █                                        ▄▄▄▄▄▄▄▄▄▄█▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
      █                                        █░░░░░░░░░█                                   █
      █  ██████  ██████  ██  ██▄  ▄██  ██████  █░▄█████░░█  ██  ██  ██  ██     ██    ▄█████  █
      █      ██      ██  ██  ███▄▄███          █░███░░░░░█  ██▄██▀  ██  ██     ██    ███     █
      █  ██████  ██████  ██  ██▀██▀██  ██████  █░▀█████▄░█  ████    ██  ██     ██    ▀█████▄ █
      █  ██      ██▀██   ██  ██    ██  ██      █░░░░░███░█  ██▀██▄  ██  ██     ██        ███ █
      █  ██      ██  ██  ██  ██    ██  ██████  █░░█████▀░█  ██  ██  ██  █████  █████  █████▀ █
      █                                        █░░░░░░░░░█                                   █
      ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀█▀▀▀▀▀▀▀▀▀▀                                   █
                                               █▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█
```

# primeskills

*English · [Русский](README.ru.md)*

Instructions for a coding agent — the kind that writes code when you ask:
Claude Code, Codex, Kimi Code, OpenCode. Each one covers a single kind of work:
how to chase a bug to its cause, how to check a change, how to hand work on.

Sets like this usually sit in the agent's head the whole time. This one barely
does. A skill's full text loads only when that skill is needed.

> I love gstack and have used it since it appeared, but by now it has grown so
> fat and so expensive that soon Garry Tan himself will not be able to afford
> it. Agentic development is thrift: of effort, of time, of money. That is the
> philosophy I built PRIMESKILLS on. Today this set holds the best and most
> dependable of what I use every day to build software products.
>
> — Ilya Priymak, author

```
always in context        466 words for all 29 skills
shared rules             2 805 words, once per session
one skill call           3 553 … 3 971 words
```

**The ceiling on one skill call is 4 600 words** (rule C3), and a check holds
it rather than a promise: the linter refuses a skill that pushes a call over the
ceiling. A sequence pays for the chain it calls and is deliberately outside that
ceiling — `primeskills-status` prints what each one costs, up to about 6 250. For comparison, one pass of the gstack set costs about 92 000 words —
measured in `bench/RESULT.md`.

## Discipline and evidence

**Order instead of memory.** The failing test comes before the code. "It
passed" means an exit code and a test count, not the absence of an error in the
output. Before a destructive command, say out loud what it will touch. Three
failed attempts on one problem: stop and ask.

**Evidence outlives the session.** A test run is recorded on disk together with
a fingerprint of the tree it ran against. Change a file after a green run and
the record goes stale, and the next step sees that. The agent cannot appeal to
a check that never happened, or to one that was about different code. Ignored
test inputs can join the fingerprint through `.primeskills/digest-include`, one
repository-root glob per line with `#` comments. Untracked files over 4 MB use
their size plus the first and last 64 KiB; symbolic links use their path and
target without reading through the link or leaving the repository.

**Authority by rungs.** Commit, push, pull request, merge, migrate, deploy,
roll back, delete, clear a failure counter — nine separate yeses. One does not
open the next,
permission for staging does not open production, and permission for one deploy
does not cover tomorrow's.

**Text it did not write is data, not orders.** Repository instructions, an
issue, a dependency's documentation, a page on the web: the agent checks them
instead of obeying a command found inside. And it does not run someone else's
code before it has read the diff.

**Nothing goes out on the set's account.** No telemetry, no calls home, no
dependencies to install. What a skill may reach for is a separate matter and is
declared in the open: the analytical ones are allowed `WebFetch` and
`WebSearch`, because reading documentation is their work.

## Agents

| agent | how it installs |
|---|---|
| Claude Code | skills + a pointer to the shared rules in `CLAUDE.md`, guards in `settings.json` |
| Codex | skills + a pointer in `~/.codex/AGENTS.md` |
| Kimi Code | `extra_skill_dirs` in the config + a pointer + the `prime-analyst` profile |
| OpenCode | skills + shared rules in `instructions` + the `prime-analyst` profile |

Analytical skills have their editing tools taken away, and the hosts honour
that. The shell is a separate channel that nobody intercepts, so role isolation
here is discipline rather than a wall — the set says so plainly instead of
implying otherwise.

## Requirements

Python 3.11 or newer, and git. Nothing else: no packages to install,
no network. The version floor is `tomllib`, which the installer uses to read
Kimi's configuration.

## Installation

```
git clone <repository> primeskills
cd primeskills
python3 bin/primeskills-install            # prints the plan, changes nothing
python3 bin/primeskills-install --apply    # installs into every agent it finds
python3 bin/primeskills-doctor             # checks that everything is connected
```

By default the installation is pinned to a commit: the agents read a separate
tree, and editing the working copy does not reach them until you install again.
While developing the set itself that is in the way:

```
python3 bin/primeskills-install --apply --live   # install from the working copy
python3 bin/primeskills-install --pin <commit>   # pin a different commit
python3 bin/primeskills-install --unpin          # go back to the working copy
```

The installer takes back only what it put there: other people's skills and your
own files inside its directories are left alone. To remove it:
`--uninstall --apply`.

**What it writes into Claude Code, spelled out.** Alongside the skills, the
installer adds `PreToolUse` hooks to `~/.claude/settings.json`. That means a
program from this repository runs before every `Bash`, `Edit` and `Write` call
the agent makes, and it can refuse the call — that is how `fence` blocks a
destructive command instead of asking you to remember one. It is also the
strongest thing this set does to your machine, so decide about it deliberately:
the hook lines name an absolute path, the pinned tree is read-only day to day,
and `--uninstall --apply` removes them. Nothing else installs hooks; the other
three agents have no such mechanism at all.

**With confirmations switched off, the guard stops asking.** In a session run
with `--dangerously-skip-permissions` — or any mode where you have said "do not
ask me" — a prompt is not protection: it is approved unread, and the reflex it
trains is the one that answers the question that mattered. So it decides
instead. A short irreversible list is refused: database contents, force-push,
cluster resources, a device overwrite, a delete outside the working directory.
Everything else runs, with a line in the run journal. A refusal lifts the way
permissions do — tell the agent what you allow, and it records your answer.

## Skills and chains

You can call a skill yourself — `/debug` — but usually you do not have to: the
agent picks by the description. Five skills call others in order and stop where
the decision is yours.

```
/autoplan   idea → brief → plan → review by three roles
/cycle      implement → verify → debug, until it is green
/close      verify → review the diff → exercise the app → pull request
/release    pull request → merge → deploy
/teams      review a plan: product, engineering, interface
```

The rest are called one at a time. All of them, because the small ones earn
their place too — `/baby` and `/prose` are among the most used here:

<!-- skills:begin -->
```
# understand the task, the code, the words
/brief        what is actually wanted, and what to cut
/study        how unfamiliar code is put together
/baby         a term, or the last answer, in plain language

# decide what to build
/plan         ordered tasks once the requirements are clear
/ceo          is this the right work at all
/money        how what this adds would be paid for
/eng          architecture, data flow, edge cases, test coverage
/beauty       interface states, hierarchy, keyboard, contrast

# write it and prove it
/build        implement, failing test first
/debug        find the cause, not the symptom
/verify       proof before the words "it passes"

# check what came out
/vet          read the diff before it merges
/probe        drive the running app, report the bugs it has
/measure      where the time actually goes
/ui           the states an interface owes the user

# hand it over
/revise       answer every review comment, rework the branch
/land         commit, push, open the pull request
/merge        merge once CI is green
/deploy       ship, with the way back ready first
/handoff      save state the next session can resume from
/handon       resume from a saved checkpoint, picked from the list

# keep the session honest
/fence        guards on destructive commands and stray edits
/prose        strip machine tells without flattening the writing
/primeskills  print the guide to this set
```
<!-- skills:end -->

`primeskills-help` prints the full guide — in your language, any of them:
`primeskills-help --set-lang <language>`, and the choice is remembered.

## Commands

```
primeskills-help              the guide to the set
primeskills-doctor            is everything connected, per agent
primeskills-status            what is in the set and what it weighs
primeskills-run show          the run record of the current branch
primeskills-run ship          run + record + open rungs in one call
primeskills-handoffs          which checkpoints are saved in this tree
primeskills-adherence --all   were the invariants of called skills followed
primeskills-lint              skill format: rules F and C — including G16 (F16) and the asking means (F17)
primeskills-release           release notes; changed skills must have been called live in all four hosts
python3 tests/run.py          the whole suite
```

Numbers in the documents are not typed by hand: `primeskills-status` reads them
out of the repository.

## Licence

MIT — `LICENSE`. The set was synthesised from seven sources; what came from
where, under which licence and from whom is in `ATTRIBUTIONS.md` and `NOTICE`,
line by line in `docs/SKILL-SOURCES.md`.

## Documents

`CHANGELOG.md` — what changed. `PLAN.md` — the intent and the principles.
`docs/SKILL-FORMAT.md` — the skill format and the linter rules.
`docs/RULE-COVERAGE.md` — which rule is held by what: a machine check or an
honestly-named insurance policy. `TODOS.md` — the queue. Version 0.9.14: the set
works, but it has not yet proved itself by measurement on live tasks, and
`PS-009` says in advance at which numbers it gets folded back.
