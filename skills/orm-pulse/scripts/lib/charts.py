"""SVG charts для command-center.

Вынесено из command-center.py при refactoring 2026-05-10.
"""
from __future__ import annotations
import csv
from datetime import datetime, timedelta

from .config import ROOT


def daily_deltas_for_chart(client: str, days: int = 14):
    """Возвращает [(MM-DD, added, removed)] за последние N дней по reviews-tracker history."""
    history = ROOT / "clients" / client / "orm" / "reviews-tracker" / "history.csv"
    if not history.exists():
        return []
    by_day: dict[str, int] = {}
    try:
        for row in csv.DictReader(open(history)):
            ts = row.get("timestamp", "")
            if len(ts) < 10:
                continue
            day = ts[:10]
            try:
                t = int(row.get("total") or 0)
            except (TypeError, ValueError):
                continue
            by_day[day] = t
    except Exception:
        return []
    if len(by_day) < 2:
        return []
    sorted_days = sorted(by_day.keys())
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    sorted_days = [d for d in sorted_days if d >= cutoff]
    if len(sorted_days) < 2:
        return []
    out = []
    prev = by_day[sorted_days[0]]
    for day in sorted_days[1:]:
        cur = by_day[day]
        d = cur - prev
        out.append((day[5:], max(d, 0), max(-d, 0)))
        prev = cur
    return out


def render_publications_svg(deltas) -> str:
    """SVG bar-chart: зелёные = added, красные = removed."""
    if not deltas:
        return ""
    n = len(deltas)
    W = max(280, n * 22 + 40)
    H = 110
    pad_l, pad_r, pad_t, pad_b = 24, 8, 14, 28
    chart_w = W - pad_l - pad_r
    chart_h = H - pad_t - pad_b
    max_v = max(max(a for _, a, _ in deltas), max(r for _, _, r in deltas), 1)
    bar_w = chart_w / n * 0.6
    gap = chart_w / n
    baseline = pad_t + chart_h * 0.65
    bars = []
    labels = []
    sum_added = sum(a for _, a, _ in deltas)
    sum_removed = sum(r for _, _, r in deltas)
    for i, (day, added, removed) in enumerate(deltas):
        cx = pad_l + gap * i + gap / 2
        bx = cx - bar_w / 2
        if added:
            h = (baseline - pad_t) * (added / max_v)
            bars.append(f'<rect x="{bx:.1f}" y="{baseline-h:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="#16a34a" rx="2"/>')
            bars.append(f'<text x="{cx:.1f}" y="{baseline-h-2:.1f}" font-size="9" fill="#16a34a" text-anchor="middle" font-weight="600">+{added}</text>')
        if removed:
            h = (H - pad_b - baseline) * (removed / max_v)
            bars.append(f'<rect x="{bx:.1f}" y="{baseline:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="#dc2626" rx="2"/>')
            bars.append(f'<text x="{cx:.1f}" y="{baseline+h+10:.1f}" font-size="9" fill="#dc2626" text-anchor="middle" font-weight="600">-{removed}</text>')
        if i % 2 == 0 or i == n - 1:
            labels.append(f'<text x="{cx:.1f}" y="{H-6:.1f}" font-size="9" fill="#64748b" text-anchor="middle">{day}</text>')
    legend = (
        f'<text x="{pad_l}" y="10" font-size="9" fill="#16a34a" font-weight="600">+{sum_added} опубл</text>'
        f'<text x="{pad_l+62}" y="10" font-size="9" fill="#dc2626" font-weight="600">-{sum_removed} снёс Я</text>'
    )
    return (
        f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" style="display:block;margin-top:8px">'
        f'<line x1="{pad_l}" y1="{baseline:.1f}" x2="{W-pad_r}" y2="{baseline:.1f}" stroke="#cbd5e1" stroke-width="0.5"/>'
        + legend + "".join(bars) + "".join(labels) +
        '</svg>'
    )
