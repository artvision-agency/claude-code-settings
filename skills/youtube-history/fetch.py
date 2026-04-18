#!/usr/bin/env python3
"""YouTube Watch History extractor via Safari AppleScript+JS."""
from __future__ import annotations
import subprocess, json, sys, argparse, time

HISTORY_URL = "https://www.youtube.com/feed/history"

def run_applescript(script: str) -> str:
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return r.stdout.strip()

def ensure_history_tab() -> None:
    """Find or open a youtube history tab (does not change user's front window)."""
    run_applescript(f'''tell application "Safari"
        set targetURL to "{HISTORY_URL}"
        set foundIt to false
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t contains "/feed/history" then
                    set foundIt to true
                    exit repeat
                end if
            end repeat
            if foundIt then exit repeat
        end repeat
        if not foundIt then
            if (count of windows) is 0 then
                make new document with properties {{URL:targetURL}}
            else
                tell front window to set current tab to (make new tab with properties {{URL:targetURL}})
            end if
        end if
    end tell''')
    time.sleep(3)

def run_js_in_history_tab(js: str) -> str:
    """Execute JS inside the YouTube history tab, regardless of front window."""
    js_escaped = js.replace('\\', '\\\\').replace('"', '\\"')
    script = f'''tell application "Safari"
        set resultValue to ""
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t contains "/feed/history" then
                    set resultValue to (do JavaScript "{js_escaped}" in t)
                    exit repeat
                end if
            end repeat
            if resultValue is not "" then exit repeat
        end repeat
        return resultValue
    end tell'''
    return run_applescript(script)

def ensure_logged_in() -> None:
    """If page shows 'Sign in' prompt, click it."""
    result = run_js_in_history_tab("""
        var btns = Array.from(document.querySelectorAll('a,button,tp-yt-paper-button'));
        var signin = btns.find(b => {
            var t = (b.textContent||'').trim();
            return t === 'Войти' || t === 'Sign in';
        });
        var bodyText = document.body ? document.body.innerText : '';
        if (signin && (bodyText.indexOf('История поиска и просмотра недоступна') >= 0 ||
                       bodyText.indexOf('Watch and search history are not available') >= 0)) {
            signin.click();
            'CLICKED_SIGNIN';
        } else {
            'OK';
        }
    """)
    if "CLICKED_SIGNIN" in result:
        time.sleep(5)

def scroll_and_load(scroll_count: int = 5) -> None:
    for _ in range(scroll_count):
        run_js_in_history_tab("window.scrollBy(0, 1500);")
        time.sleep(1.5)

def extract_items() -> dict:
    js = """
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
        JSON.stringify({items: items, dates: dates});
    """
    result = run_js_in_history_tab(js)
    try:
        return json.loads(result) if result else {"items": [], "dates": []}
    except Exception as e:
        return {"items": [], "dates": [], "error": str(e), "raw": result[:500]}

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", help="Filter by substring (case-insensitive)")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--format", choices=["json", "table"], default="table")
    ap.add_argument("--scrolls", type=int, default=5)
    ap.add_argument("--no-open", action="store_true", help="Skip opening — use existing tab")
    args = ap.parse_args()

    if not args.no_open:
        print("Ensuring YouTube history tab...", file=sys.stderr)
        ensure_history_tab()
        ensure_logged_in()
        scroll_and_load(args.scrolls)

    data = extract_items()
    items = data.get("items", [])
    dates = data.get("dates", [])

    if args.search:
        s = args.search.lower()
        items = [it for it in items if s in it["title"].lower() or s in it.get("channel", "").lower()]

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
