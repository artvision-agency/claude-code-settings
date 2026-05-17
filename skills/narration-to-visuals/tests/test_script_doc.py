import pytest

from nv_engine.scriptgen import Block
from nv_engine.script_doc import (
    ScriptValidationError,
    parse_script_md,
    render_script_md,
    validate_script_md,
)


def _blocks():
    b1 = Block(title="Определение", summary_body="")
    b1.narration = "Тех-долг это осознанный компромисс."
    b1.start, b1.end, b1.marker = 12.0, 28.0, "C"
    b2 = Block(title="Источники", summary_body="")
    b2.narration = "Хардкоды, пропущенные тесты, CI/CD pipeline."
    b2.start, b2.end, b2.marker = 31.0, 52.0, "D"
    return [b1, b2]


def test_render_contains_frontmatter_and_blocks():
    md = render_script_md(lecture="cicd", blocks=_blocks())
    assert md.startswith("---\n")
    assert "lecture: cicd" in md
    assert "## Блок 1 — Определение" in md
    assert "[C: " in md and "[D: " in md
    assert "<!-- t=12.00..28.00 -->" in md


def test_round_trip_parse():
    md = render_script_md(lecture="cicd", blocks=_blocks())
    parsed = parse_script_md(md)
    assert parsed.lecture == "cicd"
    assert len(parsed.blocks) == 2
    assert parsed.blocks[0].marker == "C"
    assert parsed.blocks[1].title == "Источники"
    assert parsed.blocks[0].narration.startswith("Тех-долг")


def test_validate_rejects_block_without_marker():
    bad = "---\nlecture: x\n---\n\n## Блок 1 — Нет маркера\n\nТекст без маркера.\n"
    with pytest.raises(ScriptValidationError, match="marker"):
        validate_script_md(bad)


def test_validate_rejects_empty_narration():
    bad = "---\nlecture: x\n---\n\n## Блок 1 — Пусто\n\n[C: слайд]\n"
    with pytest.raises(ScriptValidationError, match="narration"):
        validate_script_md(bad)


def test_validate_accepts_good_doc():
    good = render_script_md(lecture="cicd", blocks=_blocks())
    validate_script_md(good)  # не бросает
