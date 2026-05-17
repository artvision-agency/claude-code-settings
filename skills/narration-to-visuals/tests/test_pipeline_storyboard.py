import shutil
from pathlib import Path

import pytest

from nv_engine.align import FakeAligner
from nv_engine.pipeline import StoryboardResult, run_storyboard
from nv_engine.storyboard import validate_storyboard_json


def _layout(tmp_path: Path, mini_lecture: Path, lecture="tech-debt",
            with_recording=True) -> Path:
    src = tmp_path / "source" / lecture
    src.mkdir(parents=True)
    (tmp_path / "course" / lecture).mkdir(parents=True)
    shutil.copy(mini_lecture / "transcript.json", src / "transcript.json")
    shutil.copy(mini_lecture / "summary.md",
                tmp_path / "course" / lecture / "summary.md")
    shutil.copy(mini_lecture / "narration_script.md", src / "narration_script.md")
    if with_recording:
        (src / "narration.mp4").write_bytes(b"\x00")  # FakeAligner ignores bytes
    return tmp_path


def test_run_storyboard_writes_valid_artifacts(tmp_path, mini_lecture):
    root = _layout(tmp_path, mini_lecture)
    res = run_storyboard(lecture="tech-debt", project_root=root,
                         preset="ai-course", aligner=FakeAligner())
    assert isinstance(res, StoryboardResult)
    assert res.created is True
    w = root / ".nv-work" / "tech-debt"
    assert (w / "aligned.json").exists()
    assert (w / "reconcile.md").exists()
    assert (w / "storyboard.md").exists()
    sb_json = (w / "storyboard.json").read_text(encoding="utf-8")
    validate_storyboard_json(sb_json)
    assert res.block_count >= 2


def test_missing_recording_raises(tmp_path, mini_lecture):
    root = _layout(tmp_path, mini_lecture, with_recording=False)
    with pytest.raises(FileNotFoundError, match="narration.mp4"):
        run_storyboard(lecture="tech-debt", project_root=root,
                       preset="ai-course", aligner=FakeAligner())


def test_missing_script_raises(tmp_path, mini_lecture):
    root = _layout(tmp_path, mini_lecture)
    (root / "source" / "tech-debt" / "narration_script.md").unlink()
    with pytest.raises(FileNotFoundError, match="narration_script.md"):
        run_storyboard(lecture="tech-debt", project_root=root,
                       preset="ai-course", aligner=FakeAligner())


def test_idempotent_unless_force(tmp_path, mini_lecture):
    root = _layout(tmp_path, mini_lecture)
    run_storyboard(lecture="tech-debt", project_root=root,
                   preset="ai-course", aligner=FakeAligner())
    sb = root / ".nv-work" / "tech-debt" / "storyboard.json"
    sb.write_text(sb.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    marker = sb.read_text(encoding="utf-8")
    res2 = run_storyboard(lecture="tech-debt", project_root=root,
                          preset="ai-course", aligner=FakeAligner())
    assert res2.created is False
    assert sb.read_text(encoding="utf-8") == marker  # не перезаписан
    res3 = run_storyboard(lecture="tech-debt", project_root=root,
                          preset="ai-course", aligner=FakeAligner(),
                          force=True)
    assert res3.created is True
