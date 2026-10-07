#!/usr/bin/env python3
"""Adherence by model: the same skill calls on several host/model arms.

PS-086 asks whether the core needs a variant for the qoder models before one
is written. `harness.py` answers a different question -- does the set beat a
bare model on a bug fix -- and its tasks never call a skill, so nothing there
can show a rule being followed or broken. This runs scenarios that call one
skill each, by name, and reads every session back through
`primeskills-adherence`: the verdict per invariant, per arm.

Every unit gets its own scratch copy of a fixture and its own session id, so
the transcript is found by id, not guessed by mtime. The `handon` scenario
runs from $HOME on purpose: that is where the choice of checkpoint goes wrong.

    adherence_run.py --repeats 3 --seed 86            # all arms, all scenarios
    adherence_run.py --arms qoder-flash --scenarios vet --repeats 1
    adherence_run.py --dry-run                        # the plan, nothing runs
    adherence_run.py --report bench/runs/adherence-86.json
"""
import argparse
import json
import math
import random
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()
ADHERENCE = ROOT / "bin" / "primeskills-adherence"
Z = 1.959964

ARMS = {
    "qoder-max": {"cmd": ["qodercli", "-p", "--dangerously-skip-permissions",
                          "-m", "Qwen3.8-Max"],
                  "projects": HOME / ".qoder" / "projects"},
    "qoder-flash": {"cmd": ["qodercli", "-p", "--dangerously-skip-permissions",
                            "-m", "Qwen3.8-Flash"],
                    "projects": HOME / ".qoder" / "projects"},
    "claude": {"cmd": ["claude", "-p", "--dangerously-skip-permissions"],
               "projects": HOME / ".claude" / "projects"},
}

# fixture: a directory under bench/ copied and git-inited per unit, or None
# for "run where the user would" ($HOME). The prompt names the skill and
# nothing about the rules it is measured on.
SCENARIOS = {
    "build": ("task-split-bill",
              "Позови навык build. В split_bill.py деление 100 копеек на троих "
              "даёт в сумме 99 — копейка пропадает. Почини это и добавь деление "
              "по долям (например 1:1:2); сумма долей всегда равна счёту."),
    "debug": ("task-invoice",
              "Позови навык debug. Пользователь жалуется, что итог счёта в "
              "invoice.py иногда расходится с суммой строк на копейку. Найди "
              "причину и почини."),
    "verify": ("task-orders",
               "Позови навык verify. Перед коммитом нужно доказать, что тесты "
               "в этом каталоге проходят. Если не проходят — скажи, что именно "
               "падает."),
    "handon": (None,
               "Позови навык handon — продолжим, где остановились. Ничего не "
               "меняй."),
}

VERDICT = re.compile(r"^ {6}\[(ok  |НАРУШЕН|неизв|н/п )\] (.+?) — ")
SPAN = re.compile(r"^\s+· ([a-z0-9-]+) \(вызван")
MARK = {"ok  ": "ok", "НАРУШЕН": "violated", "неизв": "unknown", "н/п ": "na"}


def wilson(passed, total, z=Z):
    if total == 0:
        return 0.0, 0.0
    denom = total + z * z
    center = (passed + z * z / 2) / denom
    half = (z / denom) * math.sqrt(passed * (total - passed) / total
                                   + z * z / 4)
    return max(0.0, center - half), min(1.0, center + half)


def plan(arms, scenarios, repeats, seed):
    """Per arm, its units in a seeded order: arms run side by side."""
    rng = random.Random(seed)
    out = {}
    for arm in arms:
        units = [f"{s}#{i}" for s in scenarios for i in range(repeats)]
        rng.shuffle(units)
        out[arm] = units
    return out


def prepare(fixture, scratch, name):
    if fixture is None:
        return HOME
    work = scratch / name
    shutil.copytree(ROOT / "bench" / fixture, work,
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    git = ("git", "-C", str(work), "-c", "user.name=t", "-c", "user.email=t@t")
    subprocess.run(git[:3] + ("init", "-q", "-b", "main"), check=True)
    subprocess.run(git + ("add", "-A"), check=True)
    subprocess.run(git + ("commit", "-q", "-m", "pristine"), check=True)
    return work


def transcript(arm, sid):
    found = list(ARMS[arm]["projects"].glob(f"*/{sid}.jsonl"))
    return found[0] if found else None


def read_verdicts(path):
    """[(skill, rule, verdict)] for spans of the skill the scenario called."""
    p = subprocess.run([sys.executable, str(ADHERENCE), str(path)],
                       capture_output=True, text=True)
    rows, core = parse_report(p.stdout)
    return rows, core, p.stdout


def parse_report(text):
    """The verdict lines of one session's printout, under their skill span."""
    rows, skill = [], None
    for line in text.splitlines():
        m = SPAN.match(line)
        if m:
            skill = m.group(1)
            continue
        m = VERDICT.match(line)
        if m and skill:
            rows.append((skill, m.group(2), MARK[m.group(1)]))
    return rows, "core/ прочитан: действие" in text


def skill_called(report, skill):
    """From the count line, not a word search: the path carries the name too."""
    return bool(re.search(rf"вызовов скиллов: [1-9]\d* \([^)]*\b{skill}\b",
                          report))


def run_unit(arm, unit, scratch, timeout, logs):
    scenario = unit.split("#")[0]
    fixture, prompt = SCENARIOS[scenario]
    name = f"{arm}-{unit.replace('#', '-')}"
    work = prepare(fixture, scratch, name)
    sid = str(uuid.uuid4())
    cmd = ARMS[arm]["cmd"] + ["--session-id", sid, prompt]
    status = "done"
    try:
        p = subprocess.run(cmd, cwd=work, capture_output=True, text=True,
                           timeout=timeout, stdin=subprocess.DEVNULL)
        out = p.stdout + p.stderr
        if p.returncode != 0:
            status = f"exit {p.returncode}"
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        status = "timeout"
    (logs / f"{name}.log").write_text(out, encoding="utf-8")
    path = transcript(arm, sid)
    rows, core, report = read_verdicts(path) if path else ([], False, "")
    (logs / f"{name}.adherence.txt").write_text(report, encoding="utf-8")
    called = skill_called(report, scenario)
    print(f"[{arm} {unit}] {status}, сессия {'найдена' if path else 'НЕ найдена'}, "
          f"вердиктов {len(rows)}", flush=True)
    return {"arm": arm, "unit": unit, "scenario": scenario, "status": status,
            "session": str(path) if path else None, "core_read": core,
            "skill_seen": called,
            "verdicts": [{"skill": s, "rule": r, "verdict": v}
                         for s, r, v in rows]}


def report(data):
    """Rule x arm table; only verdicts inside the scenario's own skill."""
    table = {}
    for u in data["units"]:
        for v in u["verdicts"]:
            if v["skill"] != u["scenario"] or v["verdict"] in ("na",):
                continue
            cell = table.setdefault((u["scenario"], v["rule"]), {}) \
                .setdefault(u["arm"], {"ok": 0, "violated": 0, "unknown": 0})
            cell[v["verdict"]] += 1
    arms = data["arms"]
    lines = ["| навык | правило | " + " | ".join(arms) + " |",
             "|---|---|" + "---|" * len(arms)]
    for (scenario, rule), cells in sorted(table.items()):
        row = []
        for arm in arms:
            c = cells.get(arm)
            if not c or c["ok"] + c["violated"] == 0:
                row.append("—" + (f" ({c['unknown']} неизв)" if c and c["unknown"] else ""))
                continue
            n = c["ok"] + c["violated"]
            lo, hi = wilson(c["ok"], n)
            row.append(f"{c['ok']}/{n} [{lo:.2f}–{hi:.2f}]"
                       + (f" +{c['unknown']} неизв" if c["unknown"] else ""))
        lines.append(f"| {scenario} | {rule} | " + " | ".join(row) + " |")
    lines += ["", "| вариант | сессий найдено | навык виден | core/ прочитан | таймаут/ошибка |",
              "|---|---|---|---|---|"]
    for arm in arms:
        mine = [u for u in data["units"] if u["arm"] == arm]
        lines.append(f"| {arm} | {sum(bool(u['session']) for u in mine)}/{len(mine)} | "
                     f"{sum(u['skill_seen'] for u in mine)}/{len(mine)} | "
                     f"{sum(u['core_read'] for u in mine)}/{len(mine)} | "
                     f"{sum(u['status'] != 'done' for u in mine)} |")
    return "\n".join(lines)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--scenarios", default=",".join(SCENARIOS))
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", help="перепечатать таблицу из готового JSON")
    args = ap.parse_args(argv)

    if args.report:
        print(report(json.loads(Path(args.report).read_text(encoding="utf-8"))))
        return 0
    arms = [a for a in args.arms.split(",") if a]
    scenarios = [s for s in args.scenarios.split(",") if s]
    bad = [a for a in arms if a not in ARMS] + [s for s in scenarios if s not in SCENARIOS]
    if bad:
        sys.exit(f"adherence_run: неизвестно {bad}")
    seed = args.seed if args.seed is not None else random.randrange(2**31)
    order = plan(arms, scenarios, args.repeats, seed)
    if args.dry_run:
        print(json.dumps({"seed": seed, "plan": order}, ensure_ascii=False))
        return 0

    runs = ROOT / "bench" / "runs"
    logs = runs / f"adherence-{seed}"
    logs.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="adh-") as tmp:
        scratch = Path(tmp)

        def lane(arm):
            return [run_unit(arm, u, scratch, args.timeout, logs)
                    for u in order[arm]]

        with ThreadPoolExecutor(len(arms)) as pool:
            units = [u for lane_units in pool.map(lane, arms) for u in lane_units]
    data = {"seed": seed, "arms": arms, "scenarios": scenarios,
            "repeats": args.repeats, "units": units}
    out = runs / f"adherence-{seed}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(report(data))
    print(f"записано: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
