from pathlib import Path

import pytest

from nv_engine.assets import (
    AssetResult,
    CostCapExceeded,
    FakeImageGenerator,
    generate_assets,
)
from nv_engine.storyboard import parse_storyboard_json


def _sb(mini_storyboard):
    return parse_storyboard_json(mini_storyboard)


def test_only_B_blocks_generate_images(tmp_path, mini_storyboard):
    sb = _sb(mini_storyboard)
    res = generate_assets(storyboard=sb, assets_dir=tmp_path,
                          generator=FakeImageGenerator(), max_cost=1.0)
    assert all(isinstance(r, AssetResult) for r in res)
    assert [r.marker for r in res] == ["C", "D", "B"]
    assert res[0].image_path is None and res[1].image_path is None
    b = res[2]
    assert b.image_path is not None
    assert (tmp_path / b.image_path).exists()
    assert b.cached is False


def test_second_run_uses_cache(tmp_path, mini_storyboard):
    sb = _sb(mini_storyboard)
    gen = FakeImageGenerator()
    generate_assets(storyboard=sb, assets_dir=tmp_path, generator=gen,
                    max_cost=1.0)
    res2 = generate_assets(storyboard=sb, assets_dir=tmp_path, generator=gen,
                           max_cost=1.0)
    assert res2[2].cached is True
    assert gen.calls == 1  # второй раз генератор не звали


def test_cost_cap_raises_before_overspend(tmp_path, mini_storyboard):
    sb = _sb(mini_storyboard)
    with pytest.raises(CostCapExceeded, match="max-cost"):
        generate_assets(storyboard=sb, assets_dir=tmp_path,
                        generator=FakeImageGenerator(), max_cost=0.01,
                        cost_estimate=0.05)
