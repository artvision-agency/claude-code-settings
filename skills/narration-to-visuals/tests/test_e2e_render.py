import shutil
from pathlib import Path

from nv_engine.cli import main
from nv_engine.compose import validate_props_json


def test_e2e_storyboard_to_render(tmp_path: Path, capsys, mini_lecture,
                                  monkeypatch):
    # Старт с утверждённой раскадровки (Гейт 2 пройден) + запись
    src = tmp_path / "source" / "tech-debt"
    src.mkdir(parents=True)
    work = tmp_path / ".nv-work" / "tech-debt"
    work.mkdir(parents=True)
    shutil.copy(mini_lecture / "transcript.json", src / "transcript.json")
    (src / "narration.mp4").write_bytes(b"\x00")
    shutil.copy(mini_lecture / "storyboard.json", work / "storyboard.json")

    monkeypatch.setenv("NV_FAKE_ASSETS", "1")
    monkeypatch.setenv("NV_FAKE_RENDER", "1")
    assert main(["tech-debt", "--project-root", str(tmp_path),
                 "--stage", "render"]) == 0
    out = capsys.readouterr().out
    assert "RENDER done" in out
    assert "no further gate" in out or "no further" in out

    assert (src / "visualized.mp4").exists()
    report = (src / "nv-report.md").read_text(encoding="utf-8")
    assert "tech-debt" in report and "B: 1" in report

    props = (work / "remotion-props.json").read_text(encoding="utf-8")
    validate_props_json(props)
    assert (work / "assets").is_dir()
    pngs = list((work / "assets").glob("*.png"))
    assert len(pngs) == 1  # один B-блок
