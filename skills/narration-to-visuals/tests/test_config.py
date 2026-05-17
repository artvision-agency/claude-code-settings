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


def test_resolve_paths_has_plan2_targets(tmp_path: Path):
    src = tmp_path / "source" / "cicd"
    src.mkdir(parents=True)
    (src / "transcript.json").write_text("{}", encoding="utf-8")
    (tmp_path / "course" / "cicd").mkdir(parents=True)

    p = resolve_paths(lecture="cicd", project_root=tmp_path, preset="ai-course")
    assert p.recording == src / "narration.mp4"
    assert p.aligned == tmp_path / ".nv-work" / "cicd" / "aligned.json"
    assert p.reconcile == tmp_path / ".nv-work" / "cicd" / "reconcile.md"
    assert p.storyboard == tmp_path / ".nv-work" / "cicd" / "storyboard.json"
    assert p.storyboard_md == tmp_path / ".nv-work" / "cicd" / "storyboard.md"


def test_resolve_paths_has_plan3_targets(tmp_path: Path):
    src = tmp_path / "source" / "cicd"
    src.mkdir(parents=True)
    (src / "transcript.json").write_text("{}", encoding="utf-8")
    (tmp_path / "course" / "cicd").mkdir(parents=True)

    p = resolve_paths(lecture="cicd", project_root=tmp_path, preset="ai-course")
    assert p.assets_dir == tmp_path / ".nv-work" / "cicd" / "assets"
    assert p.remotion_props == tmp_path / ".nv-work" / "cicd" / "remotion-props.json"
    assert p.visualized == src / "visualized.mp4"
    assert p.report == src / "nv-report.md"


def test_resolve_paths_has_remotion_public(tmp_path: Path):
    src = tmp_path / "source" / "cicd"
    src.mkdir(parents=True)
    (src / "transcript.json").write_text("{}", encoding="utf-8")
    (tmp_path / "course" / "cicd").mkdir(parents=True)
    p = resolve_paths(lecture="cicd", project_root=tmp_path, preset="ai-course")
    assert p.remotion_public == tmp_path / ".nv-work" / "cicd" / "remotion-public"
