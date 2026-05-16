import shutil
from pathlib import Path

import pytest

from nv_engine.pipeline import ScriptGenResult, run_script_gen


def _ai_course_layout(tmp_path: Path, fixture: Path, lecture: str, with_notes: bool) -> Path:
    src = tmp_path / "source" / lecture
    src.mkdir(parents=True)
    course = tmp_path / "course" / lecture
    course.mkdir(parents=True)
    shutil.copy(fixture / "transcript.json", src / "transcript.json")
    shutil.copy(fixture / "summary.md", course / "summary.md")
    if with_notes and (fixture / "speaker_notes.md").exists():
        shutil.copy(fixture / "speaker_notes.md", course / "speaker_notes.md")
    return tmp_path


def test_run_script_gen_writes_valid_artifact(tmp_path, mini_lecture):
    root = _ai_course_layout(tmp_path, mini_lecture, "cicd", with_notes=True)
    res = run_script_gen(lecture="cicd", project_root=root, preset="ai-course")
    assert isinstance(res, ScriptGenResult)
    assert res.created is True
    out = root / "source" / "cicd" / "narration_script.md"
    assert out.exists()
    from nv_engine.script_doc import validate_script_md
    validate_script_md(out.read_text(encoding="utf-8"))
    # промежуточный brief сохранён
    assert (root / ".nv-work" / "cicd" / "script_brief.json").exists()


def test_idempotent_second_call_skips(tmp_path, mini_lecture):
    root = _ai_course_layout(tmp_path, mini_lecture, "cicd", with_notes=True)
    run_script_gen(lecture="cicd", project_root=root, preset="ai-course")
    out = root / "source" / "cicd" / "narration_script.md"
    out.write_text(out.read_text(encoding="utf-8") + "\n<!-- edited -->\n", encoding="utf-8")
    res2 = run_script_gen(lecture="cicd", project_root=root, preset="ai-course")
    assert res2.created is False  # не перезаписали
    assert "<!-- edited -->" in out.read_text(encoding="utf-8")


def test_force_regenerates(tmp_path, mini_lecture):
    root = _ai_course_layout(tmp_path, mini_lecture, "cicd", with_notes=True)
    run_script_gen(lecture="cicd", project_root=root, preset="ai-course")
    out = root / "source" / "cicd" / "narration_script.md"
    out.write_text("STALE", encoding="utf-8")
    res = run_script_gen(lecture="cicd", project_root=root, preset="ai-course", force=True)
    assert res.created is True
    assert out.read_text(encoding="utf-8") != "STALE"


def test_works_without_speaker_notes(tmp_path, nonotes_lecture):
    root = _ai_course_layout(tmp_path, nonotes_lecture, "logging", with_notes=False)
    res = run_script_gen(lecture="logging", project_root=root, preset="ai-course")
    assert res.created is True
    from nv_engine.script_doc import validate_script_md
    validate_script_md((root / "source" / "logging" / "narration_script.md").read_text("utf-8"))
