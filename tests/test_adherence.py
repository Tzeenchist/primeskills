#!/usr/bin/env python3
"""The adherence reader must reproduce verdicts that were derived by hand.

One fixture is a real session reduced to its tool calls -- the SHOP-009 run of
2026-08-17, where `build` was invoked and its red phase was not honoured. That
verdict was established by reading the transcript manually before this tool
existed, so it is the regression that matters most.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "bin" / "primeskills-adherence"
FIX = ROOT / "tests" / "fixtures" / "transcripts"

# fixture -> substrings that must all appear in the report
EXPECT = {
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
}


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

    db = fixtures / "opencode.db"
    con = sqlite3.connect(db)
    con.execute("create table part (id text, session_id text, time_created int, data text)")
    for n, part in enumerate([
        {"type": "tool", "tool": "read", "state": {"input": {"filePath": "/home/x/.config/opencode/skills/land/SKILL.md"}}},
        {"type": "tool", "tool": "bash", "state": {"input": {"command": "git status"}}},
    ]):
        con.execute("insert into part values (?,?,?,?)", (str(n), "ses_1", n, _json.dumps(part)))
    con.commit(); con.close()
    checks += 1
    p = subprocess.run([sys.executable, str(TOOL), f"{db}::ses_1"], capture_output=True, text=True)
    if "вызовов скиллов: 1 (land)" not in p.stdout:
        failures.append(f"база OpenCode прочитана неверно:\n{p.stdout}")

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

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
