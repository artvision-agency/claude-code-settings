from pathlib import Path

from nv_engine.storyboard import parse_storyboard_json, validate_storyboard_json


def test_mini_has_approved_storyboard(mini_lecture: Path):
    s = (mini_lecture / "storyboard.json").read_text(encoding="utf-8")
    validate_storyboard_json(s)
    sb = parse_storyboard_json(s)
    assert sb.lecture == "tech-debt"
    assert [b.marker for b in sb.blocks] == ["C", "D", "B"]
    assert sb.blocks[2].content["image_prompt"]
    assert sb.blocks[0].content["slide_lines"]
    assert sb.blocks[1].content["diagram_spec"]
    assert all(b.start is not None and b.end is not None for b in sb.blocks)
