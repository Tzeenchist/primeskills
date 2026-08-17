#!/usr/bin/env python3
"""The run record must survive the thing it exists to survive: a lost session.

Every check here runs the tool as a fresh process against a scratch repository,
because that is the failure being fixed — state that only existed while one
agent was still running.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / "bin" / "primeskills-run"


def run(repo, *args):
    p = subprocess.run([sys.executable, str(RUN), *args],
                       capture_output=True, text=True, cwd=repo)
    return p.returncode, p.stdout + p.stderr


def main():
    failures = []
    checks = 0
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "work"], cwd=repo, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-q", "--allow-empty", "-m", "init"],
                       cwd=repo, check=True)

        code, out = run(repo, "start")
        checks += 1
        record = repo / ".primeskills" / "run" / "work.md"
        if code != 0 or not record.is_file():
            failures.append(f"start: exit {code}, no record at {record}\n{out}")

        checks += 1
        run(repo, "note", "verify", "pytest -q: 12 passed, exit 0")
        if "12 passed" not in record.read_text(encoding="utf-8"):
            failures.append("note: the line is not in the record")

        # G9: the counter belongs to the file, so a new process keeps counting
        for expected in (1, 2):
            code, out = run(repo, "fail", "flaky export")
            checks += 1
            if code != 0 or f"{expected} of 3" not in out:
                failures.append(f"fail #{expected}: exit {code}, said {out.strip()!r}")
        code, out = run(repo, "fail", "flaky export")
        checks += 1
        if code != 3:
            failures.append(f"fail #3: exit {code}, expected 3 (breaker)")

        # a different problem counts separately — G9 is per problem
        code, out = run(repo, "fail", "slow query")
        checks += 1
        if code != 0 or "1 of 3" not in out:
            failures.append(f"second problem shares a counter: {out.strip()!r}")

        checks += 1
        run(repo, "clear", "flaky export")
        code, out = run(repo, "fail", "flaky export")
        if "1 of 3" not in out:
            failures.append(f"clear: counter not reset, said {out.strip()!r}")

        # the log is append-only: clearing a counter keeps the history
        checks += 1
        text = record.read_text(encoding="utf-8")
        if text.count("**attempt") < 4 or "12 passed" not in text:
            failures.append("clear or fail rewrote the log instead of appending")

        # a branch with a slash must not become a directory
        subprocess.run(["git", "checkout", "-q", "-b", "feat/thing"], cwd=repo, check=True)
        checks += 1
        code, out = run(repo, "start")
        if code != 0 or not (repo / ".primeskills" / "run" / "feat-thing.md").is_file():
            failures.append(f"branch with a slash: exit {code}\n{out}")

    # outside a repository it must refuse, not write somewhere surprising
    with tempfile.TemporaryDirectory() as bare:
        checks += 1
        code, out = run(bare, "start")
        if code == 0:
            failures.append("start outside a git repository did not fail")

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
