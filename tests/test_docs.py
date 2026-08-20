#!/usr/bin/env python3
"""Documents must not describe a set that no longer exists.

Three external reviews in a row found the same class of defect: prose written by
hand claiming behaviour the code had since changed. README still promised that
the checkpoint is committed after `PS-022` made it local; the guide named a file
extension the tool does not write; the benchmark divided by a word count from
two ceilings ago.

Numbers were already generated (`primeskills-status`), and that is why they
stopped drifting. Prose cannot be generated without turning into a worse
document, so it is checked instead: each claim below is paired with the code
that settles it. A claim nobody can check does not belong in this file — add
the check, or leave the claim out of the documents.
"""
import importlib.machinery
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# TODOS keeps the record of what was wrong and quotes it on purpose; review/
# holds other people's words. Neither describes the set as it is now.
HISTORY = {"TODOS.md", "PLAN.md"}
DOCS = sorted(d for d in list(ROOT.glob("*.md")) + list((ROOT / "docs").glob("*.md"))
              if d.name not in HISTORY)


def load(name):
    loader = importlib.machinery.SourceFileLoader("_" + name.replace("-", "_"),
                                                  str(ROOT / "bin" / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def record_suffix():
    """What `primeskills-run` actually writes, read from the program."""
    text = (ROOT / "bin" / "primeskills-run").read_text(encoding="utf-8")
    hit = re.search(r'branch\.replace\([^)]*\)\s*\+\s*"(\.[a-z]+)"', text)
    if hit:
        return hit.group(1)
    hit = re.search(r'"(\.jsonl|\.json|\.md)"', text)
    return hit.group(1) if hit else None


# (what the documents must agree on, how the code settles it)
def main():
    failures = []
    checks = 0
    lint = load("primeskills-lint")

    # 1. The extension of the run record, wherever a document spells it out.
    suffix = record_suffix()
    checks += 1
    if suffix is None:
        failures.append("не удалось прочитать расширение записи прогона из кода")
    else:
        wrong = re.compile(r"\.primeskills/run/<[^>]+>(\.[a-z]+)")
        for doc in DOCS + [ROOT / "bin" / "primeskills-help"]:
            for found in wrong.findall(doc.read_text(encoding="utf-8")):
                checks += 1
                if found != suffix:
                    failures.append(f"{doc.name}: запись прогона названа {found}, "
                                    f"код пишет {suffix}")

    # 2. The fate of the checkpoint. It is local (PS-022), and a document that
    #    still calls it committed sends the next reader to push private notes.
    committed = re.compile(r"handoff[^\n]{0,120}(коммит|commit|push|пуш)", re.I)
    local_ok = re.compile(r"(не коммит|never commit|does not travel|локальн|local)", re.I)
    for doc in DOCS:
        text = doc.read_text(encoding="utf-8")
        # by paragraph, not by line: the claim that sent this document wrong
        # was split across two lines and a line-wise check walked past it
        for para in re.split(r"\n\s*\n", text):
            flat = " ".join(para.split())
            if committed.search(flat) and not local_ok.search(flat):
                checks += 1
                failures.append(f"{doc.name}: «{flat[:80]}» — чекпоинт локальный")

    # 3. Ceilings quoted in prose must be the ceilings the linter enforces.
    #    Both READMEs say it, in two languages, so the number is found by the
    #    rule name next to it rather than by a sentence in one of them.
    for doc, pattern, want, name in (
        (ROOT / "README.md", r"(\d[\d\s ]*)\s*(?:words|слов)\*\*[^\n]*C3", lint.CALL_BUDGET, "C3"),
        (ROOT / "README.ru.md", r"(\d[\d\s ]*)\s*(?:words|слов)\*\*[^\n]*C3", lint.CALL_BUDGET, "C3"),
        (ROOT / "docs" / "SKILL-FORMAT.md", r"≤ (\d[\d\s ]*) слов \(`CORE_BUDGET`", lint.CORE_BUDGET, "C1"),
    ):
        checks += 1
        hit = re.search(pattern, doc.read_text(encoding="utf-8"))
        if not hit:
            failures.append(f"{doc.name}: не нашёл заявленный потолок {name}")
        elif int(re.sub(r"\D", "", hit.group(1))) != want:
            failures.append(f"{doc.name}: {name} назван {hit.group(1).strip()}, "
                            f"линтер держит {want}")

    # 3b. Two READMEs are one statement in two languages. What they must not do
    #     is disagree about the facts, so the numbers are compared.
    en = (ROOT / "README.md").read_text(encoding="utf-8")
    ru = (ROOT / "README.ru.md").read_text(encoding="utf-8")
    def numbers(text):
        body = re.sub(r"^```[\s\S]*?^```", "", text, count=1, flags=re.M)  # без арта
        return sorted(int(re.sub(r"\D", "", n)) for n in re.findall(r"\b\d[\d\s ]{2,}\b", body))
    checks += 1
    if numbers(en) != numbers(ru):
        failures.append(f"README и README.ru разошлись в числах: "
                        f"{numbers(en)} против {numbers(ru)}")

    # 3b'. Agreeing with each other is not the same as being true. Both READMEs
    #      promised 2 545 words of core through three ceilings, because the pair
    #      was checked against itself and against nothing else. The block at the
    #      top of each states five numbers, in one order, in both languages —
    #      settle them against the set (PS-039).
    status = load("primeskills-status")
    want = status.figures()
    order = ("always", "skills", "core", "one_min", "one_max")
    for doc in (ROOT / "README.md", ROOT / "README.ru.md"):
        checks += 1
        blocks = re.findall(r"^```.*?\n(.*?)^```", doc.read_text(encoding="utf-8"),
                            flags=re.M | re.S)
        # the first fence is the ASCII art; the numbers live in the one that
        # states five of them, which is also the only place they are stated
        counted = [[int(re.sub(r"\D", "", n)) for n in re.findall(r"\d[\d\s ]*", b)]
                   for b in blocks]
        found = [c for c in counted if len(c) == len(order)]
        if len(found) != 1:
            failures.append(f"{doc.name}: блок с пятью числами найден "
                            f"{len(found)} раз — проверка не знает, что сверять")
            continue
        said = found[0]
        if said != [want[k] for k in order]:
            failures.append(
                f"{doc.name}: числа {said} против набора "
                f"{[want[k] for k in order]} ({', '.join(order)})")

    # 3b''. The README names the skills by hand, and a hand-written list drops
    #       one quietly: six were missing on 2026-08-19, `baby` and `prose`
    #       among them — two the owner reaches for most. The prose stays human,
    #       the coverage is checked, between the markers.
    skills = {p.parent.name: p.read_text(encoding="utf-8")
              for p in ROOT.glob("skills/*/SKILL.md")}
    singles = {n for n, text in skills.items() if "\ntier: flow" not in text}
    flows = set(skills) - singles
    for doc in (ROOT / "README.md", ROOT / "README.ru.md"):
        checks += 1
        text = doc.read_text(encoding="utf-8")
        block = re.search(r"<!-- skills:begin -->(.*?)<!-- skills:end -->",
                          text, flags=re.S)
        if not block:
            failures.append(f"{doc.name}: разметки списка навыков нет")
            continue
        named = set(re.findall(r"^/([a-z][a-z-]*)", block.group(1), flags=re.M))
        if named != singles:
            failures.append(
                f"{doc.name}: список навыков разошёлся с набором — "
                f"нет {sorted(singles - named)}, лишние {sorted(named - singles)}")
        checks += 1
        missing_flows = sorted(f for f in flows if f"/{f}" not in text)
        if missing_flows:
            failures.append(f"{doc.name}: последовательности не названы: {missing_flows}")

    # 3b'''. A tag without a changelog entry cannot be released with notes, and
    #        nine of them were pushed that way before anyone noticed. Tags are
    #        absent from a shallow CI checkout, so their absence is not a
    #        failure — their disagreement with the changelog is.
    release = load("primeskills-release")
    tags = subprocess.run(["git", "-C", str(ROOT), "tag"],
                          capture_output=True, text=True).stdout.split()
    for tag in tags:
        checks += 1
        try:
            release.entry(tag.lstrip("v"))
        except SystemExit as exc:
            failures.append(f"{tag}: {exc}")
    checks += 1
    try:
        release.entry("0.0.0-нет-такой")
        failures.append("primeskills-release принял версию, которой нет в CHANGELOG")
    except SystemExit:
        pass

    # 3b''''. The changelog is wrapped at the width of the repository; a GitHub
    #         release body is rendered with hard line breaks, so that wrapping
    #         arrives as a column of ragged short lines. Undone on the way out,
    #         and only there.
    wrapped = ("- **Первый пункт.** Он занимает\n  две строки в файле.\n"
               "- Второй пункт.\n\nАбзац, тоже\nв две строки.\n\n"
               "```\nкод\n  остаётся\n```\n")
    got = release.notes_for(wrapped, "2026-01-01")
    checks += 1
    if "**Первый пункт.** Он занимает две строки в файле." not in got:
        failures.append(f"unwrap не склеил перенос внутри пункта:\n{got}")
    checks += 1
    if "- Второй пункт." not in got or got.count("- ") != 2:
        failures.append(f"unwrap потерял границу между пунктами:\n{got}")
    checks += 1
    if "Абзац, тоже в две строки." not in got:
        failures.append(f"unwrap не склеил абзац:\n{got}")
    checks += 1
    if "```\nкод\n  остаётся\n```" not in got:
        failures.append(f"unwrap тронул код внутри ограды:\n{got}")
    checks += 1
    if "\n\n" not in got:
        failures.append(f"unwrap съел пустые строки:\n{got}")

    # 3c. The guide is generated from the set, except two hand-written parts —
    #     and those are exactly the parts that went stale. Each claim below is
    #     tied to something the code decides.
    guide = (ROOT / "bin" / "primeskills-help").read_text(encoding="utf-8")
    installer = (ROOT / "bin" / "primeskills-install").read_text(encoding="utf-8")
    checks += 1
    if "hooks armed in settings.json" in installer and "installer arms them" not in guide:
        failures.append("справка не говорит, что ограничители ставит установщик")
    checks += 1
    if "устанавливаю с закреплённого коммита" in installer and "pinned" not in guide:
        failures.append("справка молчит про пин по умолчанию")
    checks += 1
    core_rules_text = (ROOT / "core" / "GUARDRAILS.md").read_text(encoding="utf-8")
    if "G18" in core_rules_text and "never an order" not in guide:
        failures.append("справка не перечисляет правило G18 среди всегда действующих")

    # 4. VERSION and the newest CHANGELOG entry are one statement in two files.
    checks += 1
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    newest = re.search(r"^## (\S+)", changelog, re.M)
    if not newest:
        failures.append("CHANGELOG.md без записей версий")
    elif newest.group(1) != version:
        failures.append(f"VERSION {version}, а верхняя запись CHANGELOG "
                        f"{newest.group(1)}")

    # 5. The queue promises its own sections by name. It lost one of them and
    #    kept describing four, which is the same defect as any other document
    #    claiming behaviour that is not there.
    todos = (ROOT / "TODOS.md").read_text(encoding="utf-8")
    intro = todos.split("## ", 1)[0]
    for name in re.findall(r"\*\*([А-ЯЁ][^*]{4,60})\*\* —", intro):
        checks += 1
        if f"\n## {name}" not in todos:
            failures.append(f"TODOS.md: во вступлении обещан раздел «{name}», "
                            f"а заголовка такого нет")

    # 6. A skill's declared role must match what it is allowed to do: `write`
    #    on a skill whose tools cannot write is a label, not a fact.
    for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
        meta, _, _ = load("primeskills-lint").split_frontmatter(
            skill.read_text(encoding="utf-8"))
        if not isinstance(meta, dict):
            continue
        tools = meta.get("allowed-tools")
        if meta.get("role") == "write" and tools and not ({"Edit", "Write", "NotebookEdit"} & set(tools)):
            checks += 1
            failures.append(f"{skill.parent.name}: role write, но писать нечем")

    for f in failures:
        print(f)
    print(f"{checks} checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
