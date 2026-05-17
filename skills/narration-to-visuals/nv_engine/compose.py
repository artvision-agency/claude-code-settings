"""COMPOSE step: storyboard + assets → remotion-props.json.

A pure-data description of the final composition that the Remotion
project consumes: 16:9 1080p, per-block background (B image+Ken Burns /
C slide / D diagram) laid contiguously on the timeline, a corner PiP of
the webcam (24% width, bottom-right) and the narration audio. No
subtitles (design decision). Times come from the storyboard (recording
timeline); blocks without times fall back to a 3s slot after the
previous block — never zero-length, never overlapping.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from nv_engine.assets import AssetResult
from nv_engine.storyboard import Storyboard

_DEFAULT_SECONDS = 3.0


class PropsValidationError(ValueError):
    pass


@dataclass(frozen=True)
class RemotionProps:
    fps: int
    width: int
    height: int
    audio_src: str
    pip: dict
    blocks: list[dict]


def build_props(*, storyboard: Storyboard, asset_results: list[AssetResult],
                narration_rel: str, fps: int = 30,
                width: int = 1920, height: int = 1080) -> RemotionProps:
    by_idx = {a.index: a for a in asset_results}
    blocks: list[dict] = []
    cursor = 0
    for b in storyboard.blocks:
        if b.start is not None and b.end is not None and b.end > b.start:
            dur = max(1, round((b.end - b.start) * fps))
        else:
            dur = max(1, round(_DEFAULT_SECONDS * fps))
        entry = {
            "index": b.index,
            "marker": b.marker,
            "title": b.title,
            "fromFrame": cursor,
            "durationFrames": dur,
            "slideLines": b.content.get("slide_lines"),
            "diagramSpec": b.content.get("diagram_spec"),
            "imageSrc": None,
        }
        if b.marker == "B":
            a = by_idx.get(b.index)
            entry["imageSrc"] = a.image_path if a else None
        blocks.append(entry)
        cursor += dur
    pip = {"src": narration_rel, "widthPct": 0.24,
           "corner": "bottom-right", "marginPct": 0.04}
    return RemotionProps(fps=fps, width=width, height=height,
                         audio_src=narration_rel, pip=pip, blocks=blocks)


def render_props_json(props: RemotionProps) -> str:
    # JSON-контракт — camelCase (как fromFrame/imageSrc/widthPct и т.д.),
    # его читает Main.tsx. asdict даёт audio_src → переименовываем в audioSrc.
    d = asdict(props)
    d["audioSrc"] = d.pop("audio_src")
    return json.dumps(d, ensure_ascii=False, indent=2)


def validate_props_json(s: str) -> None:
    data = json.loads(s)
    if not data.get("blocks"):
        raise PropsValidationError("no blocks")
    if data["pip"]["widthPct"] <= 0 or data["pip"]["widthPct"] >= 1:
        raise PropsValidationError("pip widthPct must be in (0,1)")
    expect = 0
    for i, b in enumerate(data["blocks"]):
        if b["marker"] not in {"B", "C", "D"}:
            raise PropsValidationError(f"block {i}: bad marker {b['marker']!r}")
        if b["durationFrames"] <= 0:
            raise PropsValidationError(f"block {i}: durationFrames must be > 0")
        if b["fromFrame"] != expect:
            raise PropsValidationError(
                f"block {i}: fromFrame {b['fromFrame']} != expected {expect} "
                f"(timeline must be contiguous)")
        if b["marker"] == "B" and not b.get("imageSrc"):
            raise PropsValidationError(f"block {i}: B block missing imageSrc")
        if b["marker"] == "C" and not b.get("slideLines"):
            raise PropsValidationError(f"block {i}: C block missing slideLines")
        if b["marker"] == "D" and not b.get("diagramSpec"):
            raise PropsValidationError(f"block {i}: D block missing diagramSpec")
        expect += b["durationFrames"]
