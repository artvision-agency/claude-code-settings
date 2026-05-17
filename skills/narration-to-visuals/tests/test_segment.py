from pathlib import Path

from nv_engine.align import FakeAligner, align_recording
from nv_engine.script_doc import parse_script_md
from nv_engine.segment import BlockSpan, map_blocks_to_timeline


def _parsed(mini_lecture: Path):
    return parse_script_md(
        (mini_lecture / "narration_script.md").read_text(encoding="utf-8")
    )


def test_spans_cover_every_block_in_order(mini_lecture):
    parsed = _parsed(mini_lecture)
    script_text = " ".join(b.narration for b in parsed.blocks)
    aligned = align_recording(recording=Path("n.mp4"),
                              script_text=script_text, aligner=FakeAligner())
    spans = map_blocks_to_timeline(parsed_script=parsed, aligned=aligned)
    assert [s.index for s in spans] == list(range(len(parsed.blocks)))
    assert all(isinstance(s, BlockSpan) for s in spans)
    assert [s.title for s in spans] == [b.title for b in parsed.blocks]
    assert [s.marker for s in spans] == [b.marker for b in parsed.blocks]


def test_spans_have_monotonic_nonoverlapping_times(mini_lecture):
    parsed = _parsed(mini_lecture)
    script_text = " ".join(b.narration for b in parsed.blocks)
    aligned = align_recording(recording=Path("n.mp4"),
                              script_text=script_text, aligner=FakeAligner())
    spans = map_blocks_to_timeline(parsed_script=parsed, aligned=aligned)
    timed = [s for s in spans if s.start is not None]
    assert timed
    for s in timed:
        assert s.end >= s.start
    for a, b in zip(timed, timed[1:]):
        assert b.start >= a.start


def test_all_aligned_words_distributed_no_loss(mini_lecture):
    parsed = _parsed(mini_lecture)
    script_text = " ".join(b.narration for b in parsed.blocks)
    aligned = align_recording(recording=Path("n.mp4"),
                              script_text=script_text, aligner=FakeAligner())
    spans = map_blocks_to_timeline(parsed_script=parsed, aligned=aligned)
    assigned = sum(len(s.aligned_words) for s in spans)
    assert assigned == len(aligned.words)
