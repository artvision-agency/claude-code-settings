"""Deterministic DRAFT content per block, keyed by the author-approved
marker. Claude refines these per SKILL.md before Gate 2; Plan 3 turns
them into real assets. The marker itself is authoritative (set by the
author at Gate 1) — here we only scaffold content shaped for it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SENT = re.compile(r"[^.!?]+[.!?]?")


@dataclass(frozen=True)
class BlockContent:
    marker: str
    image_prompt: str | None = None
    slide_lines: list[str] | None = None
    diagram_spec: str | None = None


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT.findall(text) if s.strip()]


def draft_content(*, title: str, marker: str, narration: str) -> BlockContent:
    m = marker if marker in {"B", "C", "D"} else "C"
    sents = _sentences(narration)
    if m == "B":
        lead = sents[0] if sents else title
        return BlockContent(marker="B",
                            image_prompt=f"{title}: {lead}")
    if m == "D":
        return BlockContent(marker="D",
                            diagram_spec=f"diagram: {title}\nsource: {narration.strip()}")
    # C (default)
    lines = [s[:120] for s in sents] or [title[:120]]
    return BlockContent(marker="C", slide_lines=lines)
