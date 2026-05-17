"""Deviation flags: how far the recording drifted from the approved script.

Per block: token-level edit distance between the block's script narration
and the recording words allocated to that block (by segment.py). Ratio
above threshold → DEVIATION (surfaced in the storyboard for Gate 2).
Content stays script-driven; this only flags where the author improvised.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from nv_engine.segment import BlockSpan

_TOK = re.compile(r"\S+")


@dataclass(frozen=True)
class BlockReconciliation:
    index: int
    title: str
    edit_ratio: float
    deviation: bool


def _norm(tokens: list[str]) -> list[str]:
    return [t.lower().strip(".,!?;:—-«»\"'()") for t in tokens]


def _edit_distance(a: list[str], b: list[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, ta in enumerate(a, 1):
        cur = [i]
        for j, tb in enumerate(b, 1):
            cur.append(min(
                prev[j] + 1,
                cur[j - 1] + 1,
                prev[j - 1] + (0 if ta == tb else 1),
            ))
        prev = cur
    return prev[-1]


def reconcile_blocks(*, spans: list[BlockSpan],
                     threshold: float = 0.2) -> list[BlockReconciliation]:
    out: list[BlockReconciliation] = []
    for s in spans:
        script_tok = _norm(_TOK.findall(s.narration))
        rec_tok = _norm([w.word for w in s.aligned_words])
        denom = max(len(script_tok), len(rec_tok), 1)
        ratio = _edit_distance(script_tok, rec_tok) / denom
        ratio = round(ratio, 4)
        out.append(BlockReconciliation(index=s.index, title=s.title,
                                       edit_ratio=ratio,
                                       deviation=ratio > threshold))
    return out


def render_reconcile_md(recs: list[BlockReconciliation]) -> str:
    lines = ["# Reconcile — отклонения записи от сценария", ""]
    for r in recs:
        status = "DEVIATION" if r.deviation else "OK"
        lines.append(
            f"- Блок {r.index + 1} «{r.title}»: edit_ratio={r.edit_ratio} — {status}"
        )
    return "\n".join(lines) + "\n"
