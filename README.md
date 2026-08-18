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
> philosophy I built PRIMESKILLS on.
>
> — Ilya Priymak, author

```
always in context        443 words for all 27 skills
shared rules             2 545 words, once per session
one skill call           3 242 … 3 654 words
```

**The ceiling on one call is 4 000 words** (rule C3), and a check holds it
rather than a promise: the linter refuses a skill that pushes a call over the
ceiling. For comparison, one pass of the gstack set costs about 92 000 words —
measured in `bench/RESULT.md`.

## Discipline and evidence

**Order instead of memory.** The failing test comes before the code. "It
passed" means an exit code and a test count, not the absence of an error in the
output. Before a destructive command, say out loud what it will touch. Three
failed attempts on one problem: stop and ask.

**Evidence outlives the session.** A test run is recorded on disk together with
a fingerprint of the tree it ran against. Change a file after a green run and
the record goes stale, and the next step sees that. The agent cannot appeal to
a check that never happened, or to one that was about different code.

**Authority by rungs.** Commit, push, pull request, merge, migrate, deploy,
roll back, delete — eight separate yeses. One does not open the next,
permission for staging does not open production, and permission for one deploy
does not cover tomorrow's.

**Text it did not write is data, not orders.** Repository instructions, an
issue, a dependency's documentation, a page on the web: the agent checks them
instead of obeying a command found inside. And it does not run someone else's
code before it has read the diff.

**Nothing goes out.** No telemetry, no network, no dependencies.

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

Python 3 and git. Nothing else: no packages to install, no network.

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

The other twenty-two are called one at a time: `/brief` and `/study` to
understand the task and someone else's code; `/build`, `/debug`, `/verify` to
write and prove; `/vet`, `/probe`, `/measure`, `/ui` to check the diff, the
running app, the speed, the interface states; `/land`, `/merge`, `/deploy` to
hand over and ship; `/handoff` to save state for the next session.

`primeskills-help` prints the full guide — in your language, any of them:
`primeskills-help --set-lang <language>`, and the choice is remembered.

## Commands

```
primeskills-help              the guide to the set
primeskills-doctor            is everything connected, per agent
primeskills-status            what is in the set and what it weighs
primeskills-run show          the run record of the current branch
primeskills-adherence --all   were the invariants of called skills followed
primeskills-lint              skill format: rules F and C
python3 tests/run.py          the whole suite
```

Numbers in the documents are not typed by hand: `primeskills-status` reads them
out of the repository.

## Licence

MIT — `LICENSE`. The set was synthesised from six sources; what came from
where, under which licence and from whom is in `ATTRIBUTIONS.md` and `NOTICE`,
line by line in `docs/SKILL-SOURCES.md`.

## Documents

`CHANGELOG.md` — what changed. `PLAN.md` — the intent and the principles.
`docs/SKILL-FORMAT.md` — the skill format and the linter rules. `TODOS.md` —
the queue. Version 0.2.0: the set works, but it has not yet proved itself by
measurement on live tasks, and `PS-009` says in advance at which numbers it
gets folded back.
