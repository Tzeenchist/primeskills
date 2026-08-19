#!/usr/bin/env python3
"""An installer must never delete what it did not create.

Written after an external review found two unconditional deletions: a foreign
`prime-analyst.md` was unlinked, and a `prime-<name>` directory belonging to
another tool would have gone through `shutil.rmtree`.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "bin" / "primeskills-install"


def run(home, *args):
    """Installation checks are about this working copy, so they ask for it.

    Pinned is the default since 2026-08-18: a plain --apply builds a worktree
    at HEAD and installs from there, which would test the last commit instead
    of the change under test.
    """
    if "--apply" in args and "--live" not in args and "--pin" not in args:
        args = args + ("--live",)
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

    # the guards are armed by the installer, not by invoking the skill, and
    # uninstall must leave a stranger's hook and the rest of settings alone
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp)
        (h / ".claude").mkdir()
        (h / ".claude" / "settings.json").write_text(json.dumps({
            "theme": "dark",
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
                {"type": "command", "command": "python3 /home/other/guard.py"}]}]},
        }), encoding="utf-8")
        run(tmp, "claude", "--apply")
        settings = json.loads((h / ".claude" / "settings.json").read_text(encoding="utf-8"))
        armed = json.dumps(settings)
        checks += 1
        if "check-commands.py" not in armed or "check-boundary.py" not in armed:
            failures.append(f"хуки не встали при установке: {armed[:200]}")
        checks += 1
        if "/home/other/guard.py" not in armed or settings.get("theme") != "dark":
            failures.append("установка затёрла чужие настройки")

        doctor = ROOT / "bin" / "primeskills-doctor"
        env = dict(os.environ, HOME=tmp)
        checked = subprocess.run([sys.executable, str(doctor)], capture_output=True,
                                 text=True, env=env)
        checks += 1
        if "[ok  ] claude     hook armed for Bash" not in checked.stdout:
            failures.append(f"doctor не исполнил установленный command hook:\n{checked.stdout}")

        for entry in settings["hooks"]["PreToolUse"]:
            if entry.get("matcher") == "Bash":
                entry["hooks"][0]["command"] = f"python3 {ROOT / 'bin' / 'primeskills-help'}"
        (h / ".claude" / "settings.json").write_text(
            json.dumps(settings), encoding="utf-8")
        checked = subprocess.run([sys.executable, str(doctor)], capture_output=True,
                                 text=True, env=env)
        checks += 1
        if "[FAIL] claude     hook armed for Bash" not in checked.stdout:
            failures.append("doctor принял строку hook, не проверив её фактический ответ")
        (h / ".claude" / "settings.json").write_text(armed, encoding="utf-8")

        run(tmp, "claude", "--uninstall", "--apply")
        left = (h / ".claude" / "settings.json").read_text(encoding="utf-8")
        checks += 1
        if "check-commands.py" in left:
            failures.append("uninstall оставил наши хуки")
        checks += 1
        if "/home/other/guard.py" not in left or "dark" not in left:
            failures.append("uninstall снёс чужой хук или чужие настройки")

    # a pin makes the agents read a fixed commit instead of the working copy.
    # It needs ROOT to be a git repository; where it is not — an extracted copy
    # of the index, for one — the case is not applicable, and n/a is not a
    # failure (R4).
    # Against a clone, never against this repository: pinning writes worktree
    # metadata into .git, and a test that leaves traces in the tree it tests is
    # the harness tampering G8 forbids.
    in_repo = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-dir"],
                             capture_output=True).returncode == 0
    if not in_repo:
        print("пин: не применимо — ROOT не git-репозиторий")
    with tempfile.TemporaryDirectory() as tmp:
      if in_repo:
          h = Path(tmp) / "home"
          h.mkdir()
          (h / ".claude").mkdir()
          clone = Path(tmp) / "clone"
          made = subprocess.run(["git", "clone", "--quiet", "--no-hardlinks",
                                 str(ROOT), str(clone)], capture_output=True)
          if made.returncode == 0:
              # the clone carries the committed state; the test is about the
              # working tree, so the working files go over it — and are
              # committed there, because a pin checks out a commit and would
              # otherwise install the code as it was before the change
              for part in ("bin", "core", "skills", "docs", "tests"):
                  if (ROOT / part).is_dir():
                      shutil.copytree(ROOT / part, clone / part, dirs_exist_ok=True)
              subprocess.run(["git", "-C", str(clone), "-c", "user.email=t@t",
                              "-c", "user.name=t", "commit", "-qam", "рабочая копия"],
                             capture_output=True)
          if made.returncode != 0:
              print("пин: не применимо — клон не создан")
          else:
              tool = clone / "bin" / "primeskills-install"
              env = dict(os.environ, HOME=str(h))
              subprocess.run([sys.executable, str(tool), "claude", "--pin", "HEAD"],
                             capture_output=True, text=True, env=env)
              link = h / ".claude" / "skills" / "build" / "SKILL.md"
              checks += 1
              if not (link.is_symlink() and "/.primeskills/pinned/" in os.path.realpath(link)):
                  failures.append("пин не переключил ссылки на закреплённое дерево")
              checks += 1
              if not (h / ".primeskills" / "pin.json").is_file():
                  failures.append("пин не записан")
              # uncommitted work inside the pinned tree must stop the removal
              (h / ".primeskills" / "pinned" / "DIRTY.txt").write_text("моё\n",
                                                                      encoding="utf-8")
              checks += 1
              out = subprocess.run([sys.executable, str(tool), "claude", "--unpin"],
                                   capture_output=True, text=True, env=env)
              if "uncommitted work" not in (out.stdout + out.stderr):
                  failures.append("снятие пина не заметило незакоммиченную работу")
              off = subprocess.run([sys.executable, str(tool), "claude", "--unpin",
                                    "--force"], capture_output=True, text=True, env=env)
              checks += 1
              if "/.primeskills/pinned/" in os.path.realpath(link):
                  failures.append("снятие пина не вернуло ссылки на рабочую копию")
              # PS-048: the guard used to survive unpinning in two copies, and
              # the command reported success and then raised. Both were invisible
              # until someone read settings.json.
              checks += 1
              if off.returncode != 0:
                  failures.append(f"снятие пина завершилось не нулём:\n{off.stdout}{off.stderr}")
              armed = json.loads((h / ".claude" / "settings.json").read_text(encoding="utf-8"))
              cmds = [x["command"] for e in armed["hooks"]["PreToolUse"] for x in e["hooks"]]
              checks += 1
              if len(cmds) != 2 or any("/.primeskills/pinned/" in c for c in cmds):
                  failures.append(f"после снятия пина сторож остался в двух деревьях: {cmds}")
              checks += 1
              if (h / ".primeskills" / "pin.json").exists():
                  failures.append("запись пина пережила снятие")
              checks += 1
              if (h / ".primeskills" / "pinned").exists():
                  failures.append("закреплённое дерево не снято — падение унесло уборку")

    # the update path must also take back only its own links: uninstall was
    # fixed first and reinstall kept deleting whole directories
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp)
        (h / ".claude").mkdir()
        run(tmp, "claude", "--apply")
        theirs = h / ".claude" / "skills" / "verify" / "notes.md"
        if theirs.parent.is_dir():
            theirs.write_text("моё\n", encoding="utf-8")
            run(tmp, "claude", "--apply")
            checks += 1
            if not theirs.is_file():
                failures.append("повторная установка снесла чужой файл")

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
