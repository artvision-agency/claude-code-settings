#!/usr/bin/env python3
"""
extract_top3.py — STUB.

Goal: Fetch top-3 SERP URLs for a keyword and run parse_dom.py on each.

TODO:
1. WebSearch top-3 (Google) OR Topvisor API (Yandex, requires region from tokens.json)
   - For Yandex: read tokens.json -> topvisor.api_key, POST to /v2/json/get/searcher_competitor/operate
   - Exclude domains: wikipedia.org, reddit.com, pinterest, ozon.ru, wildberries.ru,
     youtube.com, gov.ru, government sites, social platforms
2. Fetch HTML for each URL:
   - Try WebFetch first (fast, static)
   - Fallback to Playwright (~/.claude/skills/agent-browser/) for JS-heavy SPAs
   - Detect SPA: <noscript> message OR <div id="app"> empty + heavy <script> tags
3. Run parse_dom.analyze_html(html, source_url) for each
4. Write per-URL JSON to ~/.claude/cache/serp-format/<sha1>-{0,1,2}.json
5. Aggregate -> pass to build_template.py
6. Log fetch results to ~/.claude/logs/serp-format-extractor.log

Args (planned):
    --keyword "имплантация зубов спб"
    --region spb|msk|all (for Yandex)
    --engine google|yandex (default: google)
    --out path.json
    --no-cache (skip cache, force refetch)

Cache TTL: 7 days
Cache key: sha1(keyword + region + engine)
Cache path: ~/.claude/cache/serp-format/<key>.json

Exit codes:
    0  = success
    1  = no valid competitors found (< 2 after filtering)
    2  = fetch errors > 50% (anti-captcha tripped)
    3  = invalid arguments
"""

import sys


def main() -> int:
    sys.stderr.write(
        "STUB: extract_top3.py not yet implemented.\n"
        "Use parse_dom.py directly with --html for now:\n"
        "  python3 parse_dom.py --html article.html --out section-1.json\n"
        "\n"
        "TODO list see docstring at top of file.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
