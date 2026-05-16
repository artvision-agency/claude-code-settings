import shutil
from pathlib import Path

from nv_engine.cli import main


def _layout(tmp_path: Path, fixture: Path, lecture: str) -> Path:
    (tmp_path / "source" / lecture).mkdir(parents=True)
    (tmp_path / "course" / lecture).mkdir(parents=True)
    shutil.copy(fixture / "transcript.json", tmp_path / "source" / lecture / "transcript.json")
    shutil.copy(fixture / "summary.md", tmp_path / "course" / lecture / "summary.md")
    return tmp_path


def test_cli_success(tmp_path, capsys, nonotes_lecture):
    root = _layout(tmp_path, nonotes_lecture, "logging")
    code = main(["logging", "--project-root", str(root)])
    assert code == 0
    out = capsys.readouterr().out
    assert "narration_script.md" in out
    assert "REVIEW GATE 1" in out
    assert (root / "source" / "logging" / "narration_script.md").exists()


def test_cli_idempotent_message(tmp_path, capsys, nonotes_lecture):
    root = _layout(tmp_path, nonotes_lecture, "logging")
    main(["logging", "--project-root", str(root)])
    capsys.readouterr()
    code = main(["logging", "--project-root", str(root)])
    assert code == 0
    assert "already exists" in capsys.readouterr().out


def test_cli_missing_lecture_returns_error(tmp_path, capsys):
    code = main(["ghost", "--project-root", str(tmp_path)])
    assert code == 2
    assert "transcript not found" in capsys.readouterr().err
