#!/usr/bin/env python3
"""
scaffold.py — создаёт 5-file personality bundle для клиента.

Usage:
    python3 scaffold.py <client-slug> [--base-dir <path>] [--from-brand-voice] [--force]

По умолчанию создаёт:
    <ARTVISION_DATA>/clients/<slug>/personality/{voice,humor,stats,stories,opinions}.md

Подставляет {CLIENT_NAME} = slug в title-case и {DATE} = today.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"
FILES = ["voice.md", "humor.md", "stats.md", "stories.md", "opinions.md"]


def detect_base_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    # Default: ~/artvision-data/clients
    candidate = Path.home() / "artvision-data" / "clients"
    if candidate.exists():
        return candidate
    # Fallback: ./clients
    return Path.cwd() / "clients"


def render(template: str, client_name: str, date: str, sources: str = "TBD") -> str:
    return (
        template
        .replace("{CLIENT_NAME}", client_name)
        .replace("{DATE}", date)
        .replace("{SOURCES_LIST}", sources)
    )


def scaffold(slug: str, base_dir: Path, force: bool = False) -> tuple[Path, list[str], list[str]]:
    target = base_dir / slug / "personality"
    target.mkdir(parents=True, exist_ok=True)

    client_name = slug.replace("-", " ").replace("_", " ").title()
    today = dt.date.today().isoformat()

    created: list[str] = []
    skipped: list[str] = []

    for fname in FILES:
        src = TEMPLATES_DIR / fname
        dst = target / fname

        if not src.exists():
            print(f"[WARN] template missing: {src}", file=sys.stderr)
            continue

        if dst.exists() and not force:
            skipped.append(fname)
            continue

        content = src.read_text(encoding="utf-8")
        rendered = render(content, client_name=client_name, date=today)
        dst.write_text(rendered, encoding="utf-8")
        created.append(fname)

    return target, created, skipped


def main() -> int:
    p = argparse.ArgumentParser(description="Scaffold 5-file personality bundle for a client.")
    p.add_argument("slug", help="Client slug (e.g. andrey-burenie)")
    p.add_argument("--base-dir", help="Base clients directory (default: ~/artvision-data/clients or ./clients)")
    p.add_argument("--from-brand-voice", action="store_true",
                   help="TODO: seed voice.md from existing brand-voice.md in client folder")
    p.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = p.parse_args()

    base_dir = detect_base_dir(args.base_dir)
    if not base_dir.exists():
        print(f"[ERR] base dir does not exist: {base_dir}", file=sys.stderr)
        return 2

    target, created, skipped = scaffold(args.slug, base_dir, force=args.force)

    print(f"Personality bundle: {target}")
    if created:
        print(f"  Created ({len(created)}): {', '.join(created)}")
    if skipped:
        print(f"  Skipped existing ({len(skipped)}): {', '.join(skipped)}  (use --force to overwrite)")

    if args.from_brand_voice:
        bv = base_dir / args.slug / "brand-voice.md"
        if bv.exists():
            print(f"  TODO: --from-brand-voice would seed voice.md from {bv}")
        else:
            print(f"  --from-brand-voice: no brand-voice.md found at {bv}, nothing to seed.")

    print("\nNext steps:")
    print(f"  1. Review templates: ls {target}")
    print(f"  2. Run interview to fill content: python3 {SKILL_DIR}/scripts/interview.py {args.slug}")
    print(f"  3. Wire into downstream skills via inject.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
