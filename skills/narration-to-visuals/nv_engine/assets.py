"""GENERATE step: produce the assets that don't exist yet.

Only B blocks need an external image (fal.ai); C/D are rendered by
Remotion from the storyboard content, so they pass through with no file.
Images are cached by sha256(prompt); a hard --max-cost cap is enforced
BEFORE each paid call so we never overspend.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from nv_engine.storyboard import Storyboard


class CostCapExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class AssetResult:
    index: int
    marker: str
    image_path: str | None  # relative to assets_dir, only for B
    cached: bool
    cost_usd: float


class ImageGenerator(Protocol):
    def generate(self, prompt: str, out_path: Path) -> float:
        """Write an image to out_path; return the USD cost actually spent."""
        ...


class FakeImageGenerator:
    """Deterministic test generator: writes a tiny fixed PNG, cost 0."""

    _PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00"
            b"\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc"
            b"\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str, out_path: Path) -> float:
        self.calls += 1
        out_path.write_bytes(self._PNG)
        return 0.0


def generate_assets(*, storyboard: Storyboard, assets_dir: Path,
                     generator: ImageGenerator, max_cost: float = 1.0,
                     cost_estimate: float = 0.04) -> list[AssetResult]:
    assets_dir.mkdir(parents=True, exist_ok=True)
    results: list[AssetResult] = []
    spent = 0.0
    for b in storyboard.blocks:
        if b.marker != "B":
            results.append(AssetResult(index=b.index, marker=b.marker,
                                       image_path=None, cached=False,
                                       cost_usd=0.0))
            continue
        prompt = str(b.content.get("image_prompt", "")).strip()
        h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]
        name = f"{b.index:03d}-{h}.png"
        path = assets_dir / name
        if path.exists():
            results.append(AssetResult(index=b.index, marker="B",
                                       image_path=name, cached=True,
                                       cost_usd=0.0))
            continue
        if spent + cost_estimate > max_cost:
            raise CostCapExceeded(
                f"--max-cost {max_cost} would be exceeded "
                f"(spent {spent:.4f} + est {cost_estimate:.4f}) "
                f"at block {b.index}; raise --max-cost or reduce B blocks"
            )
        cost = generator.generate(prompt, path)
        spent += cost
        results.append(AssetResult(index=b.index, marker="B",
                                    image_path=name, cached=False,
                                    cost_usd=cost))
    return results
