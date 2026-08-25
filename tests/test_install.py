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

    # the collision that ended: ours under `prime-<name>` while the plain name
    # came free. Two names for one skill is a host-visible defect -- the skill
    # is offered twice -- and it made the doctor's count read full while a
    # skill was missing (2026-08-21, `prime-autoplan`).
    with tempfile.TemporaryDirectory() as home:
        h = Path(home)
        skills = h / ".claude" / "skills"
        foreign = skills / "autoplan"
        foreign.mkdir(parents=True)
        (foreign / "SKILL.md").write_text("someone else's autoplan\n", encoding="utf-8")
        (h / ".codex").mkdir(exist_ok=True)

        run(home, "--apply")
        checks += 1
        if not (skills / "prime-autoplan").exists():
            failures.append("коллизия: наш autoplan не встал под префиксным именем")

        # the squatter leaves; the next install must take the plain name and
        # take back what it left under the prefix
        shutil.rmtree(foreign)
        out = run(home, "--apply").stdout

        checks += 1
        if not (skills / "autoplan" / "SKILL.md").exists():
            failures.append("плоское имя освободилось, а навык под него не встал")
        checks += 1
        if (skills / "prime-autoplan").exists():
            failures.append("префиксная копия осталась: хост увидит навык дважды")
        checks += 1
        if "stale copy removed: prime-autoplan" not in out:
            failures.append(f"про снятую копию не сказано в отчёте:\n{out}")

        # the doctor names what is missing instead of printing a bare count
        doctor = ROOT / "bin" / "primeskills-doctor"
        (skills / "handoff").exists() and shutil.rmtree(skills / "handoff")
        told = subprocess.run([sys.executable, str(doctor)], capture_output=True,
                              text=True, env=dict(os.environ, HOME=home)).stdout
        checks += 1
        if "missing: handoff" not in told:
            failures.append(f"доктор не назвал отсутствующий навык:\n{told}")

    # the same installation, read from another tree. `--apply` builds a pinned
    # worktree and runs from there, so everything installed live led out of the
    # tree it was reading -- and 27 skills got a second copy under prime-<name>
    # in three agents (2026-08-21). The manifest is what tells ours from a
    # stranger's when the paths differ.
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as other:
        h = Path(home)
        skills = h / ".claude" / "skills"
        skills.mkdir(parents=True)
        (h / ".codex").mkdir(exist_ok=True)

        elsewhere = Path(other) / "skills" / "verify"
        elsewhere.mkdir(parents=True)
        (elsewhere / "SKILL.md").write_text("verify, installed from another tree\n",
                                            encoding="utf-8")
        dest = skills / "verify"
        dest.mkdir()
        (dest / "SKILL.md").symlink_to(elsewhere / "SKILL.md")
        record = h / ".primeskills" / "installed.json"
        record.parent.mkdir(parents=True)
        record.write_text(json.dumps({str(dest): str(elsewhere)}), encoding="utf-8")

        run(home, "--apply")
        checks += 1
        if (skills / "prime-verify").exists():
            failures.append("своя установка из другого дерева продублирована под префиксом")
        checks += 1
        if os.path.realpath(dest / "SKILL.md") != str(ROOT / "skills" / "verify" / "SKILL.md"):
            failures.append("своя прежняя установка не обновлена на месте")

    # the record only covers what still points where it was recorded to point
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as other:
        h = Path(home)
        skills = h / ".claude" / "skills"
        skills.mkdir(parents=True)
        (h / ".codex").mkdir(exist_ok=True)
        taken = skills / "verify"
        taken.mkdir()
        (taken / "SKILL.md").write_text("someone else took this name since\n",
                                        encoding="utf-8")
        record = h / ".primeskills" / "installed.json"
        record.parent.mkdir(parents=True)
        record.write_text(json.dumps({str(taken): str(Path(other) / "skills" / "verify")}),
                          encoding="utf-8")
        run(home, "--apply")
        checks += 1
        if "someone else took this name" not in (taken / "SKILL.md").read_text(encoding="utf-8"):
            failures.append("запись манифеста дала снести чужой каталог под тем же именем")

    # the doctor asks the same question and must get the same answer. Run from
    # the working copy against an installation made from another tree, it said
    # "none found" for all three agents -- a correct pinned installation
    # reported as missing (2026-08-21, the third copy of this rule).
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as other:
        h = Path(home)
        skills = h / ".claude" / "skills"
        skills.mkdir(parents=True)
        elsewhere = Path(other) / "skills" / "verify"
        elsewhere.mkdir(parents=True)
        (elsewhere / "SKILL.md").write_text("verify, from another tree\n", encoding="utf-8")
        dest = skills / "verify"
        dest.mkdir()
        (dest / "SKILL.md").symlink_to(elsewhere / "SKILL.md")
        record = h / ".primeskills" / "installed.json"
        record.parent.mkdir(parents=True)
        record.write_text(json.dumps({str(dest): str(elsewhere)}), encoding="utf-8")

        doctor = ROOT / "bin" / "primeskills-doctor"
        told = subprocess.run([sys.executable, str(doctor)], capture_output=True,
                              text=True, env=dict(os.environ, HOME=home)).stdout
        want = len(list(ROOT.glob("skills/*/SKILL.md")))
        # only claude has anything installed in this HOME; the other two are
        # legitimately empty, and "none found" there is the right answer
        said = next((l for l in told.splitlines()
                     if "claude" in l and "skills linked" in l), "")
        checks += 1
        if "none found" in said:
            failures.append(f"доктор не узнал установку из другого дерева:\n{told}")
        checks += 1
        if f"1 of {want}" not in said:
            failures.append(f"доктор не засчитал узнанный навык:\n{told}")

    # a foreign directory under the prefix is still not ours to clear
    with tempfile.TemporaryDirectory() as home:
        h = Path(home)
        skills = h / ".claude" / "skills"
        squat = skills / "prime-autoplan"
        squat.mkdir(parents=True)
        (squat / "SKILL.md").write_text("someone else's skill\n", encoding="utf-8")
        (h / ".codex").mkdir(exist_ok=True)
        run(home, "--apply")
        checks += 1
        if "someone else's skill" not in (squat / "SKILL.md").read_text(encoding="utf-8"):
            failures.append("чужой prime-autoplan снесён как устаревшая копия")

    # cline discovers ~/.cline/skills and reads the cross-tool AGENTS.md.
    # Same shape as codex: one symlink per skill, core reachable through a
    # managed block with exact markers. The file at ~/.agents/AGENTS.md is
    # shared with every other tool speaking the agents.md standard, so
    # uninstall must take back our block and nothing else.
    with tempfile.TemporaryDirectory() as home:
        h = Path(home)
        (h / ".cline").mkdir()
        out = run(home, "--apply")
        skills = h / ".cline" / "skills"
        want = len(list(ROOT.glob("skills/*/SKILL.md")))
        linked = list(skills.glob("*")) if skills.is_dir() else []
        checks += 1
        if len(linked) < want:
            failures.append(f"cline: слинковано {len(linked)} из {want} навыков")
        agents = h / ".agents" / "AGENTS.md"
        text = agents.read_text(encoding="utf-8") if agents.is_file() else ""
        checks += 1
        if ("<!-- primeskills:begin -->" not in text
                or "core/PRINCIPLES.md" not in text):
            failures.append("cline: указателя на core нет в ~/.agents/AGENTS.md")
        run(home, "--apply", "--uninstall", "cline")
        checks += 1
        if agents.is_file() and "primeskills:begin" in agents.read_text(encoding="utf-8"):
            failures.append("cline: uninstall не снял блок из ~/.agents/AGENTS.md")

    # kilo is an OpenCode fork: skills under its config dir, core through the
    # `instructions` field, prime-analyst in agent/. Two things are its own.
    # It accepts four config names and reads the one that exists, so the
    # installer must write into that one rather than create a canonical
    # `kilo.json` the host may load second or not at all. And a `.jsonc` may
    # carry comments: unreadable JSON is reported, never rewritten.
    with tempfile.TemporaryDirectory() as home:
        h = Path(home)
        cfg = h / ".config" / "kilo" / "kilo.jsonc"
        cfg.parent.mkdir(parents=True)
        cfg.write_text('{"$schema": "https://app.kilo.ai/config.json"}\n', encoding="utf-8")
        run(home, "--apply")

        skills = h / ".config" / "kilo" / "skills"
        want = len(list(ROOT.glob("skills/*/SKILL.md")))
        linked = list(skills.glob("*")) if skills.is_dir() else []
        checks += 1
        if len(linked) < want:
            failures.append(f"kilo: слинковано {len(linked)} из {want} навыков")

        checks += 1
        if (h / ".config" / "kilo" / "kilo.json").exists():
            failures.append("kilo: создан kilo.json рядом с живым kilo.jsonc")

        data = json.loads(cfg.read_text(encoding="utf-8"))
        checks += 1
        if not any("core/PRINCIPLES.md" in i for i in data.get("instructions", [])):
            failures.append("kilo: core не попал в instructions живого конфига")
        checks += 1
        if data.get("$schema") != "https://app.kilo.ai/config.json":
            failures.append("kilo: чужие ключи конфига потеряны при записи")

        prof = h / ".config" / "kilo" / "agent" / "prime-analyst.md"
        checks += 1
        if not prof.is_symlink():
            failures.append("kilo: профиль prime-analyst не слинкован в agent/")

        run(home, "--apply", "--uninstall", "kilo")
        data = json.loads(cfg.read_text(encoding="utf-8"))
        checks += 1
        if any("primeskills" in i for i in data.get("instructions", [])):
            failures.append("kilo: uninstall не убрал core из instructions")

    # a config with comments is valid JSONC and unreadable as JSON: rewriting
    # it would delete the user's own notes, so the installer says so and stops
    with tempfile.TemporaryDirectory() as home:
        h = Path(home)
        cfg = h / ".config" / "kilo" / "kilo.jsonc"
        cfg.parent.mkdir(parents=True)
        before = '// my notes\n{"$schema": "https://app.kilo.ai/config.json"}\n'
        cfg.write_text(before, encoding="utf-8")
        out = run(home, "--apply").stdout
        checks += 1
        if cfg.read_text(encoding="utf-8") != before:
            failures.append("kilo: конфиг с комментариями переписан")
        checks += 1
        if "not valid JSON" not in out:
            failures.append("kilo: про нечитаемый конфиг ничего не сказано")

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
    # the harness tampering G7 forbids.
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

    # PS-053. A dry run described writes it never made: three status lines were
    # built from `remove`/`present` alone and never consulted `apply_it`, so
    # `primeskills-install kilo` printed "core added to instructions" beside
    # "would link 29 skills" -- one run, one output block, two tenses. The
    # last check here is the one that matters: it asks the filesystem whether
    # the dry run stayed dry, not the wording whether it claims it did.
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp)

        # config branch: a config must exist, or bootstrap() returns
        # "no config, skipped" and never reaches the line under test
        kilo_cfg = h / ".config" / "kilo" / "kilo.json"
        kilo_cfg.parent.mkdir(parents=True)
        kilo_cfg.write_text("{}\n", encoding="utf-8")
        # a host whose directory is absent is skipped before the line under
        # test is ever reached (bin/primeskills-install:772)
        (h / ".claude").mkdir()
        (h / ".config" / "opencode").mkdir(parents=True)

        dry = run(tmp, "kilo").stdout
        checks += 1
        if "core added to instructions" in dry:
            failures.append("сухой ход отчитался о записи core в instructions")
        checks += 1
        if "core would be added to instructions" not in dry:
            failures.append(f"сухой ход не сказал would про instructions:\n{dry}")
        checks += 1
        if json.loads(kilo_cfg.read_text(encoding="utf-8")) != {}:
            failures.append("сухой ход всё-таки записал конфиг")

        # always-loaded branch
        dry = run(tmp, "claude").stdout
        checks += 1
        if "core pointer added to CLAUDE.md" in dry:
            failures.append("сухой ход отчитался о записи указателя core")
        checks += 1
        if "core pointer would be added to CLAUDE.md" not in dry:
            failures.append(f"сухой ход не сказал would про указатель:\n{dry}")

        # profile branch
        dry = run(tmp, "opencode").stdout
        checks += 1
        if "prime-analyst linked into" in dry:
            failures.append("сухой ход отчитался о создании профиля")
        checks += 1
        if "prime-analyst would be linked into" not in dry:
            failures.append(f"сухой ход не сказал would про профиль:\n{dry}")

        # removal is dry too
        dry = run(tmp, "kilo", "--uninstall").stdout
        checks += 1
        if "core removed from instructions" in dry:
            failures.append("сухое удаление отчиталось о снятии core")
        checks += 1
        if "core would be removed from instructions" not in dry:
            failures.append(f"сухое удаление не сказало would:\n{dry}")

        checks += 1
        # "would remove 29 skills" contains "remove 29 skills", so the bare
        # verb has to be anchored to where the line actually starts it
        if ": remove 29 skills" in dry:
            failures.append(f"сухое удаление отчиталось о снятии скиллов:\n{dry}")
        checks += 1
        if "would remove 29 skills" not in dry:
            failures.append(f"сухое удаление не сказало would про скиллы:\n{dry}")

        # the point of all of the above: nothing was created
        checks += 1
        stray = [p for p in ((h / ".config" / "opencode" / "agents" / "prime-analyst.md"),
                             (h / ".claude" / "CLAUDE.md"))
                 if p.exists()]
        if stray:
            failures.append(f"сухой ход создал файлы: {stray}")

    # and the wording survives a real run: --apply still speaks in the past
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp)
        kilo_cfg = h / ".config" / "kilo" / "kilo.json"
        kilo_cfg.parent.mkdir(parents=True)
        kilo_cfg.write_text("{}\n", encoding="utf-8")
        wet = run(tmp, "kilo", "--apply").stdout
        checks += 1
        if "core added to instructions" not in wet:
            failures.append(f"боевой прогон потерял прежнюю строку:\n{wet}")
        checks += 1
        if "would" in wet:
            failures.append(f"боевой прогон заговорил сослагательно:\n{wet}")

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
