"""REPORT step: human-readable nv-report.md of the render run."""

from __future__ import annotations

from collections import Counter

from nv_engine.assets import AssetResult
from nv_engine.storyboard import Storyboard


def render_report_md(*, lecture: str, storyboard: Storyboard,
                     asset_results: list[AssetResult], video_path: str,
                     cost_usd: float) -> str:
    counts = Counter(b.marker for b in storyboard.blocks)
    devs = [b for b in storyboard.blocks if b.deviation]
    cached = sum(1 for a in asset_results if a.cached)
    gen = sum(1 for a in asset_results if a.marker == "B" and not a.cached)
    lines = [
        f"# narration-to-visuals — отчёт: {lecture}",
        "",
        f"- Блоков: {len(storyboard.blocks)} "
        f"(B: {counts.get('B', 0)}, C: {counts.get('C', 0)}, "
        f"D: {counts.get('D', 0)})",
        f"- B-картинки: сгенерировано {gen}, из кэша {cached}",
        f"- Стоимость fal.ai: ${cost_usd:.3f}",
        f"- Видео: {video_path}",
        "",
        f"## Отклонения (DEVIATION): {len(devs)}",
    ]
    if devs:
        for b in devs:
            lines.append(f"- Блок {b.index + 1} «{b.title}»")
    else:
        lines.append("- нет")
    return "\n".join(lines) + "\n"
