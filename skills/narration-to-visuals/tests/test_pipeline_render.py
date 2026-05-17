import shutil
from pathlib import Path

import pytest

from nv_engine.assets import FakeImageGenerator
from nv_engine.pipeline import RenderResult, run_render
from nv_engine.render import FakeRunner


def _layout(tmp_path: Path, mini_lecture: Path, with_sb=True,
            with_rec=True) -> Path:
    src = tmp_path / "source" / "tech-debt"
    src.mkdir(parents=True)
    work = tmp_path / ".nv-work" / "tech-debt"
    work.mkdir(parents=True)
    # transcript.json всегда есть в реальной раскладке ai-course (вход Plan 1)
    # и нужен resolve_paths; без него тест падал бы на "transcript not found".
    shutil.copy(mini_lecture / "transcript.json", src / "transcript.json")
    if with_rec:
        (src / "narration.mp4").write_bytes(b"\x00")
    if with_sb:
        shutil.copy(mini_lecture / "storyboard.json", work / "storyboard.json")
    return tmp_path


def test_run_render_produces_video_and_report(tmp_path, mini_lecture):
    root = _layout(tmp_path, mini_lecture)
    res = run_render(lecture="tech-debt", project_root=root,
                     preset="ai-course", image_generator=FakeImageGenerator(),
                     runner=FakeRunner())
    assert isinstance(res, RenderResult)
    assert res.created is True
    assert (root / "source" / "tech-debt" / "visualized.mp4").exists()
    assert (root / "source" / "tech-debt" / "nv-report.md").exists()
    assert (root / ".nv-work" / "tech-debt" / "remotion-props.json").exists()
    assert res.generated_images == 1


def test_missing_storyboard_raises(tmp_path, mini_lecture):
    root = _layout(tmp_path, mini_lecture, with_sb=False)
    with pytest.raises(FileNotFoundError, match="storyboard.json"):
        run_render(lecture="tech-debt", project_root=root, preset="ai-course",
                   image_generator=FakeImageGenerator(), runner=FakeRunner())


def test_missing_recording_raises(tmp_path, mini_lecture):
    root = _layout(tmp_path, mini_lecture, with_rec=False)
    with pytest.raises(FileNotFoundError, match="narration.mp4"):
        run_render(lecture="tech-debt", project_root=root, preset="ai-course",
                   image_generator=FakeImageGenerator(), runner=FakeRunner())


def test_idempotent_unless_force(tmp_path, mini_lecture):
    root = _layout(tmp_path, mini_lecture)
    run_render(lecture="tech-debt", project_root=root, preset="ai-course",
               image_generator=FakeImageGenerator(), runner=FakeRunner())
    vid = root / "source" / "tech-debt" / "visualized.mp4"
    vid.write_bytes(b"EDITED")
    res2 = run_render(lecture="tech-debt", project_root=root,
                      preset="ai-course", image_generator=FakeImageGenerator(),
                      runner=FakeRunner())
    assert res2.created is False
    assert vid.read_bytes() == b"EDITED"
    res3 = run_render(lecture="tech-debt", project_root=root,
                      preset="ai-course", image_generator=FakeImageGenerator(),
                      runner=FakeRunner(), force=True)
    assert res3.created is True
    assert vid.read_bytes() != b"EDITED"
