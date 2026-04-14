#!/usr/bin/env python3
"""screenshot-breakpoints.py — снять скриншоты URL на 3 breakpoints через Playwright.

Usage:
  screenshot-breakpoints.py <url> --out /tmp/review/ [--widths 1440,768,375] [--name page]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", required=True, help="Output dir")
    ap.add_argument("--widths", default="1440,768,375")
    ap.add_argument("--name", default="page")
    ap.add_argument("--full-page", action="store_true", default=True)
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        print("ERROR: playwright not installed. Run: pip3 install playwright && playwright install chromium", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    widths = [int(w.strip()) for w in args.widths.split(",") if w.strip()]

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for w in widths:
            ctx = browser.new_context(viewport={"width": w, "height": 900})
            page = ctx.new_page()
            try:
                page.goto(args.url, wait_until="networkidle", timeout=30_000)
            except Exception as e:
                print(f"WARN: {w}px load error: {e}", file=sys.stderr)
            path = out_dir / f"{args.name}-{w}.png"
            page.screenshot(path=str(path), full_page=args.full_page)
            size = path.stat().st_size
            print(f"✅ {w}px → {path} ({size // 1024} KB)")
            results.append((w, path, size))
            ctx.close()
        browser.close()

    tiny = [r for r in results if r[2] < 5_000]
    if tiny:
        print(f"⚠️  CRITICAL: {len(tiny)} screenshots < 5KB (likely blank)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
