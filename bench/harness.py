#!/usr/bin/env python3
"""Run one bench task across arms x repeats, grade every unit, aggregate.

PS-037 п.2: runs 3–8 each paid for their own hand-built stand and left behind
no way to re-run the experiment from a checkout. This file is the way. It
never touches the fixtures under bench/<task>/ -- those are the pristine
sources -- but copies each unit into its own scratch directory, git-inits it,
runs the host CLI headless with an identical prompt that names no set, grades
the result with the task's hidden grader (whose non-zero exit code is the
verdict), and sums tokens from the session log.

The arms differ in exactly one thing, the environment:

    set   the host's real HOME, primeskills installed;
    bare  a scratch HOME holding only the host's auth and config.

Arm order is shuffled under --seed so that machine load lands on both arms
alike, and the same seed reproduces the same order. Aggregation reports the
Wilson interval next to every pass rate: with two repeats a point estimate
is a mood, not a measurement (run 8's own caveat).
"""
import argparse
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
Z = 1.959964

# What one host needs to run headless. `home` is where auth lives in a normal
# install; `bare_files` are the only things a bare HOME may carry -- they
# authenticate and configure, they do not instruct.
HOSTS = {
    "codex": {
        "home": Path.home() / ".codex",
        "bare_files": ["auth.json", "config.toml"],
        "cmd": ["codex", "exec", "--skip-git-repo-check",
                "--sandbox", "danger-full-access"],
    },
}


def wilson(passed, total, z=Z):
    """Wilson score interval for a binomial proportion."""
    if total == 0:
        return 0.0, 0.0
    denom = total + z * z
    center = (passed + z * z / 2) / denom
    half = (z / denom) * math.sqrt(passed * (total - passed) / total
                                   + z * z / 4)
    return max(0.0, center - half), min(1.0, center + half)


def plan_arms(arms, repeats, seed):
    """Units of the run in execution order: deterministic from the seed."""
    units = [f"{arm}#{i}" for arm in arms for i in range(repeats)]
    random.Random(seed).shuffle(units)
    return units


def prepare_work(fixture: Path, scratch_root: Path, unit: str) -> Path:
    """A fresh git-inited copy of the pristine fixture; reset is re-copy."""
    work = scratch_root / unit.replace("#", "-")
    shutil.copytree(fixture, work)
    shutil.rmtree(work / "__pycache__", ignore_errors=True)
    shutil.rmtree(work / ".pytest_cache", ignore_errors=True)
    def git(*args):
        subprocess.run(("git", "-C", str(work)) + args, check=True,
                       capture_output=True)
    git("init", "-q", "-b", "main")
    git("-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@t",
        "commit", "-q", "-m", "pristine")
    return work


def bare_home(host: dict, scratch_root: Path) -> Path:
    home = Path(tempfile.mkdtemp(prefix="bench-home-", dir=scratch_root))
    dst = home / ".codex"
    dst.mkdir()
    for name in host["bare_files"]:
        shutil.copy2(host["home"] / name, dst / name)
    return home


PROMPT = ("Работай в каталоге task-orders внутри своей текущей рабочей "
          "директории. Прочитай там README.md и выполни задачу из него: "
          "найди причину бага и почини её, не нарушив ограничений из README.")


def run_unit(host_name: str, work: Path, log: Path, env_home: Path,
             timeout: int) -> None:
    host = HOSTS[host_name]
    env = dict(os.environ, HOME=str(env_home))
    p = subprocess.run(host["cmd"] + [PROMPT], cwd=work, env=env,
                       capture_output=True, text=True, timeout=timeout)
    log.write_text(p.stdout + p.stderr, encoding="utf-8")


def grade(task: str, work: Path, log: Path):
    """(passed_bool, tokens) -- the grader's exit code is the verdict."""
    grader = ROOT / "bench" / f"{task.removeprefix('task-')}-grader.py"
    cmd = [sys.executable, str(grader)]
    pristine = ROOT / "bench" / task / "app.db"
    if pristine.is_file():
        cmd.append(str(pristine))
    p = subprocess.run(cmd, cwd=work, capture_output=True, text=True)
    tokens = None
    m = re.search(r"tokens used\s*\n(\d+)", log.read_text(encoding="utf-8"))
    if m:
        tokens = int(m.group(1))
    return p.returncode == 0, tokens


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True,
                    help="каталог под bench/, например task-orders")
    ap.add_argument("--host", default="codex", choices=sorted(HOSTS))
    ap.add_argument("--arms", default="set,bare")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--timeout", type=int, default=1800,
                    help="секунд на один вызов хоста")
    ap.add_argument("--dry-run", action="store_true",
                    help="напечатать план и выйти: ничего не запускается")
    args = ap.parse_args(argv)

    fixture = ROOT / "bench" / args.task
    # graders drop the task- prefix: task-orders -> orders-grader.py
    grader = ROOT / "bench" / f"{args.task.removeprefix('task-')}-grader.py"
    if not fixture.is_dir() or not grader.is_file():
        sys.exit(f"harness: нет задачи {args.task} или её грейдера "
                 f"({grader.name})")

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arms if a not in ("set", "bare")]
    if unknown:
        sys.exit(f"harness: плечи только set|bare, а не {unknown}")
    seed = args.seed if args.seed is not None else random.randrange(2**31)
    plan = plan_arms(arms, args.repeats, seed)

    if args.dry_run:
        print(json.dumps({"task": args.task, "seed": seed, "plan": plan}))
        return 0

    results_root = ROOT / "bench" / "runs"
    results_root.mkdir(exist_ok=True)
    stamp = results_root / f"{args.task}-{seed}.json"

    units = []
    with tempfile.TemporaryDirectory(prefix="bench-run-") as tmp:
        scratch = Path(tmp)
        homes = {"set": Path.home(),
                 "bare": bare_home(HOSTS[args.host], scratch)}
        for unit in plan:
            arm = unit.split("#")[0]
            work = prepare_work(fixture, scratch, unit)
            log = scratch / f"{unit.replace('#', '-')}.log"
            print(f"[{unit}] запуск...", flush=True)
            try:
                run_unit(args.host, work, log, homes[arm], args.timeout)
            except subprocess.TimeoutExpired:
                print(f"[{unit}] таймаут {args.timeout}s")
            passed, tokens = grade(args.task, work, log)
            words = None
            if arm == "set":
                sessions = sorted((homes["set"] / ".codex" / "sessions")
                                  .rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime)[-1]
                q = subprocess.run([sys.executable, str(ROOT / "bench" / "loaded.py"),
                                    str(sessions), "--root", str(ROOT)],
                                   capture_output=True, text=True)
                m = re.search(r"слов инструкций загружено:\s*(\d+)", q.stdout)
                words = int(m.group(1)) if m else None
            print(f"[{unit}] {'PASS' if passed else 'FAIL'}"
                  f"{f', {tokens} токенов' if tokens else ''}", flush=True)
            units.append({"unit": unit, "arm": arm, "passed": passed,
                          "tokens": tokens, "loaded_words": words})

    out = {"task": args.task, "host": args.host, "seed": seed, "units": units}
    for arm in arms:
        mine = [u for u in units if u["arm"] == arm]
        n = len(mine)
        ok = sum(u["passed"] for u in mine)
        lo, hi = wilson(ok, n)
        out[arm] = {"passed": ok, "total": n,
                    "wilson": [round(lo, 3), round(hi, 3)],
                    "tokens": [u["tokens"] for u in mine if u["tokens"]]}
        print(f"{arm}: {ok}/{n} pass, wilson [{lo:.3f}, {hi:.3f}], "
              f"токены {out[arm]['tokens']}")
    stamp.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"записано: {stamp}")
    all_passed = all(u["passed"] for u in units)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
