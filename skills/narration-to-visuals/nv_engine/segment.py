"""Map approved-script blocks onto the recording timeline.

Deterministic proportional allocation: aligned words are split across
blocks in order, proportionally to each block's narration token count.
Good enough for a DRAFT timeline (author refines at Gate 2; Plan 3 uses
these times for visual cues). No content is lost — every aligned word is
assigned to exactly one block.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from nv_engine.align import AlignedTranscript, AlignedWord
from nv_engine.script_doc import ParsedScript

_TOK = re.compile(r"\S+")


@dataclass(frozen=True)
class BlockSpan:
    index: int
    title: str
    marker: str
    narration: str
    start: float | None
    end: float | None
    aligned_words: list[AlignedWord]


def _token_count(text: str) -> int:
    return len(_TOK.findall(text))


def map_blocks_to_timeline(*, parsed_script: ParsedScript,
                           aligned: AlignedTranscript) -> list[BlockSpan]:
    blocks = parsed_script.blocks
    words = aligned.words
    total_tok = sum(_token_count(b.narration) for b in blocks) or 1
    n_words = len(words)

    spans: list[BlockSpan] = []
    cursor = 0
    allocated = 0
    for i, b in enumerate(blocks):
        if i == len(blocks) - 1:
            take = n_words - cursor  # last block gets the remainder
        else:
            share = _token_count(b.narration) / total_tok
            take = round(share * n_words)
            take = max(0, min(take, n_words - cursor))
        chunk = words[cursor:cursor + take]
        cursor += take
        allocated += len(chunk)
        if chunk:
            start: float | None = chunk[0].start
            end: float | None = chunk[-1].end
        else:
            start = end = None
        spans.append(BlockSpan(index=i, title=b.title, marker=b.marker or "C",
                               narration=b.narration, start=start, end=end,
                               aligned_words=list(chunk)))
    return spans
