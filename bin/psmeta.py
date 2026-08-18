#!/usr/bin/env python3
"""Frontmatter for SKILL.md, read without a YAML library.

PyYAML was the only third-party import in the set and it was never declared as a
dependency, so `primeskills-lint` and `primeskills-route` died with ImportError
on any machine that did not already happen to have it.

What the frontmatter here actually uses is a small subset of YAML: scalars,
inline lists, and one list of flat mappings (`refs`). The only nested block is
`hooks:`, which nothing in this repository reads -- Claude Code parses it
itself -- so it is carried as opaque text and never interpreted.

Anything outside that subset is refused rather than guessed at: `problems` comes
back non-empty and the linter turns it into F14. A parser that silently
mis-reads a shape it does not model is worse than a missing dependency, because
the missing dependency at least announces itself.

Three readers existed before this one (yaml here, a regex sweep in
primeskills-help, a strip in primeskills-status) and the documents they fed had
already drifted apart once. This is the one place a field name is spelled.
"""
import re

# Keys whose value this parser carries but never interprets, because no tool
# here reads them. Adding a key to this list is a decision to stop checking it.
OPAQUE_KEYS = ("hooks",)

KEY = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(.*)$")
ITEM = re.compile(r"^-\s+([A-Za-z][A-Za-z0-9_-]*):(.*)$")


class Opaque(str):
    """Raw text of a block this parser deliberately does not read."""


def scalar(raw):
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def inline_list(raw):
    inner = raw.strip()[1:-1].strip()
    return [scalar(part) for part in inner.split(",")] if inner else []


def dedent(lines):
    indents = [len(ln) - len(ln.lstrip()) for ln in lines if ln.strip()]
    cut = min(indents) if indents else 0
    return [ln[cut:] if ln.strip() else "" for ln in lines]


def take_block(lines, i):
    """Consume the indented lines belonging to the key that ends at line i-1."""
    block = []
    while i < len(lines) and (not lines[i].strip() or lines[i][0].isspace()):
        block.append(lines[i])
        i += 1
    while block and not block[-1].strip():
        block.pop()
    return block, i


def mapping_list(key, block, problems):
    """`refs:` and nothing else so far: a list of mappings, one level deep."""
    items, current = [], None
    for line in dedent(block):
        if not line.strip():
            continue
        head = ITEM.match(line)
        if head:
            current = {head.group(1): scalar(head.group(2))}
            items.append(current)
            continue
        nested = KEY.match(line.strip())
        if current is not None and line[0].isspace() and nested and nested.group(2).strip():
            current[nested.group(1)] = scalar(nested.group(2))
            continue
        problems.append(f"'{key}': expected a list of flat mappings, "
                        f"got {line.strip()[:48]!r}")
        return items
    return items


def parse(block, problems):
    lines = block.splitlines()
    meta, i = {}, 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        head = KEY.match(line)
        if not head or line[0].isspace():
            problems.append(f"expected 'key: value', got {line.strip()[:48]!r}")
            i += 1
            continue
        key, rest = head.group(1), head.group(2)
        nested, i = take_block(lines, i + 1)
        if key in OPAQUE_KEYS:
            meta[key] = Opaque("\n".join(nested))
            continue
        value = rest.strip()
        if value and nested:
            problems.append(f"'{key}': a value and an indented block")
            meta[key] = scalar(value)
        elif value.startswith("[") and value.endswith("]"):
            meta[key] = inline_list(value)
        elif value:
            meta[key] = scalar(value)
        elif nested:
            meta[key] = mapping_list(key, nested, problems)
        else:
            meta[key] = ""
    return meta


def split_frontmatter(text):
    """(meta, body, problems). meta is None when there is no frontmatter at all,
    which is a different failure from a frontmatter this parser refuses."""
    if not text.startswith("---\n"):
        return None, text, []
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text, []
    problems = []
    return parse(text[4:end], problems), text[end + 5:], problems
