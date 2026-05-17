"""Deterministic noise removal from raw ASR transcript text.

Conservative: removes only well-known Russian fillers and clearly
organizational/off-topic segments. Semantic rewriting is NOT done here —
that is Claude's job per SKILL.md.
"""

from __future__ import annotations

import re

from nv_engine.inputs import Segment

_FILLERS = [
    "эээ", "ээ", "эм", "ну как бы", "как бы", "ну", "вот", "значит",
    "понимаете", "знаете", "типа", "в общем-то", "то есть как бы",
]
# слова-маркеры оргмомента/оффтопика (не контент лекции)
_OFFTOPIC = [
    "кто-то пишет в чат", "пишет в чат", "люди ещё", "люди еще",
    "ещё подключаются", "еще подключаются", "секунду", "подождите",
    "слышно меня", "демонстрация экрана", "запись идёт", "запись идет",
]

_FILLER_RE = re.compile(
    r"(?<![\wа-яё])(" + "|".join(re.escape(f) for f in _FILLERS) + r")(?![\wа-яё])",
    re.IGNORECASE,
)
_PUNCT_FIX = re.compile(r"\s+([,.!?;:])")
_MULTISPACE = re.compile(r"\s{2,}")
_LEADING_PUNCT = re.compile(r"^[\s,.;:!?-]+")


def clean_segment_text(text: str) -> str:
    t = _FILLER_RE.sub("", text)
    t = _PUNCT_FIX.sub(r"\1", t)
    t = re.sub(r"(,\s*){2,}", ", ", t)
    t = _LEADING_PUNCT.sub("", t)
    t = _MULTISPACE.sub(" ", t).strip()
    # если осталась только пунктуация/пусто — считаем пустым
    if not re.search(r"[A-Za-zА-Яа-яЁё0-9]", t):
        return ""
    if t:
        t = t[0].upper() + t[1:]
    return t


def is_offtopic_segment(segment: Segment) -> bool:
    low = segment.text.lower()
    return any(marker in low for marker in _OFFTOPIC)
