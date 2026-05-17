import shutil
from pathlib import Path

from nv_engine.cli import main
from nv_engine.storyboard import parse_storyboard_json, validate_storyboard_json


def test_e2e_script_then_storyboard(tmp_path: Path, capsys, mini_lecture,
                                    monkeypatch):
    src = tmp_path / "source" / "tech-debt"
    src.mkdir(parents=True)
    (tmp_path / "course" / "tech-debt").mkdir(parents=True)
    shutil.copy(mini_lecture / "transcript.json", src / "transcript.json")
    shutil.copy(mini_lecture / "summary.md",
                tmp_path / "course" / "tech-debt" / "summary.md")

    # Стадия 1: SCRIPT-GEN
    assert main(["tech-debt", "--project-root", str(tmp_path)]) == 0
    assert "REVIEW GATE 1" in capsys.readouterr().out
    script = src / "narration_script.md"
    assert script.exists()

    # автор «записал» чтение скрипта
    (src / "narration.mp4").write_bytes(b"\x00")
    monkeypatch.setenv("NV_FAKE_ALIGNER", "1")

    # Стадия 2: STORYBOARD
    assert main(["tech-debt", "--project-root", str(tmp_path),
                 "--stage", "storyboard"]) == 0
    out = capsys.readouterr().out
    assert "REVIEW GATE 2" in out

    sb_path = tmp_path / ".nv-work" / "tech-debt" / "storyboard.json"
    s = sb_path.read_text(encoding="utf-8")
    validate_storyboard_json(s)
    sb = parse_storyboard_json(s)
    assert sb.lecture == "tech-debt"
    assert len(sb.blocks) >= 2
    for b in sb.blocks:
        assert b.marker in {"B", "C", "D"}
        assert b.narration.strip()
        key = {"B": "image_prompt", "C": "slide_lines", "D": "diagram_spec"}[b.marker]
        assert key in b.content
    w = tmp_path / ".nv-work" / "tech-debt"
    assert (w / "aligned.json").exists() and (w / "reconcile.md").exists()
