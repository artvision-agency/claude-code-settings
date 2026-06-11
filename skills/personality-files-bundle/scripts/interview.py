#!/usr/bin/env python3
"""
interview.py — CLI-опрос для заполнения 5-file personality bundle.

Usage:
    python3 interview.py <client-slug> [--file voice|humor|stats|stories|opinions|all] [--base-dir <path>]

STATUS: STUB — структура готова, вопросы по каждому файлу не реализованы.

TODO:
- Загрузить существующий personality/<file>.md
- Парсить секции (## headers)
- Для каждой секции с placeholder ({...} или TBD) — задать вопрос пользователю
- Сохранить ответы обратно в файл с подстановкой placeholder
- Поддержать --file all (прогон по всем 5 файлам)
- Поддержать resume: пропускать уже заполненные секции
- Опц.: интеграция с brand-voice (если есть VOICE PROFILE — заполнить voice.md автоматом)
- Опц.: source-extract — если в clients/<slug>/sources/ есть .txt/.md с реальными постами,
  показывать их пользователю в качестве подсказки при ответе
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
VALID_FILES = ["voice", "humor", "stats", "stories", "opinions", "all"]


def main() -> int:
    p = argparse.ArgumentParser(description="Interview to fill personality files (STUB).")
    p.add_argument("slug", help="Client slug")
    p.add_argument("--file", default="all", choices=VALID_FILES,
                   help="Which file to fill (default: all)")
    p.add_argument("--base-dir", help="Base clients directory")
    args = p.parse_args()

    print(f"[STUB] interview.py for client '{args.slug}', file '{args.file}'")
    print("This script is not yet implemented.")
    print()
    print("Planned questions per file:")
    print("  voice.md  — ритм, длина предложений, словарь, что НИКОГДА не делает")
    print("  humor.md  — регистр (сарказм/самоирония/абсурд), где уместен, табу")
    print("  stats.md  — personal track record, industry stats, кейсы")
    print("  stories.md — 3-5 поворотных моментов карьеры + клиентские истории")
    print("  opinions.md — острые позиции, что критикует, кого уважает")
    print()
    print("For now, fill templates manually:")
    target_hint = Path.home() / "artvision-data" / "clients" / args.slug / "personality"
    print(f"  $EDITOR {target_hint}/*.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
