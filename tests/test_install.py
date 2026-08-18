#!/usr/bin/env python3
"""An installer must never delete what it did not create.

Written after an external review found two unconditional deletions: a foreign
`prime-analyst.md` was unlinked, and a `prime-<name>` directory belonging to
another tool would have gone through `shutil.rmtree`.
"""
import json
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

    # a damaged marker block must stop the rewrite, not be repaired blindly
    with tempfile.TemporaryDirectory() as home:
        h = Path(home)
        (h / ".claude").mkdir(parents=True)
        (h / ".claude" / "CLAUDE.md").write_text(
            "mine\n<!-- primeskills:begin -->\nno closing marker\n", encoding="utf-8")
        (h / ".codex").mkdir()
        out = run(home, "claude", "--apply").stdout
        checks += 1
        if "markers are damaged" not in out:
            failures.append("повреждённые маркеры не остановили правку")
        checks += 1
        if "no closing marker" not in (h / ".claude" / "CLAUDE.md").read_text(encoding="utf-8"):
            failures.append("файл с повреждёнными маркерами всё-таки переписан")

    # a config is never left half-written, and a backup exists after the change
    with tempfile.TemporaryDirectory() as home:
        h = Path(home)
        (h / ".claude").mkdir(parents=True)
        (h / ".claude" / "CLAUDE.md").write_text("my own notes\n", encoding="utf-8")
        (h / ".codex").mkdir()
        run(home, "claude", "--apply")
        checks += 1
        backup = h / ".claude" / "CLAUDE.md.primeskills-backup"
        if not backup.is_file() or "my own notes" not in backup.read_text(encoding="utf-8"):
            failures.append("бэкап конфига не создан до правки")
        checks += 1
        if "my own notes" not in (h / ".claude" / "CLAUDE.md").read_text(encoding="utf-8"):
            failures.append("правка конфига затёрла чужой текст")
        checks += 1
        if list((h / ".claude").glob("*.primeskills-tmp")):
            failures.append("остался временный файл после атомарной записи")

        # uninstall follows the manifest and puts the file back to its own content
        run(home, "claude", "--uninstall", "--apply")
        checks += 1
        left = list((h / ".claude" / "skills").glob("*/SKILL.md")) if (h / ".claude" / "skills").is_dir() else []
        if left:
            failures.append(f"после uninstall осталось {len(left)} наших навыков")
        checks += 1
        manifest = h / ".primeskills" / "installed.json"
        if manifest.is_file() and json.loads(manifest.read_text(encoding="utf-8")):
            failures.append("манифест не опустел после uninstall")

    # a file the user added into our directory must survive uninstall
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp)
        (h / ".claude").mkdir()          # the installer skips a host that is not here
        run(tmp, "claude", "--apply")
        theirs = h / ".claude" / "skills" / "build" / "notes.md"
        if theirs.parent.is_dir():
            theirs.write_text("мои заметки\n", encoding="utf-8")
            out = run(tmp, "claude", "--uninstall", "--apply")
            checks += 1
            if not theirs.is_file():
                failures.append("uninstall снёс чужой файл внутри нашего каталога")
            checks += 1
            if "not ours" not in (out.stdout + out.stderr):
                failures.append("uninstall промолчал про оставленное")
            checks += 1
            if (h / ".claude" / "skills" / "verify").exists():
                failures.append("uninstall не убрал наши каталоги без чужого содержимого")

    # ownership is decided by path components, not by substring: a neighbour
    # directory whose name merely begins with ours is not ours, and the caller
    # of this check is allowed to shutil.rmtree what it owns
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader("_pi_test", str(TOOL))
    spec = importlib.util.spec_from_loader("_pi_test", loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    neighbour = str(mod.ROOT) + "-foreign"
    checks += 1
    if mod.under_root(neighbour):
        failures.append(f"{neighbour} опознан как наш каталог")
    checks += 1
    if not mod.under_root(str(mod.ROOT / "skills")):
        failures.append("собственный каталог не опознан как наш")

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
