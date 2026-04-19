#!/usr/bin/env python3
"""YouTube Watch History extractor via Safari automation.

Uses the shared safari_driver.SafariTab for all browser automation (JS-safe).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path.home() / ".claude" / "lib"))
from safari_driver import SafariTab, AppleScriptError  # type: ignore[import-not-found]  # noqa: E402

HISTORY_URL = "https://www.youtube.com/feed/history"


def ensure_logged_in(tab: SafariTab) -> None:
    """If page shows 'Sign in' prompt, click it."""
    js = r"""
        var btns = Array.from(document.querySelectorAll('a,button,tp-yt-paper-button'));
        var signin = btns.find(b => {
            var t = (b.textContent||'').trim();
            return t === 'Войти' || t === 'Sign in';
        });
        var bodyText = document.body ? document.body.innerText : '';
        if (signin && (bodyText.indexOf('История поиска и просмотра недоступна') >= 0 ||
                       bodyText.indexOf('Watch and search history are not available') >= 0)) {
            signin.click();
            return 'CLICKED_SIGNIN';
        }
        return 'OK';
    """
    if "CLICKED_SIGNIN" in tab.run_js(js):
        import time
        time.sleep(5)


def extract_items(tab: SafariTab) -> dict:
    """Extract video items + date headers from the history page."""
    js = r"""
        var h = document.querySelectorAll('h3, #video-title');
        var items = [];
        var seen = new Set();
        h.forEach(function(el) {
            var t = (el.textContent||'').trim();
            if (t.length > 5 && t.length < 200 && !seen.has(t)) {
                seen.add(t);
                var link = el.closest('a') || el.querySelector('a');
                if (!link) {
                    var parent = el.closest('[class*=renderer]') || el.parentElement;
                    link = parent ? parent.querySelector('a[href*=watch],a[href*=shorts]') : null;
                }
                var container = el.closest('[class*=renderer]');
                var byline = container ? container.querySelector('[id*=channel-name], [class*=byline]') : null;
                items.push({
                    title: t.substring(0, 150),
                    url: link ? link.href.split('&')[0] : '',
                    channel: byline ? (byline.textContent||'').trim().substring(0, 60) : ''
                });
            }
        });
        var dates = Array.from(document.querySelectorAll('#title-container #title, ytd-item-section-header-renderer'))
            .map(el => (el.textContent||'').trim()).filter(t => t.length > 0 && t.length < 40);
        return JSON.stringify({items: items, dates: dates});
    """
    raw = tab.run_js(js)
    try:
        return json.loads(raw) if raw else {"items": [], "dates": []}
    except json.JSONDecodeError as e:
        return {"items": [], "dates": [], "error": str(e), "raw": raw[:500]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", help="Filter by substring (case-insensitive)")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--format", choices=["json", "table"], default="table")
    ap.add_argument("--scrolls", type=int, default=5)
    ap.add_argument("--no-open", action="store_true", help="Skip ensure() — use existing tab")
    args = ap.parse_args()

    tab = SafariTab(url_match="/feed/history", open_url=HISTORY_URL)

    if not args.no_open:
        print("Ensuring YouTube history tab...", file=sys.stderr)
        try:
            tab.ensure()
            ensure_logged_in(tab)
            tab.scroll(iterations=args.scrolls)
        except AppleScriptError as e:
            print(f"Safari error: {e}", file=sys.stderr)
            sys.exit(1)

    data = extract_items(tab)
    items = data.get("items", [])
    dates = data.get("dates", [])

    if args.search:
        s = args.search.lower()
        items = [
            it for it in items
            if s in it["title"].lower() or s in it.get("channel", "").lower()
        ]

    items = items[: args.limit]

    if args.format == "json":
        print(json.dumps({"dates": dates, "items": items}, ensure_ascii=False, indent=2))
    else:
        print(f"Date markers: {', '.join(dates) if dates else '(none)'}")
        print(f"Items: {len(items)}\n")
        for i, it in enumerate(items, 1):
            ch = f" [{it['channel']}]" if it.get("channel") else ""
            print(f"{i}. {it['title']}{ch}")
            if it.get("url"):
                print(f"   {it['url']}")


if __name__ == "__main__":
    main()
