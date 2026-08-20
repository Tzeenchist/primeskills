#!/usr/bin/env python3
"""How many words of instruction a session actually loaded.

The 9,3–14,8× in RESULT.md compares our budgets — a ceiling the linter
enforces — against what gstack's files weigh on disk. Neither side is what a
session pays: a set is only as heavy as the part of it that gets read. Both
external reviews said so, and PS-041 п.12 asks for the fact instead.

This reads a transcript in any of the four agent formats (the loaders come from
`bin/primeskills-adherence`, so a fix there is a fix here) and sums the words of
every instruction file the session opened.

    bench/loaded.py <session> --root <path to a set> [--root ...]

A file counts once, whole, on first read. Whole is an over-count: `sed -n
'1,40p'` pays for forty lines, not for the file. It is the same over-count on
both sides, and stating it is cheaper than a range parser that would have its
own edge cases.
"""
import argparse
import importlib.machinery
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def reader():
    """The transcript loaders, borrowed rather than copied."""
    path = ROOT / "bin" / "primeskills-adherence"
    loader = importlib.machinery.SourceFileLoader("_adherence", str(path))
    spec = importlib.util.spec_from_loader("_adherence", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


# A path as it appears in a Read argument or inside a shell command.
PATH_IN_TEXT = re.compile(r"[\w./~-]*/[\w./-]+\.md\b")


def candidates(c):
    """Every file path this call could have read."""
    found = set()
    if c["path"]:
        found.add(c["path"])
    for text in (c["cmd"], c["path"]):
        found.update(PATH_IN_TEXT.findall(text or ""))
    return found


def loaded(calls, roots):
    """First read of each instruction file, in order, with its weight."""
    seen, out = set(), []
    for c in calls:
        for raw in sorted(candidates(c)):
            try:
                path = Path(raw).expanduser().resolve()
            except (OSError, ValueError, RuntimeError):
                continue
            if path in seen or not path.is_file():
                continue
            if not any(path == r or r in path.parents for r in roots):
                continue
            seen.add(path)
            words = len(path.read_text(encoding="utf-8", errors="ignore").split())
            out.append((c["n"], path, words))
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--root", action="append", required=True,
                    help="каталог набора инструкций; можно повторять")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    roots = [Path(r).expanduser().resolve() for r in args.root]
    missing = [r for r in roots if not r.is_dir()]
    if missing:
        sys.exit(f"bench/loaded.py: нет такого каталога: {missing[0]}")

    module = reader()
    calls = module.load_calls(Path(args.session))
    rows = loaded(calls, roots)

    if not args.quiet:
        for n, path, words in rows:
            print(f"  #{n:<4} {words:>6}  {path}")
    total = sum(w for _n, _p, w in rows)
    print(f"вызовов инструментов: {len(calls)}   файлов набора прочитано: {len(rows)}")
    print(f"слов инструкций загружено: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
