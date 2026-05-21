#!/usr/bin/env python3
"""
inject.py — формирует context-block из personality/<files>.md для downstream скиллов.

Usage (CLI):
    python3 inject.py <client-slug> --role <role> [--base-dir <path>]

    role ∈ {article, post, social, outreach, copy, kp}

Usage (Python):
    from inject import build_context
    ctx = build_context(client_slug="andrey-burenie", role="article")
    # returns: str (markdown block ready to embed in another skill's context)

STATUS: STUB — структура готова, парсинг и роль-маппинг не реализованы.

TODO:
- Маппинг роль → набор файлов (см. таблицу в SKILL.md)
- Чтение personality/<file>.md, фильтрация пустых placeholder-секций
- Сборка единого context-block с заголовком и метаданными
- Кэширование (если файлы не менялись — не парсить заново)
- Опц.: токен-бюджет (если >N токенов — сжать или дать только summary каждого файла)
- Опц.: hook в content-writer / outreach-emails / smm-strategist для авто-вызова
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent

# Роль → список файлов personality/ для инжекта
ROLE_MAP: dict[str, list[str]] = {
    "article": ["voice", "stats", "stories", "opinions"],
    "post": ["voice", "humor", "opinions"],
    "social": ["voice", "humor", "opinions"],
    "outreach": ["voice", "humor", "stats"],
    "copy": ["voice", "humor"],
    "kp": ["voice", "stats"],  # KP — без humor/opinions
}


def detect_base_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    candidate = Path.home() / "artvision-data" / "clients"
    if candidate.exists():
        return candidate
    return Path.cwd() / "clients"


def build_context(client_slug: str, role: str, base_dir: Path | None = None) -> str:
    """
    Build a markdown context block from relevant personality files.

    STUB: currently returns a placeholder. Real implementation should:
    1. Find clients/<slug>/personality/
    2. Map role -> files via ROLE_MAP
    3. Read each file, strip empty/placeholder sections
    4. Concatenate into single markdown block
    """
    if base_dir is None:
        base_dir = detect_base_dir(None)

    files = ROLE_MAP.get(role)
    if files is None:
        return f"[ERROR] Unknown role '{role}'. Valid roles: {list(ROLE_MAP)}"

    target = base_dir / client_slug / "personality"
    if not target.exists():
        return f"[INFO] No personality bundle at {target} — using default voice."

    # TODO: actual parsing
    found = [f"{f}.md" for f in files if (target / f"{f}.md").exists()]
    return (
        f"# Personality context for {client_slug} (role: {role})\n"
        f"# STUB — would inject: {', '.join(found)}\n"
        f"# Source: {target}\n"
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Build personality context block for downstream skills (STUB).")
    p.add_argument("slug", help="Client slug")
    p.add_argument("--role", required=True, choices=list(ROLE_MAP.keys()),
                   help="Content role (determines which files to include)")
    p.add_argument("--base-dir", help="Base clients directory")
    args = p.parse_args()

    base_dir = detect_base_dir(args.base_dir)
    ctx = build_context(args.slug, args.role, base_dir)
    print(ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
