from pathlib import Path

from nv_engine.script_doc import parse_script_md, validate_script_md


def test_mini_has_approved_script(mini_lecture: Path):
    md = (mini_lecture / "narration_script.md").read_text(encoding="utf-8")
    validate_script_md(md)
    parsed = parse_script_md(md)
    assert parsed.lecture == "tech-debt"
    assert len(parsed.blocks) >= 2
    assert all(b.marker in {"B", "C", "D"} for b in parsed.blocks)
    assert all(b.narration.strip() for b in parsed.blocks)
