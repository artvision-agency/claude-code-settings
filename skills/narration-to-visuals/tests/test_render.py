from pathlib import Path

import pytest

from nv_engine.render import FakeRunner, RenderError, render_video


def test_render_builds_cmd_and_writes_output(tmp_path):
    props = tmp_path / "remotion-props.json"
    props.write_text("{}", encoding="utf-8")
    out = tmp_path / "visualized.mp4"
    runner = FakeRunner()
    render_video(props_path=props, remotion_dir=tmp_path / "remotion",
                 out_path=out, runner=runner)
    assert out.exists()
    cmd = " ".join(runner.last_cmd)
    assert "remotion" in cmd and "render" in cmd
    assert str(out) in runner.last_cmd
    assert str(props) in runner.last_cmd


def test_render_raises_on_nonzero(tmp_path):
    props = tmp_path / "p.json"
    props.write_text("{}", encoding="utf-8")
    with pytest.raises(RenderError, match="exit 1"):
        render_video(props_path=props, remotion_dir=tmp_path,
                     out_path=tmp_path / "v.mp4",
                     runner=FakeRunner(returncode=1))


def test_render_raises_if_output_missing(tmp_path):
    props = tmp_path / "p.json"
    props.write_text("{}", encoding="utf-8")
    with pytest.raises(RenderError, match="no output"):
        render_video(props_path=props, remotion_dir=tmp_path,
                     out_path=tmp_path / "v.mp4",
                     runner=FakeRunner(write_output=False))
