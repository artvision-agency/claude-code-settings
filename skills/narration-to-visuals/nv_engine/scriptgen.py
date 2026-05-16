"""Rule-based first draft: summary H2 sections -> blocks, transcript mapped in.

This is a DRAFT. Claude refines wording per SKILL.md before the review gate.
Mapping is deterministic keyword overlap so it is unit-testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from nv_engine.cleaning import clean_segment_text, is_offtopic_segment
from nv_engine.inputs import RawInputs, Segment

_WORD = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")
_STOP = {
    "и", "в", "на", "что", "это", "как", "не", "а", "но", "за", "по", "о",
    "the", "a", "to", "of", "про", "для", "из", "же", "бы", "ли", "то",
}


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text) if w.lower() not in _STOP and len(w) > 2}


@dataclass
class Block:
    title: str
    summary_body: str
    narration: str = ""
    start: float | None = None
    end: float | None = None
    marker: str | None = None  # "B" | "C" | "D" — проставит Task 7
    source_segments: list[Segment] = field(default_factory=list)


def _clean_segments(raw: RawInputs) -> list[tuple[Segment, str]]:
    out: list[tuple[Segment, str]] = []
    for seg in raw.segments:
        if is_offtopic_segment(seg):
            continue
        cleaned = clean_segment_text(seg.text)
        if cleaned:
            out.append((seg, cleaned))
    return out


def _summary_to_text(body: str) -> str:
    """Конспект-секцию → плоский текст: снять markdown-маркеры (> # - *)."""
    lines = []
    for ln in body.splitlines():
        s = ln.strip().lstrip(">#-*").strip()
        if s:
            lines.append(s)
    return " ".join(lines).strip()


def build_blocks(raw: RawInputs) -> list[Block]:
    h2 = [s for s in raw.summary_sections if s.level == 2]
    blocks = [Block(title=s.title, summary_body=s.body) for s in h2]
    if not blocks:
        blocks = [Block(title="Лекция", summary_body="")]

    block_tokens = [
        _tokens(b.title + " " + b.summary_body) for b in blocks
    ]
    cleaned = _clean_segments(raw)

    for seg, ctext in cleaned:
        seg_tok = _tokens(ctext)
        scores = [
            len(seg_tok & bt) for bt in block_tokens
        ]
        best = max(range(len(blocks)), key=lambda i: scores[i]) if scores else 0
        # если ноль пересечений — кладём в последний содержательный блок,
        # чтобы текст не терялся (никогда не бросаем контент)
        if scores and scores[best] == 0:
            best = min(best, len(blocks) - 1)
        blocks[best].source_segments.append(seg)

    for b in blocks:
        if b.source_segments:
            b.narration = " ".join(
                clean_segment_text(s.text) for s in b.source_segments
            ).strip()
            b.start = min(s.start for s in b.source_segments)
            b.end = max(s.end for s in b.source_segments)
        else:
            # H2-секция без сопоставленного транскрипта: черновик из конспекта,
            # НИКОГДА не пустой (Claude доведёт на ревью №1). Тайм-якоря нет.
            b.narration = _summary_to_text(b.summary_body) or b.title
    return blocks


# --- B/C/D marker heuristic -------------------------------------------------
# Приоритет: сильный C (определение / 🎯) > D (схема/код/техника)
#          > прочий C (тезис) > B (иллюстрация).
# Дефолт без сигналов = C (никогда не пустой экран; слайд с тезисом).
# Примечание: голое «код» НЕ сигнал D — слишком частое слово ("плохой код"),
# даёт ложные D. Явное определение/🎯 — намеренный сигнал автора, бьёт D.

_STRONG_C = re.compile(r"(🎯|определени)\w*", re.IGNORECASE)
_D_SIGNALS = re.compile(
    r"\b(pipeline|ci/cd|ci\b|cd\b|архитектур|схем|диаграмм|алгоритм|api|"
    r"deploy|kubernetes|docker|sql|функци|класс|структур)\w*",
    re.IGNORECASE,
)
_C_SIGNALS = re.compile(
    r"(тезис|принцип|правило|вывод|итог|ключев|формул)\w*",
    re.IGNORECASE,
)
_B_SIGNALS = re.compile(
    r"\b(представьте|метафор|как кредит|история|пример из жизни|аналог)\w*",
    re.IGNORECASE,
)


def assign_markers(blocks: list[Block]) -> list[Block]:
    for b in blocks:
        blob = f"{b.title}\n{b.summary_body}\n{b.narration}"
        if _STRONG_C.search(blob):
            b.marker = "C"
        elif _D_SIGNALS.search(blob):
            b.marker = "D"
        elif _C_SIGNALS.search(blob):
            b.marker = "C"
        elif _B_SIGNALS.search(blob):
            b.marker = "B"
        else:
            b.marker = "C"  # дефолт — слайд с тезисом
    return blocks
