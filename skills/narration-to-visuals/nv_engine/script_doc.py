"""Schema, renderer and parser for the narration_script.md artifact.

Format (the artifact the author reads on review gate #1):

    ---
    lecture: <name>
    generated_by: nv_engine
    review_status: draft
    ---

    > Прочитайте вслух текст блоков. [B/C/D: ...] — подсказка визуала, НЕ читать.

    ## Блок 1 — <title>
    <!-- t=<start>..<end> -->

    [C: краткая подсказка визуала]

    <narration text to read aloud>

A block is valid iff it has a [B|C|D: ...] marker line AND non-empty narration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

from nv_engine.scriptgen import Block

_FM = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_BLOCK = re.compile(
    r"^##\s+Блок\s+\d+\s+—\s+(?P<title>.+?)\s*$"
    r"(?:\n<!--\s*t=(?P<start>[\d.]+)\.\.(?P<end>[\d.]+)\s*-->)?"
    r"\n+\[(?P<marker>[BCD]):\s*(?P<hint>[^\]]*)\]"
    r"\n+(?P<narration>.*?)(?=\n##\s+Блок\s|\Z)",
    re.DOTALL | re.MULTILINE,
)

_PREAMBLE = (
    "> Прочитайте вслух **только текст блоков**. "
    "Строки `[B/C/D: ...]` — подсказка визуала, их читать не нужно. "
    "Маркеры и текст можно править — это ревью №1.\n"
)


class ScriptValidationError(ValueError):
    pass


@dataclass
class ParsedScript:
    lecture: str
    blocks: list[Block]


def render_script_md(*, lecture: str, blocks: list[Block]) -> str:
    fm = yaml.safe_dump(
        {"lecture": lecture, "generated_by": "nv_engine", "review_status": "draft"},
        allow_unicode=True,
        sort_keys=False,
    ).strip()
    parts = [f"---\n{fm}\n---\n", _PREAMBLE]
    for i, b in enumerate(blocks, 1):
        parts.append(f"\n## Блок {i} — {b.title}")
        if b.start is not None and b.end is not None:
            parts.append(f"\n<!-- t={b.start:.2f}..{b.end:.2f} -->")
        marker = b.marker or "C"
        hint = (b.title if not b.summary_body else b.title).strip()
        parts.append(f"\n\n[{marker}: {hint}]\n")
        parts.append(f"\n{b.narration.strip()}\n")
    return "".join(parts)


def parse_script_md(md: str) -> ParsedScript:
    m = _FM.search(md)
    meta = yaml.safe_load(m.group(1)) if m else {}
    blocks: list[Block] = []
    for bm in _BLOCK.finditer(md):
        b = Block(title=bm.group("title").strip(), summary_body="")
        b.marker = bm.group("marker")
        b.narration = bm.group("narration").strip()
        if bm.group("start"):
            b.start = float(bm.group("start"))
            b.end = float(bm.group("end"))
        blocks.append(b)
    return ParsedScript(lecture=str(meta.get("lecture", "")), blocks=blocks)


def validate_script_md(md: str) -> None:
    if not _FM.search(md):
        raise ScriptValidationError("missing YAML frontmatter")
    headers = re.findall(r"^##\s+Блок\s+\d+\s+—\s+.+$", md, re.MULTILINE)
    parsed = parse_script_md(md)
    if len(parsed.blocks) != len(headers):
        raise ScriptValidationError(
            f"block(s) missing a valid [B/C/D: ...] marker line: "
            f"{len(headers)} headers vs {len(parsed.blocks)} valid blocks"
        )
    for i, b in enumerate(parsed.blocks, 1):
        if b.marker not in {"B", "C", "D"}:
            raise ScriptValidationError(f"block {i}: invalid marker {b.marker!r}")
        if not b.narration.strip():
            raise ScriptValidationError(f"block {i}: empty narration")
