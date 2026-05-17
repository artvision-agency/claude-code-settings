from pathlib import Path

import yaml

SKILL = Path(__file__).parents[1] / "SKILL.md"
PRESET = Path(__file__).parents[1] / "presets" / "ai-course.yaml"


def _frontmatter(text: str) -> dict:
    assert text.startswith("---\n")
    end = text.index("\n---\n", 4)
    return yaml.safe_load(text[4:end])


def test_skill_md_exists_and_has_valid_frontmatter():
    text = SKILL.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    assert fm["name"] == "narration-to-visuals"
    assert "description" in fm and fm["description"].strip()
    assert fm.get("user-invocable") is True
    assert "argument-hint" in fm


def test_skill_md_documents_review_gate_1_as_hard_stop():
    text = SKILL.read_text(encoding="utf-8")
    assert "REVIEW GATE 1" in text
    assert "STOP" in text
    # шаг 0 SCRIPT-GEN описан
    assert "SCRIPT-GEN" in text
    # явно сказано, что План 2/3 — вне рамок текущей вехи
    assert "Plan 2" in text or "План 2" in text


def test_preset_yaml_matches_engine_preset():
    from nv_engine.config import PRESETS
    data = yaml.safe_load(PRESET.read_text(encoding="utf-8"))
    assert data["transcript"] == PRESETS["ai-course"]["transcript"]
    assert data["summary"] == PRESETS["ai-course"]["summary"]
    assert data["narration_script"] == PRESETS["ai-course"]["narration_script"]
    assert data["recording"] == PRESETS["ai-course"]["recording"]
    assert data["storyboard"] == PRESETS["ai-course"]["storyboard"]
    assert data["visualized"] == PRESETS["ai-course"]["visualized"]
    assert data["assets_dir"] == PRESETS["ai-course"]["assets_dir"]


def test_skill_md_documents_stage_2_and_gate_2():
    text = SKILL.read_text(encoding="utf-8")
    assert "REVIEW GATE 2" in text
    assert "--stage storyboard" in text
    assert "narration.mp4" in text
    # обновлён объём: вне рамок теперь только Plan 3
    assert "Plan 3" in text or "План 3" in text
