from nv_engine.assets import AssetResult
from nv_engine.report import render_report_md
from nv_engine.storyboard import parse_storyboard_json


def test_report_summarizes_run(mini_storyboard):
    sb = parse_storyboard_json(mini_storyboard)
    assets = [
        AssetResult(0, "C", None, False, 0.0),
        AssetResult(1, "D", None, False, 0.0),
        AssetResult(2, "B", "002-abc.png", False, 0.039),
    ]
    md = render_report_md(lecture="tech-debt", storyboard=sb,
                          asset_results=assets, video_path="visualized.mp4",
                          cost_usd=0.039)
    assert md.startswith("# narration-to-visuals — отчёт: tech-debt")
    assert "Блоков: 3" in md
    assert "B: 1" in md and "C: 1" in md and "D: 1" in md
    assert "$0.039" in md or "0.039" in md
    assert "visualized.mp4" in md
    assert "DEVIATION" in md  # секция есть даже если 0
