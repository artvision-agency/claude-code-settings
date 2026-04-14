#!/usr/bin/env python3
"""ui-autocheck.py — автопроверки скриншотов перед передачей агенту.

Usage: ui-autocheck.py /tmp/review/*.png
Exit: 0 = PASS, 1 = CRITICAL fail, 2 = WARN
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: ui-autocheck.py <png...>", file=sys.stderr)
        return 2

    try:
        from PIL import Image  # type: ignore
    except ImportError:
        print("ERROR: Pillow not installed. Run: pip3 install Pillow", file=sys.stderr)
        return 2

    critical = 0
    warn = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        if not p.exists():
            print(f"❌ {p}: not found")
            critical += 1
            continue
        size = p.stat().st_size
        if size < 5_000:
            print(f"❌ {p}: {size}B < 5KB (не отрендерилось)")
            critical += 1
            continue
        try:
            img = Image.open(p).convert("RGB")
        except Exception as e:
            print(f"❌ {p}: open error {e}")
            critical += 1
            continue

        w, h = img.size
        if h < 500:
            print(f"❌ {p}: height {h}px < 500")
            critical += 1
            continue

        pixels = list(iter(img.getdata()))
        total = len(pixels)
        white_count = sum(1 for px in pixels if px == (255, 255, 255))
        white_ratio = white_count / total if total else 0
        unique = len(set(pixels[::max(1, total // 10_000)]))  # sample for speed

        if white_ratio > 0.99:
            print(f"❌ {p}: {white_ratio:.1%} белого (белый экран)")
            critical += 1
        elif unique < 100:
            print(f"⚠️  {p}: всего {unique} цветов (сэмпл) — подозрительно пусто")
            warn += 1
        else:
            print(f"✅ {p}: {w}×{h}, {white_ratio:.1%} белого, ~{unique} цветов")

    if critical:
        return 1
    if warn:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
