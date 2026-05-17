from pathlib import Path

from nv_engine.align import FakeAligner, align_recording
from nv_engine.reconcile import (
    BlockReconciliation,
    reconcile_blocks,
    render_reconcile_md,
)
from nv_engine.script_doc import parse_script_md
from nv_engine.segment import map_blocks_to_timeline


def _setup(mini_lecture: Path, recognized=None):
    parsed = parse_script_md(
        (mini_lecture / "narration_script.md").read_text(encoding="utf-8")
    )
    script_text = " ".join(b.narration for b in parsed.blocks)
    aligned = align_recording(recording=Path("n.mp4"), script_text=script_text,
                              aligner=FakeAligner(recognized_text=recognized))
    spans = map_blocks_to_timeline(parsed_script=parsed, aligned=aligned)
    return parsed, spans


def test_perfect_read_has_no_deviation(mini_lecture):
    parsed, spans = _setup(mini_lecture)
    recs = reconcile_blocks(spans=spans, threshold=0.2)
    assert all(isinstance(r, BlockReconciliation) for r in recs)
    assert len(recs) == len(parsed.blocks)
    assert all(r.edit_ratio == 0.0 for r in recs)
    assert not any(r.deviation for r in recs)


def test_garbled_recording_flags_deviation(mini_lecture):
    # запись полностью не совпадает со скриптом
    _, spans = _setup(mini_lecture,
                       recognized="ля ля ля ля ля ля ля ля ля ля ля ля")
    recs = reconcile_blocks(spans=spans, threshold=0.2)
    assert any(r.deviation for r in recs)
    assert any(r.edit_ratio > 0.2 for r in recs)


def test_render_reconcile_md_lists_blocks(mini_lecture):
    _, spans = _setup(mini_lecture)
    md = render_reconcile_md(reconcile_blocks(spans=spans, threshold=0.2))
    assert md.startswith("# Reconcile")
    assert "Блок 1" in md
    assert "OK" in md  # нет отклонений при идеальном чтении
