#!/usr/bin/env python3
"""
build-routing-table.py — автогенерация routing-таблицы из SKILL.md frontmatter.

Читает ~/.claude/skills/*/SKILL.md (или plugin variants), парсит:
  - name (из frontmatter или папки)
  - description
  - триггеры (русские/английские keywords из description)
Генерирует Markdown-таблицу в формате routing для CLAUDE.md.

Использование:
    python3 ~/.claude/scripts/build-routing-table.py [--out FILE]

По умолчанию печатает в stdout. С --out пишет в файл.
"""

from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

SKILLS_ROOT = Path.home() / ".claude" / "skills"
PLUGINS_ROOT = Path.home() / ".claude" / "plugins" / "cache"


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    fm_text = text[4:end]
    out: dict = {}
    for line in fm_text.splitlines():
        m = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


def extract_triggers(description: str, name: str) -> list[str]:
    """Извлекает потенциальные триггеры из description.
    Эвристика: слова в кавычках, после 'Триггеры:', 'Use when:', и сам name."""
    triggers = {name}
    # «триггеры: X, Y, Z» / 'Triggers: X, Y'
    m = re.search(r"(?:[Тт]риггеры?|[Tt]riggers?|[Tt]rigger)[:\s]+([^\n.]{3,200})", description)
    if m:
        for w in re.split(r"[,;|/]", m.group(1)):
            w = w.strip().strip("'\"`«»").lower()
            if 2 < len(w) < 40:
                triggers.add(w)
    # quoted phrases 'foo' or "bar"
    for m in re.finditer(r"['\"`]([^'\"`\n]{3,40})['\"`]", description):
        triggers.add(m.group(1).strip().lower())
    return sorted(triggers)


def find_skills() -> list[tuple[str, Path, dict]]:
    """Returns list of (skill_name, path, frontmatter)."""
    out: list[tuple[str, Path, dict]] = []
    seen: set[str] = set()
    if SKILLS_ROOT.exists():
        for skill_md in SKILLS_ROOT.glob("*/SKILL.md"):
            try:
                text = skill_md.read_text(errors="replace")
            except Exception:
                continue
            fm = parse_frontmatter(text)
            name = fm.get("name") or skill_md.parent.name
            if name in seen:
                continue
            seen.add(name)
            out.append((name, skill_md, fm))
    return sorted(out, key=lambda x: x[0])


def build_table(skills: list) -> str:
    lines = [
        "| Триггеры (рус/eng) | Скилл |",
        "|---------------------|-------|",
    ]
    for name, _, fm in skills:
        if name.startswith(".") or "archived" in name:
            continue
        desc = fm.get("description", "")
        triggers = extract_triggers(desc, name)
        # ограничиваем 6 наиболее показательных триггеров
        trigger_str = ", ".join(triggers[:8])
        skill_ref = f"`/{name}`"
        lines.append(f"| {trigger_str} | {skill_ref} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="output file (default stdout)")
    ap.add_argument("--stats", action="store_true", help="show coverage stats only")
    args = ap.parse_args()

    skills = find_skills()
    if not skills:
        print("No skills found in", SKILLS_ROOT)
        sys.exit(1)

    if args.stats:
        with_desc = sum(1 for _, _, fm in skills if fm.get("description"))
        with_triggers_word = sum(
            1 for _, _, fm in skills if re.search(r"[Тт]риггеры", fm.get("description", ""))
        )
        print(f"Total skills: {len(skills)}")
        print(f"With description: {with_desc}")
        print(f"With explicit Триггеры section: {with_triggers_word}")
        sys.exit(0)

    out_text = (
        "# Auto-generated routing table from SKILL.md frontmatter\n"
        f"# Generated: by ~/.claude/scripts/build-routing-table.py\n"
        f"# Total skills: {len(skills)}\n\n"
        + build_table(skills)
        + "\n"
    )
    if args.out:
        Path(args.out).write_text(out_text)
        print(f"Written → {args.out} ({len(skills)} skills)")
    else:
        print(out_text)


if __name__ == "__main__":
    main()
