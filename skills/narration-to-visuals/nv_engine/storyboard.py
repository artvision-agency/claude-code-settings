"""Storyboard: the Review Gate 2 artifact.

Assembled from the approved script blocks + recording timeline (segment) +
deviation flags (reconcile) + per-marker draft content (classify).
JSON is the machine artifact; .md is the human review view. A storyboard
is valid iff every block has a B/C/D marker, sequential indices, and
content shaped for its marker.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields

from nv_engine.classify import BlockContent
from nv_engine.reconcile import BlockReconciliation
from nv_engine.segment import BlockSpan


class StoryboardValidationError(ValueError):
    pass


@dataclass
class StoryboardBlock:
    index: int
    title: str
    marker: str
    start: float | None
    end: float | None
    narration: str
    deviation: bool
    content: dict = field(default_factory=dict)


@dataclass
class Storyboard:
    lecture: str
    blocks: list[StoryboardBlock]


def _content_dict(c: BlockContent) -> dict:
    d = asdict(c)
    return {k: v for k, v in d.items() if v is not None}


def build_storyboard(*, lecture: str, spans: list[BlockSpan],
                     recs: list[BlockReconciliation],
                     contents: list[BlockContent]) -> Storyboard:
    by_idx = {r.index: r for r in recs}
    blocks: list[StoryboardBlock] = []
    for s, c in zip(spans, contents):
        r = by_idx[s.index]
        blocks.append(StoryboardBlock(
            index=s.index, title=s.title, marker=s.marker,
            start=s.start, end=s.end, narration=s.narration,
            deviation=r.deviation, content=_content_dict(c),
        ))
    return Storyboard(lecture=lecture, blocks=blocks)


def render_storyboard_json(sb: Storyboard) -> str:
    return json.dumps(
        {"lecture": sb.lecture,
         "blocks": [asdict(b) for b in sb.blocks]},
        ensure_ascii=False, indent=2,
    )


_BLOCK_FIELDS = {f.name for f in fields(StoryboardBlock)}


def parse_storyboard_json(s: str) -> Storyboard:
    # storyboard.json правит автор на Гейте 2 — посторонний/битый ключ
    # должен дать понятный StoryboardValidationError, а не сырой TypeError
    # (его ловит CLI; это контракт, который потребляет Plan 3).
    data = json.loads(s)
    blocks: list[StoryboardBlock] = []
    for i, b in enumerate(data.get("blocks", [])):
        unknown = set(b) - _BLOCK_FIELDS
        if unknown:
            raise StoryboardValidationError(
                f"block {i}: unknown key(s) {sorted(unknown)}")
        try:
            blocks.append(StoryboardBlock(**b))
        except TypeError as e:  # отсутствует обязательное поле
            raise StoryboardValidationError(f"block {i}: {e}") from e
    return Storyboard(lecture=str(data.get("lecture", "")), blocks=blocks)


def render_storyboard_md(sb: Storyboard) -> str:
    lines = [f"# Storyboard — {sb.lecture}", ""]
    for b in sb.blocks:
        t = (f"{b.start:.2f}..{b.end:.2f}"
             if b.start is not None and b.end is not None else "—")
        dev = " ⚠️DEVIATION" if b.deviation else ""
        lines += [f"## Блок {b.index + 1} — {b.title}  [{b.marker}]  ({t}){dev}",
                  "", b.narration, "", f"`content`: {b.content}", ""]
    return "\n".join(lines) + "\n"


def validate_storyboard_json(s: str) -> None:
    sb = parse_storyboard_json(s)
    if not sb.blocks:
        raise StoryboardValidationError("storyboard has no blocks")
    for i, b in enumerate(sb.blocks):
        if b.index != i:
            raise StoryboardValidationError(
                f"block {i}: non-sequential index {b.index}")
        if b.marker not in {"B", "C", "D"}:
            raise StoryboardValidationError(
                f"block {i}: invalid marker {b.marker!r}")
        if not b.narration.strip():
            raise StoryboardValidationError(f"block {i}: empty narration")
        key = {"B": "image_prompt", "C": "slide_lines", "D": "diagram_spec"}[b.marker]
        if key not in b.content:
            raise StoryboardValidationError(
                f"block {i}: marker {b.marker} missing content key {key!r}")
