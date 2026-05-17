"""Real fal.ai image generator (import name: fal_client).

Paid + network, so isolated behind a factory with guard import + API-key
check. Unit tests use FakeImageGenerator; this runs only when fal_client
is installed and FAL_KEY is set (integration). Satisfies the
ImageGenerator protocol from assets.py.
"""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path

_MODEL = "fal-ai/nano-banana"
_COST_USD = 0.039  # ориентир Nano Banana; фактический счёт — у fal


class FalImageGenerator:
    def __init__(self, client) -> None:
        self._client = client

    def generate(self, prompt: str, out_path: Path) -> float:
        result = self._client.subscribe(
            _MODEL, arguments={"prompt": prompt, "image_size": "landscape_16_9"}
        )
        url = result["images"][0]["url"]
        with urllib.request.urlopen(url, timeout=120) as r:  # noqa: S310
            out_path.write_bytes(r.read())
        return _COST_USD


def make_fal_generator() -> FalImageGenerator:
    try:
        import fal_client  # noqa: PLC0415
    except ImportError as e:  # pragma: no cover - exercised via monkeypatch
        raise RuntimeError(
            "fal-client not installed. `pip install fal-client` "
            "to run the render stage with real B images."
        ) from e
    if not os.environ.get("FAL_KEY"):
        raise RuntimeError(
            "FAL_KEY env var not set — required for fal.ai image generation."
        )
    return FalImageGenerator(fal_client)
