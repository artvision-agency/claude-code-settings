#!/usr/bin/env python3
"""
skill-discovery-tfidf.py — улучшенный matcher prompt → relevant skills.

Заменяет grep-based prompt-skill-discovery.sh.
TF-IDF по описаниям всех SKILL.md, top-5 матчей.

Использование:
  echo "<prompt text>" | python3 skill-discovery-tfidf.py
  → выводит markdown-блок [SKILL-DISCOVERY] с топ-5

Returns 0 always (non-blocking).
"""

from __future__ import annotations
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

SKILLS_DIR = Path.home() / ".claude" / "skills"
STOP = set("и в во не на с что как а но да по для от из до при об за без the of and to a in is for with on this that be it as".split())


def tokenize(text: str) -> list[str]:
    text = text.lower()
    return [t for t in re.findall(r"[a-zа-я][a-zа-я-]{3,}", text) if t not in STOP]


def parse_skill(skill_md: Path) -> tuple[str, str]:
    name = skill_md.parent.name
    try:
        text = skill_md.read_text(errors="replace")
    except Exception:
        return name, ""
    if text.startswith("---"):
        end = text.find("\n---", 4)
        if end > 0:
            fm = text[4:end]
            for line in fm.splitlines():
                m = re.match(r"^description:\s*(.*)$", line)
                if m:
                    return name, m.group(1).strip().strip('"').strip("'")
    return name, ""


def main():
    prompt = sys.stdin.read()
    if len(prompt) < 30:
        return  # too short
    prompt_tokens = tokenize(prompt)
    if not prompt_tokens:
        return

    if not SKILLS_DIR.exists():
        return

    # Build corpus
    docs = {}  # skill_name -> tokens
    for skill_md in SKILLS_DIR.glob("*/SKILL.md"):
        name, desc = parse_skill(skill_md)
        if name.startswith(".") or not desc:
            continue
        docs[name] = tokenize(desc + " " + name.replace("-", " "))

    if not docs:
        return

    # IDF
    N = len(docs)
    df: Counter = Counter()
    for tokens in docs.values():
        for t in set(tokens):
            df[t] += 1
    idf = {t: math.log(N / (1 + c)) + 1 for t, c in df.items()}

    # Score: TF-IDF cosine-ish
    pq = Counter(prompt_tokens)
    scores = {}
    for name, tokens in docs.items():
        tf = Counter(tokens)
        score = 0.0
        for t, q in pq.items():
            if t in tf:
                score += q * tf[t] * idf.get(t, 1.0)
        # bonus за упоминание имени skill
        if name in prompt.lower():
            score += 50
        if score > 2:
            scores[name] = score

    if not scores:
        return

    top = sorted(scores.items(), key=lambda x: -x[1])[:5]
    if not top or top[0][1] < 5:
        return

    print("[SKILL-DISCOVERY] Под эту задачу могут подойти скиллы (по описанию):")
    print()
    for name, score in top:
        print(f"  • {name} (score={score:.0f})")
    print()
    print("Если задача попадает в их домен — ВЫЗОВИ Skill tool с этим именем,")
    print("а не имитируй через Bash/Agent.")


if __name__ == "__main__":
    main()
