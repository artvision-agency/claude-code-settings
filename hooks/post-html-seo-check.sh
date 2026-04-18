#!/bin/bash
set -euo pipefail

# PostToolUse(Write/Edit) — SEO и автономность проверка HTML
# Проверяет: schema, OG, h-tags, CDN, размер

FILE_PATH="${TOOL_INPUT_FILE_PATH:-${TOOL_INPUT_PATH:-}}"
[ -z "$FILE_PATH" ] && exit 0

# Только для HTML файлов в clients/ и projects/
echo "$FILE_PATH" | grep -qE '\.(html|htm)$' || exit 0
echo "$FILE_PATH" | grep -qE '(clients/|projects/)' || exit 0
[ -f "$FILE_PATH" ] || exit 0

WARNINGS=""

# 1. Автономность — внешние зависимости
CDN_HITS=$(grep -cE '(fonts\.googleapis|cdn\.|ajax\.|cdnjs\.|unpkg\.com|jsdelivr)' "$FILE_PATH" 2>/dev/null || true)
if [ -n "$CDN_HITS" ] && [ "$CDN_HITS" -gt 0 ]; then
  WARNINGS="${WARNINGS}🔴 АВТОНОМНОСТЬ: найдено $CDN_HITS внешних CDN-зависимостей — инлайнить!\n"
fi

# 2. Schema markup (JSON-LD)
SCHEMA=$(grep -c 'application/ld+json' "$FILE_PATH" 2>/dev/null || true)
if [ -z "$SCHEMA" ] || [ "$SCHEMA" -eq 0 ]; then
  WARNINGS="${WARNINGS}🟡 SEO: нет Schema markup (JSON-LD)\n"
fi

# 3. OG tags
OG_TITLE=$(grep -c 'og:title' "$FILE_PATH" 2>/dev/null || true)
OG_IMAGE=$(grep -c 'og:image' "$FILE_PATH" 2>/dev/null || true)
if [ -z "$OG_TITLE" ] || [ "$OG_TITLE" -eq 0 ]; then
  WARNINGS="${WARNINGS}🟡 SEO: нет og:title\n"
fi
if [ -z "$OG_IMAGE" ] || [ "$OG_IMAGE" -eq 0 ]; then
  WARNINGS="${WARNINGS}🟡 SEO: нет og:image\n"
fi

# 4. H1 — должен быть ровно 1
H1_COUNT=$(grep -coE '<h1[ >]' "$FILE_PATH" 2>/dev/null || true)
if [ -z "$H1_COUNT" ] || [ "$H1_COUNT" -eq 0 ]; then
  WARNINGS="${WARNINGS}🔴 SEO: нет <h1>\n"
elif [ "$H1_COUNT" -gt 1 ]; then
  WARNINGS="${WARNINGS}🟡 SEO: найдено $H1_COUNT тегов <h1> (должен быть 1)\n"
fi

# 5. H2 >= 3
H2_COUNT=$(grep -coE '<h2[ >]' "$FILE_PATH" 2>/dev/null || true)
if [ -n "$H2_COUNT" ] && [ "$H2_COUNT" -lt 3 ]; then
  WARNINGS="${WARNINGS}🟡 SEO: только $H2_COUNT тегов <h2> (рекомендуется >= 3)\n"
fi

# 6. Canonical
CANONICAL=$(grep -c 'rel="canonical"' "$FILE_PATH" 2>/dev/null || true)
if [ -z "$CANONICAL" ] || [ "$CANONICAL" -eq 0 ]; then
  WARNINGS="${WARNINGS}🟡 SEO: нет canonical URL\n"
fi

# 7. Размер файла
FILE_SIZE=$(wc -c < "$FILE_PATH" 2>/dev/null | tr -d ' ')
if [ "$FILE_SIZE" -gt 512000 ]; then
  SIZE_KB=$((FILE_SIZE / 1024))
  WARNINGS="${WARNINGS}🟡 Размер: ${SIZE_KB}KB (рекомендуется < 500KB)\n"
fi

# 8. Viewport
VIEWPORT=$(grep -c 'viewport' "$FILE_PATH" 2>/dev/null || true)
if [ -z "$VIEWPORT" ] || [ "$VIEWPORT" -eq 0 ]; then
  WARNINGS="${WARNINGS}🔴 Нет viewport meta tag\n"
fi

# 9. Lang attribute
LANG=$(grep -c 'lang="' "$FILE_PATH" 2>/dev/null || true)
if [ -z "$LANG" ] || [ "$LANG" -eq 0 ]; then
  WARNINGS="${WARNINGS}🟡 Нет lang attribute на <html>\n"
fi

if [ -n "$WARNINGS" ]; then
  echo "📋 HTML SEO Check: $(basename "$FILE_PATH")"
  echo -e "$WARNINGS"
fi
