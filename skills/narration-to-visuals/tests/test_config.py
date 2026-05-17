from pathlib import Path

import pytest

from nv_engine.config import LecturePaths, resolve_paths


def test_resolve_paths_ai_course_preset(tmp_path: Path):
    # Имитируем раскладку ai-course
    src = tmp_path / "source" / "cicd"
    src.mkdir(parents=True)
    (src / "transcript.json").write_text("{}", encoding="utf-8")
    course = tmp_path / "course" / "cicd"
    course.mkdir(parents=True)
    (course / "summary.md").write_text("# s", encoding="utf-8")

    paths = resolve_paths(lecture="cicd", project_root=tmp_path, preset="ai-course")

    assert isinstance(paths, LecturePaths)
    assert paths.transcript == src / "transcript.json"
    assert paths.summary == course / "summary.md"
    assert paths.speaker_notes is None  # нет файла
    assert paths.narration_script == src / "narration_script.md"
    assert paths.work_dir == tmp_path / ".nv-work" / "cicd"


def test_resolve_paths_detects_speaker_notes(tmp_path: Path):
    src = tmp_path / "source" / "ai-history"
    src.mkdir(parents=True)
    (src / "transcript.json").write_text("{}", encoding="utf-8")
    course = tmp_path / "course" / "ai-history"
    course.mkdir(parents=True)
    (course / "summary.md").write_text("# s", encoding="utf-8")
    (course / "speaker_notes.md").write_text("# sn", encoding="utf-8")

    paths = resolve_paths(lecture="ai-history", project_root=tmp_path, preset="ai-course")

    assert paths.speaker_notes == course / "speaker_notes.md"


def test_resolve_paths_missing_transcript_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="transcript"):
        resolve_paths(lecture="ghost", project_root=tmp_path, preset="ai-course")


def test_resolve_paths_unknown_preset_raises(tmp_path: Path):
    with pytest.raises(ValueError, match="unknown"):
        resolve_paths(lecture="x", project_root=tmp_path, preset="no-such-preset")
