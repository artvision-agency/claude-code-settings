#!/usr/bin/env bash
# UserPromptSubmit hook: reminds Claude to use Screaming Frog CLI (`sf`)
# for structural SEO tasks instead of WebFetch/agents.
# Triggers on keywords: seo аудит, краул, crawl, битые ссылки, broken links,
# дубли meta, canonical, orphan pages, sitemap audit, screaming frog.

set -euo pipefail

# Claude Code passes the prompt as JSON on stdin
PROMPT="$(cat 2>/dev/null || true)"

# Case-insensitive match against SEO structural keywords
if echo "$PROMPT" | grep -iqE "seo[- ]?аудит|краул|crawl|битые ссылки|broken links|дубли (meta|title)|canonical цеп|orphan page|sitemap audit|screaming ?frog|проверить ссылки на сайте|meta[- ]audit"; then
  cat <<'EOF'
[SF-REMINDER] Задача похожа на структурный SEO-краул.
Используй `sf` (Screaming Frog CLI), а не WebFetch/агентов:

  sf --crawl https://example.com --headless --save-crawl \
     --export-tabs "Internal:All,Response Codes:Client Error (4xx),Page Titles:Duplicate" \
     --output-folder /tmp/sf-out --overwrite

SF точнее и быстрее для: битые ссылки, дубли meta, canonical, orphan pages,
response codes, sitemap diff. Claude подключается после на смысловом слое (читает CSV).

Обёртка: ~/artvision-data/scripts/seo-toolkit.py (wraps SF + Lighthouse).
EOF
fi

exit 0
