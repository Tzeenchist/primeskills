#!/usr/bin/env python3
"""The floor guard names a lowered bar in the diff, and says when it could not look.

PS-097: G7 forbids making a build green by editing tests or thresholds, and on
the projects the set works in that rule was text. The guard reads the diff
from the merge base to the working tree, untracked files included, and reports
each added line that lowers the bar. Exit 0 clean, 1 found, 2 could not check
-- and a 2 must never read like a 0.

Every case runs in a scratch repository under a scratch HOME.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLOOR = ROOT / "bin" / "primeskills-floor"
CLEAN_WORD = "проверено"


def env_for(home):
    return dict(os.environ, HOME=str(home), GIT_CONFIG_NOSYSTEM="1",
                GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def sh(args, cwd, env):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)


def floor(cwd, env, *args):
    return sh([sys.executable, str(FLOOR), *args], cwd, env)


def write(work, name, text):
    p = work / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def repo(base, env, name="work"):
    """A repository on `main` with one test file, and a branch `feature` off it."""
    work = base / name
    sh(["git", "init", "-q", "-b", "main", str(work)], base, env)
    write(work, "tests/test_price.py",
          "def test_price():\n    assert 1 + 1 == 2\n")
    sh(["git", "add", "tests/test_price.py"], work, env)
    sh(["git", "commit", "-q", "-m", "start"], work, env)
    sh(["git", "switch", "-q", "-c", "feature"], work, env)
    return work


def main():
    failures, checks = [], 0

    def expect(label, r, code, must=(), must_not=()):
        nonlocal checks
        checks += 1
        out = r.stdout + r.stderr
        if r.returncode != code:
            failures.append(f"{label}: exit {r.returncode}, expected {code}: {out[-300:]!r}")
            return
        for s in must:
            checks += 1
            if s not in out:
                failures.append(f"{label}: {s!r} missing from {out[-300:]!r}")
        for s in must_not:
            checks += 1
            if s in out:
                failures.append(f"{label}: {s!r} must not appear: {out[-300:]!r}")

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        home = base / "home"
        home.mkdir()
        env = env_for(home)

        # 1: nothing changed -- clean, and it says how much it looked at
        work = repo(base, env, "empty")
        expect("empty diff", floor(work, env, "--base", "main"), 0,
               must=(f"{CLEAN_WORD}: 0",))

        # 1: an ordinary change -- clean, one file looked at
        work = repo(base, env, "plain")
        write(work, "price.py", "def price(total):\n    return total\n")
        sh(["git", "add", "price.py"], work, env)
        sh(["git", "commit", "-q", "-m", "plain"], work, env)
        expect("plain change", floor(work, env, "--base", "main"), 0,
               must=(f"{CLEAN_WORD}: 1",))

        # 2a: a committed skip decorator -- found, by path, line and rule only
        work = repo(base, env, "skip")
        write(work, "tests/test_price.py",
              "import pytest\n\n@pytest.mark.skip(reason='SECRET-ish text')\n"
              "def test_price():\n    assert 1 + 1 == 2\n")
        sh(["git", "commit", "-qam", "skip"], work, env)
        expect("committed skip", floor(work, env, "--base", "main"), 1,
               must=("tests/test_price.py:3 skip",),
               must_not=("SECRET-ish", CLEAN_WORD))

        # 2a: every spelling of a skip is a skip
        for i, line in enumerate(("@pytest.mark.skipif(True, reason='x')",
                                  "@pytest.mark.xfail",
                                  "@unittest.skip('x')",
                                  "@unittest.skipUnless(False, 'x')",
                                  "    self.skipTest('x')",
                                  "    pytest.skip('x')")):
            work = repo(base, env, f"spell{i}")
            write(work, "tests/test_price.py",
                  f"{line}\ndef test_price():\n    assert 1 + 1 == 2\n")
            sh(["git", "commit", "-qam", "skip"], work, env)
            expect(f"spelling {line.strip()}", floor(work, env, "--base", "main"), 1,
                   must=("tests/test_price.py:1 skip",))

        # 2a: a skip spelled inside a string is data, not a skip
        work = repo(base, env, "literal")
        write(work, "tests/test_price.py",
              "FIXTURE = \"@pytest.mark.skip\\ndef test_x(): pass\"\n"
              "MSG = 'call pytest.skip(reason) to skip'\n"
              "def test_price():\n    assert 1 + 1 == 2\n")
        sh(["git", "commit", "-qam", "literal"], work, env)
        expect("skip inside a string", floor(work, env, "--base", "main"), 0)

        # 3 (cheap here): removing a skip lowers nothing
        work = repo(base, env, "unskip")
        sh(["git", "switch", "-q", "main"], work, env)
        write(work, "tests/test_price.py",
              "import pytest\n@pytest.mark.skip\ndef test_price():\n    assert True\n")
        sh(["git", "commit", "-qam", "skipped on main"], work, env)
        sh(["git", "switch", "-q", "-C", "feature"], work, env)
        write(work, "tests/test_price.py",
              "def test_price():\n    assert True\n")
        sh(["git", "commit", "-qam", "unskip"], work, env)
        expect("removed skip", floor(work, env, "--base", "main"), 0)

        # 4: staged, unstaged and untracked work all count
        work = repo(base, env, "staged")
        write(work, "tests/test_price.py",
              "import pytest\n@pytest.mark.xfail\ndef test_price():\n    assert True\n")
        sh(["git", "add", "tests/test_price.py"], work, env)
        expect("staged skip", floor(work, env, "--base", "main"), 1,
               must=("tests/test_price.py:2 skip",))

        work = repo(base, env, "unstaged")
        write(work, "tests/test_price.py",
              "def test_price():\n    pytest.skip('later')\n")
        expect("unstaged skip", floor(work, env, "--base", "main"), 1,
               must=("tests/test_price.py:2 skip",))

        work = repo(base, env, "untracked")
        write(work, "tests/test_new.py",
              "import pytest\n\n\n@pytest.mark.skip\ndef test_new():\n    assert True\n")
        expect("untracked skip", floor(work, env, "--base", "main"), 1,
               must=("tests/test_new.py:4 skip",))

        def case(name, files, main_files=None, commit=True):
            """A repo whose main carries main_files, and feature changes files."""
            work = repo(base, env, name)
            if main_files:
                sh(["git", "switch", "-q", "main"], work, env)
                for n, text in main_files.items():
                    write(work, n, text)
                    sh(["git", "add", n], work, env)
                sh(["git", "commit", "-q", "-m", "main"], work, env)
                sh(["git", "switch", "-q", "-C", "feature"], work, env)
            for n, text in files.items():
                if text is None:
                    sh(["git", "rm", "-q", n], work, env)
                else:
                    write(work, n, text)
                    sh(["git", "add", n], work, env)
            if commit:
                sh(["git", "commit", "-q", "-m", "change"], work, env)
            return floor(work, env, "--base", "main")

        # 2b: a deleted test file; a renamed one is not deleted
        expect("deleted test file", case("deleted", {"tests/test_price.py": None}), 1,
               must=("tests/test_price.py:- test-deleted",))
        work = repo(base, env, "renamed")
        sh(["git", "mv", "tests/test_price.py", "tests/test_cost.py"], work, env)
        sh(["git", "commit", "-q", "-m", "rename"], work, env)
        expect("renamed test file", floor(work, env, "--base", "main"), 0)

        # 2c: fewer assertions in a test file that stayed
        two = ("class T:\n    def test_a(self):\n        assert 1\n"
               "        self.assertEqual(1, 1)\n")
        one = "class T:\n    def test_a(self):\n        assert 1\n"
        expect("assertion removed", case("fewer", {"tests/test_t.py": one},
                                         main_files={"tests/test_t.py": two}), 1,
               must=("tests/test_t.py:- fewer-asserts 2→1",))
        expect("assertion added", case("more", {"tests/test_t.py": two},
                                       main_files={"tests/test_t.py": one}), 0)

        # 2d: new bare suppressions, as comments only (owner, 2026-10-03: one
        # with an error code is narrow and deliberate -- 44 of 46 findings on
        # four projects were those, and a reason asked 44 times is a ritual)
        for i, c in enumerate(("# noqa", "# type: ignore", "# pragma: no cover")):
            expect(f"suppression {c}",
                   case(f"supp{i}", {"price.py": f"x = 1\ny = 2  {c}\n"}), 1,
                   must=("price.py:2 suppression",))
        for i, c in enumerate(("# noqa: E501", "# noqa:F401", "# type: ignore[attr-defined]")):
            expect(f"coded suppression {c}",
                   case(f"coded{i}", {"price.py": f"x = 1\ny = 2  {c}\n"}), 0)
        expect("suppression inside a string",
               case("suppstr", {"price.py": "HELP = 'add # noqa to silence'\n"}), 0)
        expect("suppression removed",
               case("suppgone", {"price.py": "y = 2\n"},
                    main_files={"price.py": "y = 2  # noqa\n"}), 0)

        # 2e: a lowered or removed coverage floor; a raised one is silent
        cfg = "[tool.coverage.report]\nfail_under = {}\n"
        expect("threshold lowered",
               case("lower", {"pyproject.toml": cfg.format(50)},
                    main_files={"pyproject.toml": cfg.format(60)}), 1,
               must=("pyproject.toml:2 threshold 60→50",))
        expect("threshold raised",
               case("raise", {"pyproject.toml": cfg.format(70)},
                    main_files={"pyproject.toml": cfg.format(60)}), 0)
        expect("threshold removed",
               case("dropped", {"pyproject.toml": "[tool.coverage.report]\n"},
                    main_files={"pyproject.toml": cfg.format(60)}), 1,
               must=("pyproject.toml:- threshold 60→нет",))
        expect("cov-fail-under lowered",
               case("covflag", {"pytest.ini": "[pytest]\naddopts = --cov-fail-under=70\n"},
                    main_files={"pytest.ini": "[pytest]\naddopts = --cov-fail-under=80\n"}), 1,
               must=("pytest.ini:2 threshold 80→70",))

        # 6: a threshold it cannot read is named, not skipped
        expect("unknown threshold format",
               case("unknown", {"setup.cfg": "[coverage:report]\nfail_under = ${MIN}\n"},
                    main_files={"setup.cfg": "[coverage:report]\nfail_under = 60\n"}), 1,
               must=("setup.cfg:2 не знаю этот формат",))

        # 2f: CI that stops failing
        wf = ".github/workflows/gate.yml"
        expect("or-true in CI",
               case("ortrue", {wf: "jobs:\n  t:\n    steps:\n      - run: pytest || true\n"}), 1,
               must=(f"{wf}:4 ci-silenced",))
        expect("continue-on-error in CI",
               case("coe", {wf: "jobs:\n  t:\n    continue-on-error: true\n"}), 1,
               must=(f"{wf}:3 ci-silenced",))

        # 2g: a stub where code was; abstract methods in tests are not the case
        expect("stub in code",
               case("stub", {"price.py": "def price(t):\n    raise NotImplementedError\n"}), 1,
               must=("price.py:2 stub",))
        expect("stub in a test helper",
               case("stubtest", {"tests/helpers.py": "def f():\n    raise NotImplementedError\n"}), 0)

        # JS is out of scope in this version, and the output says so
        expect("js not looked at",
               case("js", {"app.test.js": "it.skip('x', () => {})\n"}), 0,
               must=("JS не смотрю",))

        # a user's git config must not change what is read: noprefix strips the
        # a/ b/ the parser expects, and quotePath quotes a non-ASCII name
        work = repo(base, env, "noprefix")
        sh(["git", "config", "diff.noprefix", "true"], work, env)
        write(work, "tests/test_price.py",
              "import pytest\n@pytest.mark.skip\ndef test_price():\n    assert 1\n")
        sh(["git", "commit", "-qam", "skip"], work, env)
        expect("diff.noprefix", floor(work, env, "--base", "main"), 1,
               must=("tests/test_price.py:2 skip",))
        expect("non-ascii name",
               case("unicode", {"tests/test_цена.py": "x = 1  # noqa\n"}), 1,
               must=("tests/test_цена.py:1 suppression",))

        # 5: could not check -- exit 2 with the reason, never the clean word
        nogit = base / "nogit"
        nogit.mkdir()
        expect("not a repository", floor(nogit, env, "--base", "main"), 2,
               must=("не git",), must_not=(CLEAN_WORD,))

        work = repo(base, env, "nobase")
        expect("base does not exist", floor(work, env, "--base", "nope"), 2,
               must=("нет базы",), must_not=(CLEAN_WORD,))

        work = repo(base, env, "unrelated")
        sh(["git", "switch", "-q", "--orphan", "other"], work, env)
        write(work, "x.py", "x = 1\n")
        sh(["git", "add", "x.py"], work, env)
        sh(["git", "commit", "-q", "-m", "orphan"], work, env)
        expect("no merge base", floor(work, env, "--base", "main"), 2,
               must=("нет merge-base",), must_not=(CLEAN_WORD,))

        work = repo(base, env, "default")
        expect("no --base and no origin", floor(work, env), 2,
               must=("нет базы",), must_not=(CLEAN_WORD,))

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
