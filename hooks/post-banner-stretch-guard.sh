#!/bin/bash
# PostToolUse(Edit|Write): детект РАСТЯЖЕНИЯ изображений в баннерах / ads.
# Триггер: .html|.css где путь содержит /ads/ ИЛИ basename содержит "banner".
# Паттерны растяжения: object-fit:fill, background-size:100% 100% → WARN в stderr.
# Warn-only (НЕ блокирует). Bypass: BANNER_STRETCH_OK=1
#
# Правило: ~/.claude/rules/visual-content-not-just-ratio.md (R1)
# Прецедент: 2026-05-29 Avto.World CTO Expo — фото 3:4 (1280×1707) в холст 4:3
#   (1080×810) через object-fit:fill → люди растянуты ×1.78. Антон 5+ раз «сплющены»,
#   Claude проверял ratio ФАЙЛА (4:3 ✓), не пропорции людей ВНУТРИ.

[ "${BANNER_STRETCH_OK:-0}" = "1" ] && exit 0

INPUT=$(cat)
FILE=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)

[ -z "$FILE" ] && exit 0

# Только html/css
case "$FILE" in
  *.html|*.htm|*.css) ;;
  *) exit 0 ;;
esac

# Только баннеры/ads: путь содержит /ads/ ИЛИ basename содержит banner
echo "$FILE" | grep -qiE '/ads/|banner' || exit 0
[ ! -f "$FILE" ] && exit 0

VIOLATIONS=0
DETAILS=""

# Pattern 1: object-fit: fill — игнорирует пропорции (тянет фото под рамку)
N1=$(grep -ciE 'object-fit:[[:space:]]*fill' "$FILE" 2>/dev/null || echo 0)
N1=$(echo "$N1" | tr -d '[:space:]'); [ -z "$N1" ] && N1=0
if [ "$N1" -gt 0 ]; then
  VIOLATIONS=$((VIOLATIONS+1))
  DETAILS+="• object-fit:fill (${N1}×) — игнорирует пропорции, растягивает фото. Замени на object-fit:cover (кроп с сохранением пропорций).\n"
fi

# Pattern 2: background-size: 100% 100% — растягивает фон под рамку
N2=$(grep -ciE 'background-size:[[:space:]]*100%[[:space:]]+100%' "$FILE" 2>/dev/null || echo 0)
N2=$(echo "$N2" | tr -d '[:space:]'); [ -z "$N2" ] && N2=0
if [ "$N2" -gt 0 ]; then
  VIOLATIONS=$((VIOLATIONS+1))
  DETAILS+="• background-size:100% 100% (${N2}×) — растягивает фон. Замени на background-size:cover.\n"
fi

if [ "$VIOLATIONS" -gt 0 ]; then
  cat <<EOF >&2

⚠️  post-banner-stretch-guard: $FILE
   Возможное РАСТЯЖЕНИЕ изображения в баннере ($VIOLATIONS):
$(echo -e "$DETAILS")
   ПРОВЕРЬ: ratio исходного фото vs холста (sips -g pixelWidth -g pixelHeight файл).
   Если разные → ТОЛЬКО object-fit:cover / background-size:cover. НИКОГДА fill / 100% 100%.
   На людях/лицах/логотипах растяжение особенно заметно (прецедент Avto.World 29.05: люди ×1.78).
   Правило: ~/.claude/rules/visual-content-not-just-ratio.md (R1, R2)
   Bypass: BANNER_STRETCH_OK=1

EOF
fi

exit 0
