#!/usr/bin/env python3
"""The adherence reader must reproduce verdicts that were derived by hand.

One fixture is a real session reduced to its tool calls -- the SHOP-009 run of
2026-08-17, where `build` was invoked and its red phase was not honoured. That
verdict was established by reading the transcript manually before this tool
existed, so it is the regression that matters most.
"""
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
        "[НАРУШЕН] не пишет (G7)",
        "sed -i",
    ],
    "verify-and-debug.jsonl": [
        "[НАРУШЕН] прогон состоялся (G4)",
        "[НАРУШЕН] воспроизведение до правки",
        "вызовов скиллов: 2 (debug, verify)",
    ],
    "git-hygiene-violation.jsonl": [
        "[НАРУШЕН] гигиена git (G11)",
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
        "[ok  ] цель разрешена до разрушения (G17)",
        "цель напечатана предыдущей командой",
        # printed one target, destroyed another: the incident G17 came from
        "[НАРУШЕН] цель разрешена до разрушения (G17)",
        "dropdb prod_shop",
    ],
    "land-and-g17.jsonl": [
        "[НАРУШЕН] дифф прочитан до коммита (G6)",
        # the printed target passes, the bare one does not
        "[ok  ] цель разрешена до разрушения (G17)",
        "[НАРУШЕН] цель разрешена до разрушения (G17)",
    ],
}

# a report must never claim a verdict the fixture cannot support
FORBIDDEN = {
    "build-red-phase-ok.jsonl": ["НАРУШЕН"],
    "live-build-red-phase.jsonl": ["[ok  ] красная фаза"],
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

    # --all must read every session, not one per project. The defect it guards
    # against read 3 files out of 44 and reported the result as "--all".
    home = Path(tmp) / "home"
    project = home / ".claude" / "projects" / "-srv-two-sessions"
    project.mkdir(parents=True)
    call = ('{"type": "assistant", "message": {"content": [{"type": "tool_use", '
            '"name": "Bash", "input": {"command": "ls"}}]}}\n')
    for n in ("older.jsonl", "newer.jsonl"):
        (project / n).write_text(call, encoding="utf-8")
    import os
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
