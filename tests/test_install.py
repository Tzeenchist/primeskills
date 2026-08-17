#!/usr/bin/env python3
"""An installer must never delete what it did not create.

Written after an external review found two unconditional deletions: a foreign
`prime-analyst.md` was unlinked, and a `prime-<name>` directory belonging to
another tool would have gone through `shutil.rmtree`.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "bin" / "primeskills-install"


def run(home, *args):
    env = dict(os.environ, HOME=home)
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, env=env)


def main():
    failures, checks = [], 0

    with tempfile.TemporaryDirectory() as home:
        h = Path(home)
        # a foreign profile and a foreign skill directory, both squatting on
        # names the installer wants
        prof = h / ".config" / "opencode" / "agents" / "prime-analyst.md"
        prof.parent.mkdir(parents=True)
        prof.write_text("someone else's profile\n", encoding="utf-8")

        # the prefix only kicks in on a first collision, so squat on both names:
        # `autoplan` forces the rename, `prime-autoplan` is what the rename hits
        first = h / ".claude" / "skills" / "autoplan"
        first.mkdir(parents=True)
        (first / "SKILL.md").write_text("someone else's autoplan\n", encoding="utf-8")
        squat = h / ".claude" / "skills" / "prime-autoplan"
        squat.mkdir(parents=True)
        (squat / "SKILL.md").write_text("someone else's skill\n", encoding="utf-8")
        (h / ".codex").mkdir(exist_ok=True)

        out = run(home, "--apply").stdout

        checks += 1
        if not prof.is_file() or "someone else" not in prof.read_text(encoding="utf-8"):
            failures.append("чужой prime-analyst.md удалён или перезаписан")
        checks += 1
        if "not ours, left alone" not in out:
            failures.append("про чужой профиль не сказано в отчёте")

        checks += 1
        if "someone else's skill" not in (squat / "SKILL.md").read_text(encoding="utf-8"):
            failures.append("чужой каталог prime-autoplan затёрт")
        checks += 1
        if "someone else's autoplan" not in (first / "SKILL.md").read_text(encoding="utf-8"):
            failures.append("чужой каталог autoplan затёрт")
        checks += 1
        if "LEFT ALONE" not in out:
            failures.append("про чужой каталог не сказано в отчёте")

        # and it still installs everything it legitimately can
        checks += 1
        linked = list((h / ".claude" / "skills").glob("*/SKILL.md"))
        if len(linked) < 20:
            failures.append(f"установлено слишком мало навыков: {len(linked)}")

        # uninstall removes only ours
        run(home, "--uninstall", "--apply")
        checks += 1
        if not prof.is_file():
            failures.append("uninstall удалил чужой профиль")
        checks += 1
        if not (squat / "SKILL.md").is_file() or not (first / "SKILL.md").is_file():
            failures.append("uninstall удалил чужой каталог")

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
