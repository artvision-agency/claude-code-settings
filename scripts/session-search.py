#!/usr/bin/env python3
"""
session-search.py — Полнотекстовый поиск по истории сессий Claude Code.

Использование:
    session-search.py "ключевое слово"
    session-search.py "слово1 слово2"              # И-логика (все слова)
    session-search.py "API" --date 2026-01-28
    session-search.py "SEO" --project artvision-data --list
    session-search.py "договор" --context 2 --limit 5

Архитектура (2 фазы):
  Фаза 1: sessions-index.json → фильтр по дате/проекту
  Фаза 2: JSONL стриминг → полнотекстовый поиск user/assistant сообщений
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── Constants ────────────────────────────────────────────────────────────────

CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"
def find_index_file() -> Path | None:
    """Найти sessions-index.json автоматически."""
    if not PROJECTS_DIR.exists():
        return None
    for proj_dir in sorted(PROJECTS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not proj_dir.is_dir():
            continue
        idx = proj_dir / "sessions-index.json"
        if idx.exists():
            return idx
    return None

# ANSI colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_YELLOW = "\033[33m"
C_CYAN = "\033[36m"
C_GREEN = "\033[32m"
C_RED = "\033[31m"
C_BG_YELLOW = "\033[43m\033[30m"  # yellow bg, black text
C_MAGENTA = "\033[35m"


def highlight(text: str, keywords: list[str]) -> str:
    """Highlight keywords in text with ANSI colors."""
    for kw in keywords:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        text = pattern.sub(f"{C_BG_YELLOW}{kw}{C_RESET}", text)
    return text


def extract_text(content) -> str:
    """Extract searchable text from message content."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                btype = block.get("type", "")
                if btype == "text":
                    parts.append(block.get("text", ""))
                # Skip: thinking, tool_use, tool_result, system
        return "\n".join(parts)
    return ""


def format_time(ts_str: str) -> str:
    """Format ISO timestamp to HH:MM."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except (ValueError, AttributeError):
        return "??:??"


def format_date(ts_str: str) -> str:
    """Format ISO timestamp to YYYY-MM-DD HH:MM."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return "unknown"


def truncate(text: str, max_len: int = 200) -> str:
    """Truncate text to max_len chars."""
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


# ── Phase 1: Index filtering ────────────────────────────────────────────────

def load_index() -> list[dict]:
    """Загрузить индекс сессий."""
    idx_path = find_index_file()
    if not idx_path:
        print(f"{C_RED}Ошибка: sessions-index.json не найден{C_RESET}", file=sys.stderr)
        sys.exit(1)

    with open(idx_path) as f:
        data = json.load(f)
    return data.get("entries", [])


def filter_index(entries: list[dict], args) -> list[dict]:
    """Filter index entries by date, project, min messages."""
    filtered = []
    for entry in entries:
        # Skip sidechains
        if entry.get("isSidechain", False):
            continue

        # Skip tiny sessions
        if entry.get("messageCount", 0) < 3:
            continue

        # Date filter
        if args.date:
            created = entry.get("created", "")
            if not created.startswith(args.date):
                modified = entry.get("modified", "")
                if not modified.startswith(args.date):
                    continue

        # Project filter
        if args.project:
            project_path = entry.get("projectPath", "")
            if args.project.lower() not in project_path.lower():
                continue

        filtered.append(entry)

    # Sort by modified date descending
    filtered.sort(key=lambda e: e.get("modified", ""), reverse=True)
    return filtered


# ── Phase 2: JSONL streaming search ─────────────────────────────────────────

def search_session(filepath: str, keywords: list[str], context_lines: int = 1) -> dict | None:
    """
    Stream through JSONL file searching for keywords in user/assistant messages.
    Returns match info or None.
    """
    if not os.path.exists(filepath):
        return None

    messages = []  # (index, role, time, text)
    match_indices = []

    kw_lower = [k.lower() for k in keywords]

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = obj.get("type", "")
                if msg_type not in ("user", "assistant"):
                    continue

                msg = obj.get("message", {})
                role = msg.get("role", msg_type)
                content = msg.get("content", "")
                text = extract_text(content)
                timestamp = obj.get("timestamp", "")

                if not text.strip():
                    continue

                idx = len(messages)
                messages.append((idx, role, timestamp, text))

                # AND logic: all keywords must be present
                text_lower = text.lower()
                if all(kw in text_lower for kw in kw_lower):
                    match_indices.append(idx)

    except (OSError, UnicodeDecodeError):
        return None

    if not match_indices:
        return None

    return {
        "messages": messages,
        "match_indices": match_indices,
        "total_messages": len(messages),
        "match_count": len(match_indices),
    }


# ── Output formatting ───────────────────────────────────────────────────────

def get_summary(entry: dict) -> str:
    """Получить описание сессии: summary или firstPrompt как fallback."""
    summary = entry.get("summary", "")
    if not summary or summary == "No summary":
        summary = entry.get("firstPrompt", "")
    if not summary:
        summary = "Без описания"
    return truncate(summary, 80)


def print_session_header(entry: dict, match_count: int, total_messages: int):
    """Print session header."""
    date = format_date(entry.get("created", ""))
    summary = get_summary(entry)
    msg_count = entry.get("messageCount", total_messages)
    project = entry.get("projectPath", "")
    # Shorten project path
    project_short = project.replace("/Users/antonk/", "~/") if project else ""

    print(f"\n{C_BOLD}{C_CYAN}=== {date} ({msg_count} сообщений, "
          f"{C_YELLOW}{match_count} совпадений{C_CYAN}) ==={C_RESET}")
    print(f"{C_DIM}Тема: {summary}{C_RESET}")
    if project_short:
        print(f"{C_DIM}Проект: {project_short}{C_RESET}")


def print_matches(result: dict, keywords: list[str], context: int, max_show: int = 3):
    """Print matched messages with context."""
    messages = result["messages"]
    match_indices = result["match_indices"]
    shown = 0

    for mi in match_indices:
        if shown >= max_show:
            remaining = len(match_indices) - shown
            if remaining > 0:
                print(f"\n{C_DIM}--- ещё {remaining} совпадений ---{C_RESET}")
            break

        # Context range
        start = max(0, mi - context)
        end = min(len(messages), mi + context + 1)

        if shown > 0:
            print(f"{C_DIM}  ...{C_RESET}")

        for i in range(start, end):
            idx, role, ts, text = messages[i]
            time_str = format_time(ts)
            role_upper = role.upper()

            if role == "user":
                role_color = C_GREEN
            else:
                role_color = C_MAGENTA

            display_text = truncate(text, 300)

            if i == mi:
                # This is the match — highlight keywords
                display_text = highlight(display_text, keywords)
                prefix = f"{C_BOLD}[{time_str}] {role_color}{role_upper}{C_RESET}: "
            else:
                # Context line
                prefix = f"{C_DIM}[{time_str}] {role_upper}: "
                display_text = f"{display_text}{C_RESET}"

            print(f"  {prefix}{display_text}")

        shown += 1


def print_list_mode(entry: dict, match_count: int):
    """Print one-line summary for --list mode."""
    date = format_date(entry.get("created", ""))
    summary = get_summary(entry)
    msg_count = entry.get("messageCount", 0)
    print(f"  {C_CYAN}{date}{C_RESET}  "
          f"{C_YELLOW}{match_count:2d} совп.{C_RESET}  "
          f"{C_DIM}({msg_count:3d} сообщ.){C_RESET}  "
          f"{summary[:70]}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Полнотекстовый поиск по сессиям Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Примеры:
  ss "avtoworld"
  ss "стоимость avtoworld"
  ss "API" --date 2026-01-28
  ss "SEO" --list --limit 5
  ss "договор" --context 2 --project artvision-data
        """,
    )
    parser.add_argument("query", help="Поисковый запрос (через пробел = И-логика)")
    parser.add_argument("--date", "-d", help="Фильтр по дате (ГГГГ-ММ-ДД)")
    parser.add_argument("--project", "-p", help="Фильтр по проекту (подстрока пути)")
    parser.add_argument("--limit", "-l", type=int, default=10,
                        help="Макс. сессий в выводе (по умолчанию: 10)")
    parser.add_argument("--context", "-c", type=int, default=1,
                        help="Контекст сообщений вокруг совпадения (по умолчанию: 1)")
    parser.add_argument("--list", action="store_true",
                        help="Режим списка: одна строка на сессию")
    parser.add_argument("--max-show", "-m", type=int, default=3,
                        help="Макс. совпадений на сессию (по умолчанию: 3)")
    parser.add_argument("--all-projects", "-a", action="store_true",
                        help="Искать по всем директориям проектов")

    args = parser.parse_args()

    keywords = args.query.split()
    if not keywords:
        print(f"{C_RED}Ошибка: пустой запрос{C_RESET}", file=sys.stderr)
        sys.exit(1)

    # Phase 1: Load and filter index
    entries = load_index()
    filtered = filter_index(entries, args)

    if not filtered:
        print(f"{C_YELLOW}Нет сессий по фильтрам{C_RESET}")
        if args.date:
            print(f"{C_DIM}  дата={args.date}{C_RESET}")
        if args.project:
            print(f"{C_DIM}  проект={args.project}{C_RESET}")
        sys.exit(0)

    # Phase 2: Search through JSONL files
    results = []  # (entry, search_result)
    scanned = 0

    for entry in filtered:
        filepath = entry.get("fullPath", "")
        if not filepath:
            continue

        result = search_session(filepath, keywords, args.context)
        scanned += 1

        if result:
            results.append((entry, result))

        # Progress indicator for large searches
        if scanned % 20 == 0 and not args.list:
            print(f"\r{C_DIM}Сканирую... {scanned}/{len(filtered)} сессий, "
                  f"{len(results)} найдено{C_RESET}", end="", file=sys.stderr)

    # Clear progress line
    if scanned >= 20 and not args.list:
        print(f"\r{' ' * 60}\r", end="", file=sys.stderr)

    if not results:
        print(f"{C_YELLOW}Нет совпадений для: {C_BOLD}{args.query}{C_RESET}")
        print(f"{C_DIM}Просканировано {scanned} сессий{C_RESET}")
        sys.exit(0)

    # Sort by match count descending
    results.sort(key=lambda r: r[1]["match_count"], reverse=True)

    # Limit results
    results = results[:args.limit]

    # Заголовок результатов
    total_matches = sum(r[1]["match_count"] for r in results)
    print(f"{C_BOLD}Найдено {C_YELLOW}{total_matches}{C_RESET}{C_BOLD} совпадений "
          f"в {C_CYAN}{len(results)}{C_RESET}{C_BOLD} сессиях{C_RESET} "
          f"{C_DIM}(просканировано {scanned}){C_RESET}")
    print(f"{C_DIM}Запрос: {' И '.join(keywords)}{C_RESET}")

    if args.list:
        # List mode
        print()
        for entry, result in results:
            print_list_mode(entry, result["match_count"])
    else:
        # Full mode
        for entry, result in results:
            print_session_header(entry, result["match_count"], result["total_messages"])
            print_matches(result, keywords, args.context, args.max_show)

    print()


if __name__ == "__main__":
    main()
