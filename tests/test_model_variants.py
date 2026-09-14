#!/usr/bin/env python3
"""Model-specific instructions stay explicit, scoped, and measurable."""
import importlib.machinery
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    path = ROOT / "bin" / name
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def lint(path):
    return subprocess.run(
        [sys.executable, str(ROOT / "bin" / "primeskills-lint"), str(path)],
        capture_output=True, text=True,
    )


def fixture(tmp, model_ref, astra_words=2):
    root = Path(tmp)
    shutil.copytree(ROOT / "tests" / "fixtures" / "ok", root / "skills")
    shutil.copytree(ROOT / "core", root / "core")
    (root / "core" / "ASTRA.md").write_text(
        ("instruction " * astra_words).strip() + "\n", encoding="utf-8")
    (root / "core" / "OTHER.md").write_text("other instructions\n", encoding="utf-8")
    skill = root / "skills" / "verify" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    skill.write_text(text.replace("role: write\n", "role: write\n" + model_ref),
                     encoding="utf-8")
    return root / "skills"


def main():
    failures, checks = [], 0
    install = load("primeskills-install")
    status = load("primeskills-status")

    common = install.bootstrap_text("claude")
    codex = install.bootstrap_text("codex")
    checks += 1
    if common != install.bootstrap_text("kimi") or "ASTRA.md" in common:
        failures.append("Astra overlay changed a non-Codex bootstrap")
    checks += 1
    if codex != common or "ASTRA.md" in codex or "model_refs" in codex:
        failures.append("Codex bootstrap asks the model to route its own overlay")

    for name, phrase in (
        ("brief", "unresolved product choices"),
        ("build", "narrowest relevant baseline"),
        ("verify", "affected checks first"),
    ):
        checks += 1
        skill = (install.ROOT / "skills" / name / "SKILL.md").read_text(
            encoding="utf-8")
        if "model_refs:" in skill or phrase not in skill:
            failures.append(f"{name} does not carry the common Astra-safe rule")

    paths = status.call_paths()
    checks += 1
    if 4517 - paths.get("common", 4600) < 25:
        failures.append(f"common path was not shortened by 25 words: {paths}")
    checks += 1
    if any(4600 - words < 25 for words in paths.values()):
        failures.append(f"a model path has less than 25 words headroom: {paths}")

    valid = ("model_refs:\n"
             "  - model: gpt-6-astra\n"
             "    path: ../../core/ASTRA.md\n")
    with tempfile.TemporaryDirectory() as tmp:
        result = lint(fixture(tmp, valid))
        checks += 1
        if result.returncode or "0 problems" not in result.stdout:
            failures.append(f"valid model_refs rejected:\n{result.stdout}{result.stderr}")

    for label, ref in (
        ("unknown model", valid.replace("gpt-6-astra", "gpt-9-unknown")),
        ("missing model", valid.replace("  - model: gpt-6-astra\n", "  - path: ../../core/ASTRA.md\n").replace("    path: ../../core/ASTRA.md\n", "")),
        ("missing path", valid.replace("../../core/ASTRA.md", "../../core/MISSING.md")),
        ("wrong registered path", valid.replace("../../core/ASTRA.md", "../../core/OTHER.md")),
    ):
        with tempfile.TemporaryDirectory() as tmp:
            result = lint(fixture(tmp, ref))
            checks += 1
            if result.returncode == 0 or "F19" not in result.stdout:
                failures.append(f"{label} did not produce F19:\n{result.stdout}{result.stderr}")

    lint_mod = load("primeskills-lint")
    with tempfile.TemporaryDirectory() as tmp:
        skills = fixture(tmp, valid, astra_words=lint_mod.MODEL_REF_BUDGET)
        files = sorted(skills.glob("*/SKILL.md"))
        core = skills.parent / "core"
        common_base = (
            sum(len((core / name).read_text(encoding="utf-8").split())
                for name in lint_mod.CORE_ALWAYS)
            + sum(len(lint_mod.split_frontmatter(
                path.read_text(encoding="utf-8"))[0]["description"].split())
                  for path in files)
            + lint_mod.pointer_words(skills.parent)
        )
        skill = skills / "verify" / "SKILL.md"
        text = skill.read_text(encoding="utf-8")
        budget = lint_mod.CALL_BUDGET - common_base - 25
        skill.write_text(text.replace("budget: 400", f"budget: {budget}"),
                         encoding="utf-8")
        result = lint(skills)
        checks += 1
        if result.returncode == 0 or "C3" not in result.stdout:
            failures.append(f"model path over C3 ceiling passed:\n{result.stdout}{result.stderr}")

    for failure in failures:
        print(failure)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
