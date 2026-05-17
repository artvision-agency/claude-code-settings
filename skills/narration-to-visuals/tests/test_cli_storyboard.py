import shutil
from pathlib import Path

from nv_engine.cli import main


def _layout(tmp_path: Path, mini_lecture: Path) -> Path:
    src = tmp_path / "source" / "tech-debt"
    src.mkdir(parents=True)
    (tmp_path / "course" / "tech-debt").mkdir(parents=True)
    shutil.copy(mini_lecture / "transcript.json", src / "transcript.json")
    shutil.copy(mini_lecture / "summary.md",
                tmp_path / "course" / "tech-debt" / "summary.md")
    shutil.copy(mini_lecture / "narration_script.md", src / "narration_script.md")
    (src / "narration.mp4").write_bytes(b"\x00")
    return tmp_path


def test_default_stage_is_script_unchanged(tmp_path, capsys, nonotes_lecture):
    (tmp_path / "source" / "logging").mkdir(parents=True)
    (tmp_path / "course" / "logging").mkdir(parents=True)
    shutil.copy(nonotes_lecture / "transcript.json",
                tmp_path / "source" / "logging" / "transcript.json")
    shutil.copy(nonotes_lecture / "summary.md",
                tmp_path / "course" / "logging" / "summary.md")
    code = main(["logging", "--project-root", str(tmp_path)])
    assert code == 0
    assert "REVIEW GATE 1" in capsys.readouterr().out


def test_stage_storyboard_uses_fake_aligner_env(tmp_path, capsys, mini_lecture,
                                                 monkeypatch):
    root = _layout(tmp_path, mini_lecture)
    monkeypatch.setenv("NV_FAKE_ALIGNER", "1")
    code = main(["tech-debt", "--project-root", str(root),
                 "--stage", "storyboard"])
    assert code == 0
    out = capsys.readouterr().out
    assert "REVIEW GATE 2" in out
    assert (root / ".nv-work" / "tech-debt" / "storyboard.json").exists()


def test_stage_storyboard_missing_recording_errors(tmp_path, capsys,
                                                   mini_lecture, monkeypatch):
    root = _layout(tmp_path, mini_lecture)
    (root / "source" / "tech-debt" / "narration.mp4").unlink()
    monkeypatch.setenv("NV_FAKE_ALIGNER", "1")
    code = main(["tech-debt", "--project-root", str(root),
                 "--stage", "storyboard"])
    assert code == 2
    assert "narration.mp4" in capsys.readouterr().err
