import json

import pytest

from nv_engine.assets import FakeImageGenerator, generate_assets
from nv_engine.compose import (
    PropsValidationError,
    build_props,
    render_props_json,
    validate_props_json,
)
from nv_engine.storyboard import parse_storyboard_json


def _ctx(tmp_path, mini_storyboard):
    sb = parse_storyboard_json(mini_storyboard)
    assets = generate_assets(storyboard=sb, assets_dir=tmp_path / "assets",
                             generator=FakeImageGenerator(), max_cost=1.0)
    return sb, assets


def test_props_layout_and_pip(tmp_path, mini_storyboard):
    sb, assets = _ctx(tmp_path, mini_storyboard)
    p = build_props(storyboard=sb, asset_results=assets,
                    narration_rel="narration.mp4", fps=30)
    assert p.fps == 30 and p.width == 1920 and p.height == 1080
    assert p.audio_src == "narration.mp4"
    assert p.pip == {"src": "narration.mp4", "widthPct": 0.24,
                     "corner": "bottom-right", "marginPct": 0.04}
    assert len(p.blocks) == 3


def test_block_frames_contiguous_and_typed(tmp_path, mini_storyboard):
    sb, assets = _ctx(tmp_path, mini_storyboard)
    p = build_props(storyboard=sb, asset_results=assets,
                    narration_rel="narration.mp4", fps=30)
    b0, b1, b2 = p.blocks
    assert b0["fromFrame"] == 0
    assert b0["durationFrames"] == round((28.0 - 12.0) * 30)
    assert b1["fromFrame"] == b0["fromFrame"] + b0["durationFrames"]
    assert b2["fromFrame"] == b1["fromFrame"] + b1["durationFrames"]
    assert b0["marker"] == "C" and b0["slideLines"]
    assert b0["title"] == "Новое определение"
    assert b1["marker"] == "D" and b1["diagramSpec"]
    assert b2["marker"] == "B" and b2["imageSrc"].endswith(".png")


def test_json_round_trip_and_validate(tmp_path, mini_storyboard):
    sb, assets = _ctx(tmp_path, mini_storyboard)
    s = render_props_json(build_props(storyboard=sb, asset_results=assets,
                                      narration_rel="narration.mp4", fps=30))
    data = json.loads(s)
    assert data["pip"]["widthPct"] == 0.24
    assert data["audioSrc"] == "narration.mp4"
    assert "audio_src" not in data
    validate_props_json(s)  # не бросает


def test_validate_rejects_zero_duration(tmp_path, mini_storyboard):
    sb, assets = _ctx(tmp_path, mini_storyboard)
    s = render_props_json(build_props(storyboard=sb, asset_results=assets,
                                      narration_rel="narration.mp4", fps=30))
    bad = json.loads(s)
    bad["blocks"][0]["durationFrames"] = 0
    with pytest.raises(PropsValidationError, match="durationFrames"):
        validate_props_json(json.dumps(bad))
