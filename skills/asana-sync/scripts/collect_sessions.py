#!/usr/bin/env python3
"""Collect today's Claude Code sessions and output JSON summaries."""

import json
import os
import sys
import re
from datetime import datetime, date
from pathlib import Path

SESSIONS_DIR = Path.home() / ".claude" / "projects" / "-Users-antonk"

# Keywords → Asana project mapping
PROJECT_KEYWORDS = {
    "ANT.partners": ["ant-partners", "ant partners", "ант парт", "ant.partners"],
    "Otido-group": ["otido", "отидо"],
    "Extru-Tech": ["extru", "экстру"],
    "Атрибьют": ["atribeaute", "атрибьют", "игор"],
    "Presale: AdvertMed (партнёры)": ["varikoz", "варикоз", "advertmed", "адвертмед"],
    "Presale: Symmetron": ["symmetron", "симметрон"],
    "Madwave": ["madwave"],
    "AI Vision (ai.artvision.pro)": ["ai vision", "ai.artvision"],
    "Structural Engineering (stressedskin.io)": ["structural", "stressedskin"],
    "Передвижной портной": ["портной"],
    "LoyalMed Конкурент": ["loyalmed"],
}

# Skip patterns for meta/informational sessions
SKIP_PATTERNS = [
    r"^--resume", r"^claude\s+--", r"^sync$", r"^пуш$", r"^синк$",
    r"^/voice", r"^/terminal", r"^/help",
]

MIN_SIZE_BYTES = 5000  # Skip sessions under 5KB


def extract_first_message(filepath: Path) -> str:
    """Extract first meaningful user message from session JSONL."""
    with open(filepath) as f:
        for line in f:
            try:
                d = json.loads(line)
                if d.get("type") != "user":
                    continue
                msg = d.get("message", {})
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content", "")
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            txt = item["text"].strip()
                            if txt and len(txt) > 3 and not txt.startswith("<"):
                                return txt[:200]
                elif isinstance(content, str) and len(content) > 3:
                    if not content.startswith("<"):
                        return content[:200]
            except (json.JSONDecodeError, KeyError):
                continue
    return ""


def guess_project(text: str) -> str | None:
    """Match session text to Asana project name."""
    lower = text.lower()
    for project, keywords in PROJECT_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return project
    return None


def should_skip(first_msg: str, size: int) -> bool:
    """Determine if session should be skipped."""
    if size < MIN_SIZE_BYTES:
        return True
    if not first_msg:
        return True
    for pat in SKIP_PATTERNS:
        if re.match(pat, first_msg, re.IGNORECASE):
            return True
    return False


def collect_sessions() -> list[dict]:
    """Collect and summarize today's sessions."""
    today = date.today()
    sessions = []

    for f in sorted(SESSIONS_DIR.glob("*.jsonl"), key=os.path.getmtime, reverse=True):
        mtime = datetime.fromtimestamp(os.path.getmtime(f))
        if mtime.date() != today:
            continue

        sid = f.stem
        size = f.stat().st_size
        first_msg = extract_first_message(f)
        project = guess_project(first_msg)
        skip = should_skip(first_msg, size)

        sessions.append({
            "id": sid[:8],
            "full_id": sid,
            "size": size,
            "size_human": f"{size // 1024}K" if size < 1048576 else f"{size / 1048576:.1f}M",
            "time": mtime.strftime("%H:%M"),
            "first_message": first_msg,
            "project": project,
            "skip": skip,
        })

    return sessions


if __name__ == "__main__":
    sessions = collect_sessions()
    json.dump(sessions, sys.stdout, ensure_ascii=False, indent=2)
    print()  # trailing newline

    # Summary to stderr
    total = len(sessions)
    actionable = sum(1 for s in sessions if not s["skip"])
    print(f"\nTotal: {total} sessions, {actionable} actionable", file=sys.stderr)
