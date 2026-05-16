import shutil
from pathlib import Path

from nv_engine.cli import main
from nv_engine.script_doc import parse_script_md, validate_script_md


def test_end_to_end_mini_lecture(tmp_path: Path, capsys, mini_lecture):
    # Полная раскладка ai-course со speaker_notes
    (tmp_path / "source" / "cicd").mkdir(parents=True)
    (tmp_path / "course" / "cicd").mkdir(parents=True)
    shutil.copy(mini_lecture / "transcript.json", tmp_path / "source" / "cicd" / "transcript.json")
    shutil.copy(mini_lecture / "summary.md", tmp_path / "course" / "cicd" / "summary.md")
    shutil.copy(mini_lecture / "speaker_notes.md", tmp_path / "course" / "cicd" / "speaker_notes.md")

    code = main(["cicd", "--project-root", str(tmp_path)])
    assert code == 0

    art = tmp_path / "source" / "cicd" / "narration_script.md"
    md = art.read_text(encoding="utf-8")
    validate_script_md(md)

    parsed = parse_script_md(md)
    assert parsed.lecture == "cicd"
    assert len(parsed.blocks) >= 3
    # каждый блок: валидный маркер + непустой текст + (если есть) корректный тайминг
    for b in parsed.blocks:
        assert b.marker in {"B", "C", "D"}
        assert b.narration.strip()
        if b.start is not None:
            assert b.end >= b.start
    # офтоп и филлеры не попали в финальный текст
    full = " ".join(b.narration for b in parsed.blocks)
    assert "пишет в чат" not in full
    assert "Эээ" not in full

    out = capsys.readouterr().out
    assert "REVIEW GATE 1" in out
