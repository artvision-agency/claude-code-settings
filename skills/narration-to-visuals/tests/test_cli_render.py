import shutil
from pathlib import Path

from nv_engine.cli import main


def _layout(tmp_path: Path, mini_lecture: Path) -> Path:
    src = tmp_path / "source" / "tech-debt"
    src.mkdir(parents=True)
    work = tmp_path / ".nv-work" / "tech-debt"
    work.mkdir(parents=True)
    shutil.copy(mini_lecture / "transcript.json", src / "transcript.json")
    (src / "narration.mp4").write_bytes(b"\x00")
    shutil.copy(mini_lecture / "storyboard.json", work / "storyboard.json")
    return tmp_path


def test_stage_render_fake_env(tmp_path, capsys, mini_lecture, monkeypatch):
    root = _layout(tmp_path, mini_lecture)
    monkeypatch.setenv("NV_FAKE_ASSETS", "1")
    monkeypatch.setenv("NV_FAKE_RENDER", "1")
    code = main(["tech-debt", "--project-root", str(root),
                 "--stage", "render"])
    assert code == 0
    out = capsys.readouterr().out
    assert "RENDER done" in out
    assert "visualized.mp4" in out
    assert (root / "source" / "tech-debt" / "visualized.mp4").exists()


def test_stage_render_missing_storyboard_errors(tmp_path, capsys,
                                                mini_lecture, monkeypatch):
    src = tmp_path / "source" / "tech-debt"
    src.mkdir(parents=True)
    shutil.copy(mini_lecture / "transcript.json", src / "transcript.json")
    (src / "narration.mp4").write_bytes(b"\x00")
    monkeypatch.setenv("NV_FAKE_ASSETS", "1")
    monkeypatch.setenv("NV_FAKE_RENDER", "1")
    code = main(["tech-debt", "--project-root", str(tmp_path),
                 "--stage", "render"])
    assert code == 2
    assert "storyboard.json" in capsys.readouterr().err


def test_default_stage_still_script(tmp_path, capsys, nonotes_lecture):
    (tmp_path / "source" / "logging").mkdir(parents=True)
    (tmp_path / "course" / "logging").mkdir(parents=True)
    shutil.copy(nonotes_lecture / "transcript.json",
                tmp_path / "source" / "logging" / "transcript.json")
    shutil.copy(nonotes_lecture / "summary.md",
                tmp_path / "course" / "logging" / "summary.md")
    assert main(["logging", "--project-root", str(tmp_path)]) == 0
    assert "REVIEW GATE 1" in capsys.readouterr().out
