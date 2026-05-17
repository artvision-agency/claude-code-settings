import json
from pathlib import Path

import pytest

from nv_engine.align import FakeAligner, align_recording
from nv_engine.classify import draft_content
from nv_engine.reconcile import reconcile_blocks
from nv_engine.script_doc import parse_script_md
from nv_engine.segment import map_blocks_to_timeline
from nv_engine.storyboard import (
    StoryboardValidationError,
    build_storyboard,
    parse_storyboard_json,
    render_storyboard_json,
    render_storyboard_md,
    validate_storyboard_json,
)


def _pipeline(mini_lecture: Path, recognized=None):
    parsed = parse_script_md(
        (mini_lecture / "narration_script.md").read_text(encoding="utf-8")
    )
    txt = " ".join(b.narration for b in parsed.blocks)
    aligned = align_recording(recording=Path("n.mp4"), script_text=txt,
                              aligner=FakeAligner(recognized_text=recognized))
    spans = map_blocks_to_timeline(parsed_script=parsed, aligned=aligned)
    recs = reconcile_blocks(spans=spans, threshold=0.2)
    contents = [draft_content(title=s.title, marker=s.marker,
                              narration=s.narration) for s in spans]
    return parsed, spans, recs, contents


def test_build_storyboard_has_one_block_per_script_block(mini_lecture):
    parsed, spans, recs, contents = _pipeline(mini_lecture)
    sb = build_storyboard(lecture="tech-debt", spans=spans, recs=recs,
                          contents=contents)
    assert sb.lecture == "tech-debt"
    assert len(sb.blocks) == len(parsed.blocks)
    assert [b.index for b in sb.blocks] == list(range(len(parsed.blocks)))
    assert sb.blocks[0].marker in {"B", "C", "D"}
    assert sb.blocks[0].deviation is False


def test_json_round_trip(mini_lecture):
    _, spans, recs, contents = _pipeline(mini_lecture)
    sb = build_storyboard(lecture="tech-debt", spans=spans, recs=recs,
                          contents=contents)
    s = render_storyboard_json(sb)
    assert json.loads(s)["lecture"] == "tech-debt"
    back = parse_storyboard_json(s)
    assert back.lecture == sb.lecture
    assert [b.title for b in back.blocks] == [b.title for b in sb.blocks]
    assert back.blocks[0].content == sb.blocks[0].content


def test_render_md_human_view(mini_lecture):
    _, spans, recs, contents = _pipeline(mini_lecture)
    sb = build_storyboard(lecture="tech-debt", spans=spans, recs=recs,
                          contents=contents)
    md = render_storyboard_md(sb)
    assert md.startswith("# Storyboard — tech-debt")
    assert "Блок 1" in md


def test_validate_rejects_bad_marker(mini_lecture):
    _, spans, recs, contents = _pipeline(mini_lecture)
    sb = build_storyboard(lecture="tech-debt", spans=spans, recs=recs,
                          contents=contents)
    s = render_storyboard_json(sb).replace('"C"', '"Z"', 1)
    with pytest.raises(StoryboardValidationError, match="marker"):
        validate_storyboard_json(s)


def test_validate_accepts_good(mini_lecture):
    _, spans, recs, contents = _pipeline(mini_lecture)
    sb = build_storyboard(lecture="tech-debt", spans=spans, recs=recs,
                          contents=contents)
    validate_storyboard_json(render_storyboard_json(sb))


def test_parse_rejects_unknown_key(mini_lecture):
    _, spans, recs, contents = _pipeline(mini_lecture)
    sb = build_storyboard(lecture="tech-debt", spans=spans, recs=recs,
                          contents=contents)
    d = json.loads(render_storyboard_json(sb))
    d["blocks"][0]["EXTRA"] = 1  # автор случайно дописал лишний ключ
    with pytest.raises(StoryboardValidationError, match="unknown"):
        parse_storyboard_json(json.dumps(d))
