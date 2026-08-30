#!/usr/bin/env python3
"""The adherence reader must reproduce verdicts that were derived by hand.

One fixture is a real session reduced to its tool calls -- the SHOP-009 run of
2026-08-17, where `build` was invoked and its red phase was not honoured. That
verdict was established by reading the transcript manually before this tool
existed, so it is the regression that matters most.
"""
import importlib.machinery
import importlib.util
import os
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "bin" / "primeskills-adherence"
FIX = ROOT / "tests" / "fixtures" / "transcripts"

# fixture -> substrings that must all appear in the report
EXPECT = {
    # PS-073. A skill typed as `/handoff` is a user turn, not a `tool_use`, and
    # counting only `tool_use` valued the way a person reaches for the set at
    # zero. This fixture holds no Skill call at all.
    "slash-command-counts.jsonl": [
        "вызовов скиллов: 1 (handoff)",
    ],
    # PS-073, owner's ruling 2026-08-30: four bodies read is four invocations.
    # In Codex a flow arrives as one `exec_command` chaining core and the chain
    # of skills with `&&`; counting the first name only threw the rest away.
    # One action, still one tool call -- three invocations inside it.
    "rollout-one-command-four-bodies.jsonl": [
        "вызовов инструментов: 1   вызовов скиллов: 3",
        "вызовов скиллов: 3 (build, cycle, verify)",
    ],
    # PS-073. Reading five SKILL.md files is studying the set -- unless they are
    # the chain one flow declares it calls. `lazy` names about nineteen, so
    # every honest run of it used to be discarded as study, which punished the
    # sessions that used the most of the set.
    "rollout-flow-reads-its-own-chain.jsonl": [
        "вызовов скиллов: 7 (autoplan, brief, build, cycle, lazy, plan, verify)",
    ],
    # ... and the rule it must not loosen: six skills that belong to no common
    # flow are still somebody paging through the directory.
    "rollout-reading-the-whole-directory.jsonl": [
        "вызовов скиллов: 0",
    ],
    "live-build-red-phase.jsonl": [
        "вызовов скиллов: 1 (build)",
        "core/ прочитан: действие #1",
        "[НАРУШЕН] красная фаза",
        "код #68 раньше теста #82",
    ],
    "build-red-phase-ok.jsonl": [
        "[ok  ] красная фаза",
        # order alone is not a red phase: the run between them is the evidence
        "тест #3, прогон #4, код #5",
        "доля 100%",
    ],
    "readonly-violation.jsonl": [
        "[НАРУШЕН] не пишет (G16)",
        "sed -i",
    ],
    "readonly-wc-ok.jsonl": [
        "[ok  ] не пишет (G16)",
        "доля 100%",
    ],
    "readonly-stat-ok.jsonl": [
        "[ok  ] не пишет (G16)",
        "доля 100%",
    ],
    "readonly-rg-ok.jsonl": [
        "[ok  ] не пишет (G16)",
        "доля 100%",
    ],
    "readonly-tee-violation.jsonl": [
        "[НАРУШЕН] не пишет (G16)",
        "tee findings.txt",
    ],
    "readonly-redirect-violation.jsonl": [
        "[НАРУШЕН] не пишет (G16)",
        "> findings.txt",
    ],
    "verify-exit-unknown.jsonl": [
        "[неизв] прогон состоялся (G4)",
        "0 применимых, 1 неизвестных",
    ],
    "verify-and-debug.jsonl": [
        "[НАРУШЕН] прогон состоялся (G4)",
        "[НАРУШЕН] воспроизведение до правки",
        "вызовов скиллов: 2 (debug, verify)",
    ],
    "git-hygiene-violation.jsonl": [
        "[НАРУШЕН] гигиена git (G14)",
        "git add -A",
        "[ok  ] дифф прочитан до коммита",
    ],
    "handoff-home.jsonl": [
        "[НАРУШЕН] чекпоинт в репозитории, не в доме",
        ".gstack/checkpoints",  # the fragment, not one account's home
    ],
    "flow-order-violation.jsonl": [
        "[НАРУШЕН] порядок цепочки",
        "land → deploy → merge",
    ],
    "green-by-test-edit.jsonl": [
        "[НАРУШЕН] зелень не куплена правкой теста",
        "test_totals.py",
    ],
    "g17-two-step.jsonl": [
        # resolve, print, act -- the pattern the guardrail describes
        "[ok  ] цель разрешена до разрушения (G8)",
        "цель напечатана предыдущей командой",
        # printed one target, destroyed another: the incident G8 came from
        "[НАРУШЕН] цель разрешена до разрушения (G8)",
        "dropdb prod_shop",
    ],
    # PS-077. The user's turn is a boundary in every host, not only in Claude
    # Code: Codex writes it as a `message` payload with role user, Kimi as a
    # `context.append_message` whose origin is the user, OpenCode as a row in
    # `message`. Until this, a span in those three ran to the next invocation.
    "rollout-user-turn-ends-span.jsonl": [
        "build (вызван #1, 2 действий в пролёте, конец по реплике пользователя)",
        "[НАРУШЕН] цель разрешена до разрушения (G8)",
    ],
    # the name is forced: `load_calls` picks the Kimi reader by it
    "wire.jsonl": [
        "build (вызван #1, 2 действий в пролёте, конец по реплике пользователя)",
        "[НАРУШЕН] цель разрешена до разрушения (G8)",
    ],
    # PS-078. Exit codes are not in the logs: of 8824 Bash calls in Claude Code
    # transcripts none carries one, and Codex records one in 19 of 3047. So the
    # only way this check could ever say "ok" was a `primeskills-run note` in
    # the span -- typing, not proof. G4 names the other evidence: the tool's own
    # success signal, read from its output.
    "suite-note-is-not-a-run.jsonl": [
        "[НАРУШЕН] прогон состоялся (G4)",
        "прогона тестов в пролёте нет",
    ],
    "suite-signal-in-output.jsonl": [
        "[ok  ] прогон состоялся (G4)",
        "0 failed",
    ],
    "suite-signal-red.jsonl": [
        "[НАРУШЕН] прогон состоялся (G4)",
        "3 failed",
    ],
    # PS-076. A span used to run to the next invocation or to the end of the
    # session, so a call in the first message owned everything after it --
    # 24 of 42 violations sat on spans longer than the cap. Two boundaries
    # close it: the exit the skill writes down, and, where none was written,
    # the user's next turn. What falls outside stays in the session-wide G8,
    # so the tail is unowned, never dropped.
    "span-ends-at-record.jsonl": [
        "build (вызван #1, 2 действий в пролёте, конец по записи)",
        # the 45 actions after the record belong to nobody, and the
        # destructive one among them is still judged
        "[НАРУШЕН] цель разрешена до разрушения (G8)",
        "rm -rf /tmp/postoronnee",
    ],
    "span-ends-at-user-turn.jsonl": [
        "build (вызван #1, 2 действий в пролёте, конец по реплике пользователя)",
        "[НАРУШЕН] цель разрешена до разрушения (G8)",
        "rm -rf /tmp/postoronnee",
    ],
    # The guard that matters most: Claude Code delivers a tool result as a
    # user-role message, and the body of a skill as an isMeta one. Read either
    # as a turn and every span collapses at its first action -- a measurement
    # that would look like a triumph and mean nothing.
    # An approval is not a new instruction. Measured over 711 live turns: 106
    # are 12 characters or shorter, and the two commonest are "Давай" (33) and
    # "Да" (30) -- said in the middle of a flow, to let it carry on. Cut the
    # span there and everything the skill did after being approved stops being
    # its own: the one direction this must never fail in.
    "span-approval-is-not-a-turn.jsonl": [
        "build (вызван #1, 3 действий в пролёте)",
    ],
    # The same trap one turn later: a command that WRITES the marker into a
    # fixture is not the marker. Found on the tool's own session, where the
    # command generating these very fixtures closed a span. `echo` was already
    # on record for this; anywhere-in-the-text was the wider version of it.
    "span-record-mentioned-not-run.jsonl": [
        "build (вызван #1, 3 действий в пролёте)",
    ],
    "span-survives-tool-results.jsonl": [
        "build (вызван #1, 3 действий в пролёте)",
    ],
    "land-and-g17.jsonl": [
        "[НАРУШЕН] дифф прочитан до коммита (G17)",
        # the printed target passes, the bare one does not
        "[ok  ] цель разрешена до разрушения (G8)",
        "[НАРУШЕН] цель разрешена до разрушения (G8)",
    ],
}

# a report must never claim a verdict the fixture cannot support
FORBIDDEN = {
    "build-red-phase-ok.jsonl": ["НАРУШЕН"],
    "live-build-red-phase.jsonl": ["[ok  ] красная фаза"],
    "readonly-wc-ok.jsonl": ["НАРУШЕН"],
    "readonly-stat-ok.jsonl": ["НАРУШЕН"],
    "readonly-rg-ok.jsonl": ["НАРУШЕН"],
    "span-ends-at-record.jsonl": ["длиннее отсечки"],
    "span-ends-at-user-turn.jsonl": ["длиннее отсечки"],
    "span-survives-tool-results.jsonl": ["конец по реплике", "конец по записи"],
    "span-record-mentioned-not-run.jsonl": ["конец по записи"],
    "span-approval-is-not-a-turn.jsonl": ["конец по реплике"],
    "rollout-user-turn-ends-span.jsonl": ["длиннее отсечки"],
    "wire.jsonl": ["длиннее отсечки"],
}


def _load(path):
    loader = importlib.machinery.SourceFileLoader("_adh", str(path))
    spec = importlib.util.spec_from_loader("_adh", loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


adh = _load(TOOL)


def main():
    failures = []
    checks = 0
    tmp_dir = tempfile.TemporaryDirectory()
    tmp = tmp_dir.name

    for name, wanted in sorted(EXPECT.items()):
        path = FIX / name
        if not path.is_file():
            failures.append(f"{name}: фикстуры нет")
            continue
        # A fixture about writing outside the repository has to name the home of
        # whoever is running it. Hard-coding one account made the fixture pass
        # on one machine and silently stop testing anything on any other, so the
        # path is a placeholder and is filled in here.
        raw = path.read_text(encoding="utf-8")
        if "{HOME}" in raw:
            path = Path(tmp) / name
            path.write_text(raw.replace("{HOME}", str(Path.home())), encoding="utf-8")
        p = subprocess.run([sys.executable, str(TOOL), str(path)],
                           capture_output=True, text=True)
        out = p.stdout + p.stderr
        for text in wanted:
            checks += 1
            if text not in out:
                failures.append(f"{name}: нет {text!r}\n{out}")
        for text in FORBIDDEN.get(name, []):
            checks += 1
            if text in out:
                failures.append(f"{name}: не должно быть {text!r}")

    # no arguments must explain itself rather than crash
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True)
    if p.returncode != 0 or "primeskills-adherence" not in p.stdout:
        failures.append("без аргументов: ожидалась справка")

    # a file that is not a transcript must not be reported as a clean session
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), str(ROOT / "README.md")],
                       capture_output=True, text=True)
    if p.returncode != 0:
        failures.append("нежурнальный файл уронил инструмент")

    # the same task moves between four agents, so the reader must speak all
    # four log formats — and must not mistake reading the set for using it
    import json as _json
    import sqlite3
    fixtures = Path(tmp) / "agents"
    fixtures.mkdir()

    codex = fixtures / "rollout-2026-08-18T00-00-00-test.jsonl"
    codex.write_text("\n".join(_json.dumps(e, ensure_ascii=False) for e in [
        {"type": "session_meta", "payload": {"cwd": "/srv/demo"}},
        {"type": "response_item", "payload": {"type": "custom_tool_call", "name": "exec",
         "input": 'await Promise.all([tools.exec_command({cmd:"cat /home/x/.codex/skills/build/SKILL.md"}),'
                  ' tools.exec_command({cmd:"pytest -q"})])'}},
    ]) + "\n", encoding="utf-8")
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), str(codex)], capture_output=True, text=True)
    if "вызовов инструментов: 2" not in p.stdout or "вызовов скиллов: 1 (build)" not in p.stdout:
        failures.append(f"журнал Codex прочитан неверно:\n{p.stdout}")

    kimi = fixtures / "wire.jsonl"
    kimi.write_text("\n".join(_json.dumps(e, ensure_ascii=False) for e in [
        {"type": "context.append_loop_event", "event": {"type": "tool.call", "name": "Read",
         "args": {"file_path": "/home/x/.kimi-code/skills/verify/SKILL.md"}}},
        {"type": "context.append_loop_event", "event": {"type": "tool.call", "name": "Bash",
         "args": {"command": "pytest -q"}}},
    ]) + "\n", encoding="utf-8")
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), str(kimi)], capture_output=True, text=True)
    if "вызовов скиллов: 1 (verify)" not in p.stdout:
        failures.append(f"журнал Kimi прочитан неверно:\n{p.stdout}")

    # The real store keeps the role one table over and links parts to it by
    # message_id; the schema here matches that, because a fixture that models
    # less than the real thing stops testing before the code does (PS-077).
    db = fixtures / "opencode.db"
    con = sqlite3.connect(db)
    con.execute("create table part (id text, message_id text, session_id text, "
                "time_created int, data text)")
    con.execute("create table message (id text, session_id text, data text)")
    for mid, role in (("m1", "assistant"), ("m2", "user"), ("m3", "assistant")):
        con.execute("insert into message values (?,?,?)",
                    (mid, "ses_1", _json.dumps({"role": role})))
    for n, (mid, part) in enumerate([
        ("m1", {"type": "tool", "tool": "read", "state": {"input": {"filePath": "/home/x/.config/opencode/skills/land/SKILL.md"}}}),
        ("m1", {"type": "tool", "tool": "bash", "state": {"input": {"command": "git status"}}}),
        # the person speaks: everything after this is a new instruction, not
        # `land` still running
        ("m2", {"type": "text", "text": "стоп, дальше совсем другая задача"}),
        ("m3", {"type": "tool", "tool": "bash", "state": {"input": {"command": "rm -rf /tmp/postoronnee"}}}),
    ]):
        con.execute("insert into part values (?,?,?,?,?)",
                    (str(n), mid, "ses_1", n, _json.dumps(part)))
    con.commit(); con.close()
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), f"{db}::ses_1"], capture_output=True, text=True)
    if "вызовов скиллов: 1 (land)" not in p.stdout:
        failures.append(f"база OpenCode прочитана неверно:\n{p.stdout}")
    checks += 1
    if "land (вызван #1, 1 действий в пролёте, конец по реплике пользователя)" not in p.stdout:
        failures.append(f"реплика пользователя в OpenCode не оборвала пролёт:\n{p.stdout}")
    checks += 1
    if "[НАРУШЕН] цель разрешена до разрушения (G8)" not in p.stdout:
        failures.append(f"выпавшее из пролёта выпало и из сессионного G8:\n{p.stdout}")

    # reading the whole set is studying it, not calling it
    study = fixtures / "study-wire.jsonl"
    study.write_text("\n".join(_json.dumps(
        {"type": "context.append_loop_event", "event": {"type": "tool.call", "name": "Read",
         "args": {"file_path": f"/home/x/.kimi-code/skills/{name}/SKILL.md"}}},
        ensure_ascii=False) for name in ("build", "verify", "land", "plan", "vet", "probe")) + "\n",
        encoding="utf-8")
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), str(study)], capture_output=True, text=True)
    if "вызовов скиллов: 0" not in p.stdout:
        failures.append(f"чтение всего набора засчитано как вызовы:\n{p.stdout}")

    # sessions of one directory, close in time, are one task — even when they
    # were written by different agents. PS-009 counts tasks, not sessions.
    home2 = Path(tmp) / "home2"
    proj = home2 / ".claude" / "projects" / "-srv-demo"
    proj.mkdir(parents=True)
    call = ('{"type": "assistant", "cwd": "/srv/demo", "message": {"content": '
            '[{"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}}\n')
    for n in ("one.jsonl", "two.jsonl"):
        (proj / n).write_text(call, encoding="utf-8")
    codex_dir = home2 / ".codex" / "sessions" / "2026" / "08" / "18"
    codex_dir.mkdir(parents=True)
    (codex_dir / "rollout-2026-08-18T00-00-00-x.jsonl").write_text(
        _json.dumps({"type": "session_meta", "payload": {"cwd": "/srv/demo"}}) + "\n",
        encoding="utf-8")
    env2 = dict(os.environ, HOME=str(home2))
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), "--all", "--summary"],
                       capture_output=True, text=True, env=env2)
    if "сессий: 3" not in p.stdout or "задач: 1" not in p.stdout:
        failures.append(f"сессии одного каталога не сошлись в задачу:\n{p.stdout}")
    checks += 1
    if "прошли через несколько агентов" not in p.stdout or "из них 1" not in p.stdout:
        failures.append(f"переход задачи между агентами не опознан:\n{p.stdout}")

    # PS-009 asks its question about *this* set. A task that called
    # `gstack-ship` is a task where some set was reached for, not evidence
    # about ours, and counting the two together put foreign skills in the
    # denominator the criterion is read off.
    home3 = Path(tmp) / "home3"
    mine = home3 / ".claude" / "projects" / "-srv-mine"
    theirs = home3 / ".claude" / "projects" / "-srv-theirs"
    for d in (mine, theirs):
        d.mkdir(parents=True)
    skill_call = ('{"type": "assistant", "cwd": "%s", "message": {"content": '
                  '[{"type": "tool_use", "name": "Skill", "input": '
                  '{"skill": "%s"}}]}}\n')
    (mine / "a.jsonl").write_text(skill_call % ("/srv/mine", "build"),
                                  encoding="utf-8")
    (theirs / "b.jsonl").write_text(skill_call % ("/srv/theirs", "gstack-ship"),
                                    encoding="utf-8")
    env3 = dict(os.environ, HOME=str(home3))
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), "--all", "--summary"],
                       capture_output=True, text=True, env=env3)
    if "задач с вызовом любого скилла: 2" not in p.stdout:
        failures.append(f"задачи с любым скиллом посчитаны не все:\n{p.stdout}")
    checks += 1
    if "с вызовом этого набора: 1" not in p.stdout:
        failures.append(f"чужой скилл засчитан набору:\n{p.stdout}")
    checks += 1
    if "навыков набора вызвано хоть раз: 1 из" not in p.stdout:
        failures.append(f"широта вызова набора посчитана неверно:\n{p.stdout}")

    # a task run inside a checkout of the set is work *on* it: it belongs on
    # the other side of the criterion from work done *with* it
    inside = Path(tmp) / "checkout"
    (inside / "bin").mkdir(parents=True)
    (inside / "core").mkdir(parents=True)
    (inside / "bin" / "primeskills-status").write_text("", encoding="utf-8")
    (inside / "core" / "PRINCIPLES.md").write_text("", encoding="utf-8")
    slug = "-" + str(inside).strip("/").replace("/", "-")
    self_work = home3 / ".claude" / "projects" / slug
    self_work.mkdir(parents=True)
    (self_work / "c.jsonl").write_text(skill_call % (str(inside), "verify"),
                                       encoding="utf-8")
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), "--all", "--summary"],
                       capture_output=True, text=True, env=env3)
    if "с вызовом этого набора: 2, и 1 из них шли внутри самого набора" not in p.stdout:
        failures.append(f"работа над набором не отделена от применения:\n{p.stdout}")

    # ...and a session that never stood in the set still edits it: it runs from
    # $HOME and reaches the repository by absolute path. Judged by the working
    # directory alone, a whole day of work *on* the set counted as work *with*
    # it (found 2026-08-20, PS-007).
    outside = home3 / ".claude" / "projects" / "-home-someone"
    outside.mkdir(parents=True)
    (outside / "d.jsonl").write_text(
        _json.dumps({"type": "assistant", "cwd": "/home/someone", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "vet"}}]}}) + "\n"
        + _json.dumps({"type": "assistant", "cwd": "/home/someone", "message": {"content": [
            {"type": "tool_use", "name": "Edit",
             "input": {"file_path": str(inside / "core" / "PRINCIPLES.md")}}]}}) + "\n",
        encoding="utf-8")
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), "--all", "--summary"],
                       capture_output=True, text=True, env=env3)
    if "с вызовом этого набора: 3, и 2 из них шли внутри самого набора" not in p.stdout:
        failures.append("правка набора из чужого каталога не опознана как "
                        f"работа над ним:\n{p.stdout}")

    # command text out of someone's log must not carry a token into this report
    leaky = Path(tmp) / "leaky.jsonl"
    leaky.write_text(_json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Bash", "input": {"command":
         "curl -H 'Authorization: Bearer ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345' https://api"}}]}},
        ensure_ascii=False) + "\n", encoding="utf-8")
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), str(leaky)], capture_output=True, text=True)
    if "ghp_ABCDEFG" in p.stdout:
        failures.append("токен из журнала попал в отчёт")

    # --all must read every session, not one per project. The defect it guards
    # against read 3 files out of 44 and reported the result as "--all".
    home = Path(tmp) / "home"
    project = home / ".claude" / "projects" / "-srv-two-sessions"
    project.mkdir(parents=True)
    call = ('{"type": "assistant", "message": {"content": [{"type": "tool_use", '
            '"name": "Bash", "input": {"command": "ls"}}]}}\n')
    for n in ("older.jsonl", "newer.jsonl"):
        (project / n).write_text(call, encoding="utf-8")
    older, newer = project / "older.jsonl", project / "newer.jsonl"
    os.utime(older, (1, 1))

    env = dict(os.environ, HOME=str(home))
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), "--all"],
                       capture_output=True, text=True, env=env)
    if "сессий: 2" not in p.stdout:
        failures.append(f"--all прочитал не все сессии:\n{p.stdout}")

    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), "--all", "--newest"],
                       capture_output=True, text=True, env=env)
    if "сессий: 1" not in p.stdout:
        failures.append(f"--newest должен оставить одну сессию:\n{p.stdout}")

    # PS-073. The last blind spot: a flow whose bodies the host hands over
    # leaves no read to infer from and no invocation event to count -- `lazy`
    # ran many times and was never once visible. `core/` now asks a flow to
    # write itself into the run record on its first step, and the reader joins
    # that record to the task by directory and time. Without it this session,
    # which calls nothing, would report no skills at all.
    with tempfile.TemporaryDirectory() as tree:
        work = Path(tree) / "work"
        (work / ".primeskills" / "run").mkdir(parents=True)
        session = Path(tree) / "session.jsonl"
        session.write_text(json.dumps({
            "cwd": str(work),
            "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": "pytest -q"}}]}}) + "\n", encoding="utf-8")
        stamp = datetime.fromtimestamp(session.stat().st_mtime,
                                       tz=timezone.utc).isoformat()
        (work / ".primeskills" / "run" / "master-1.jsonl").write_text(
            json.dumps({"kind": "note", "stage": "flow", "skill": "lazy",
                        "text": "починить импорт", "ts": stamp}) + "\n",
            encoding="utf-8")

        checks += 1
        out = subprocess.run([sys.executable, str(TOOL), str(session)],
                             capture_output=True, text=True).stdout
        if "вызовов скиллов: 1 (lazy)" not in out:
            failures.append(f"след потока не прочитан из записи прогона:\n{out}")
        checks += 1
        if "с вызовом этого набора: 1" not in out:
            failures.append(f"задача со следом потока не засчитана набору:\n{out}")

        # One note belongs to one task. Windows on neighbouring tasks of the
        # same tree overlap, and counting a note in both would inflate exactly
        # the number this was written to repair.
        # The note sits between two tasks 7 h apart, inside a +-6 h window drawn
        # around either one: that is the shape a window cannot resolve.
        far = Path(tree) / "far.jsonl"
        far.write_text(json.dumps({
            "cwd": str(work),
            "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": "t2", "name": "Bash",
                 "input": {"command": "ls"}}]}}) + "\n", encoding="utf-8")
        now = session.stat().st_mtime
        os.utime(far, (now - 7 * 3600, now - 7 * 3600))
        between = datetime.fromtimestamp(now - 4.5 * 3600,
                                         tz=timezone.utc).isoformat()
        (work / ".primeskills" / "run" / "master-1.jsonl").write_text(
            json.dumps({"kind": "note", "stage": "flow", "skill": "lazy",
                        "text": "починить импорт", "ts": between}) + "\n",
            encoding="utf-8")
        checks += 1
        out = subprocess.run([sys.executable, str(TOOL), str(session), str(far)],
                             capture_output=True, text=True).stdout
        if "задач: 2" not in out:
            failures.append(f"ждали две задачи в одном дереве:\n{out}")
        checks += 1
        if "вызовов скиллов: 1 (lazy)" not in out:
            failures.append(f"одна запись потока засчитана дважды:\n{out}")

        # and the same note must not count twice when the host did record it
        session.write_text(json.dumps({
            "cwd": str(work),
            "message": {"role": "user",
                        "content": "<command-name>/lazy</command-name>"}}) + "\n",
            encoding="utf-8")
        checks += 1
        out = subprocess.run([sys.executable, str(TOOL), str(session)],
                             capture_output=True, text=True).stdout
        if "вызовов скиллов: 1 (lazy)" not in out:
            failures.append(f"слэш-вызов и запись потока сложились в два:\n{out}")

    # PS-074. Counting every name in a command (PS-073) made one line of prose
    # about skills read as several invocations. A command that only writes read
    # nothing; the target of a redirect is not a read either.
    for cmd, want, why in (
        ('echo "см. skills/a/SKILL.md skills/b/SKILL.md" > n.md', [],
         "прозу про навыки посчитали вызовами"),
        ('printf "%s" skills/build/SKILL.md >> log', [],
         "printf ничего не читает"),
        ('cat /x/skills/build/SKILL.md', ["build"],
         "обычное чтение перестало считаться"),
        ('cat /x/skills/build/SKILL.md > /tmp/copy.md', ["build"],
         "чтение с редиректом потеряно — читали всё-таки навык"),
        ('sed -n 1,9p /x/skills/cycle/SKILL.md && sed -n 1,9p /x/skills/verify/SKILL.md',
         ["cycle", "verify"], "цепочка чтений схлопнулась"),
        # Judged per segment: the first cut blanked the whole line whenever it
        # mentioned `echo`, and threw away the read standing next to it -- the
        # same defect pointing the other way.
        ('cat /x/skills/build/SKILL.md && echo ok', ["build"],
         "чтение рядом с echo потеряно"),
        ('echo start; cat /x/skills/verify/SKILL.md', ["verify"],
         "чтение после echo потеряно"),
        ('cat /x/skills/build/SKILL.md | tee /tmp/c.md', ["build"],
         "чтение с tee потеряно"),
    ):
        checks += 1
        got = adh.named_skills("", cmd)
        if got != want:
            failures.append(f"named_skills: {why}: {cmd[:50]!r} -> {got}, "
                            f"ждали {want}")

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
