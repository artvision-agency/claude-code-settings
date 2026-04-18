#!/bin/bash
set -euo pipefail

# extract-design-system.sh <url> [output_file]
# Извлекает дизайн-систему с сайта: цвета, шрифты, стиль кнопок
# Результат → design-system.md

URL="${1:-}"
OUTPUT="${2:-design-system.md}"

if [ -z "$URL" ]; then
  echo "Usage: extract-design-system.sh <url> [output_file]"
  echo "Example: extract-design-system.sh https://example.com clients/example/design-system.md"
  exit 1
fi

echo "🎨 Извлекаю дизайн-систему с $URL..."

# Скачиваем HTML + CSS
HTML=$(curl -sL --max-time 15 "$URL" 2>/dev/null || echo "")
if [ -z "$HTML" ]; then
  echo "❌ Не удалось загрузить $URL"
  exit 1
fi

# 1. Цвета (hex)
COLORS=$(echo "$HTML" | grep -oE '#[0-9a-fA-F]{3,8}' | sort -u | head -20)

# 2. RGB/RGBA
RGBA=$(echo "$HTML" | grep -oE 'rgba?\([^)]+\)' | sort -u | head -10)

# 3. Шрифты
FONTS=$(echo "$HTML" | grep -oE "font-family:[^;\"']+" | sed 's/font-family:\s*//' | sort -u | head -10)

# 4. Google Fonts URL
GFONTS=$(echo "$HTML" | grep -oE 'fonts\.googleapis\.com/css2\?[^"'"'"' >]+' | head -5)

# 5. Размеры шрифтов
FSIZES=$(echo "$HTML" | grep -oE 'font-size:\s*[0-9]+px' | sed 's/font-size:\s*//' | sort -u | head -15)

# 6. Border-radius (стиль кнопок)
BRADIUS=$(echo "$HTML" | grep -oE 'border-radius:\s*[^;]+' | sed 's/border-radius:\s*//' | sort -u | head -5)

# 7. Background colors
BGCOLORS=$(echo "$HTML" | grep -oE 'background(-color)?:\s*#[0-9a-fA-F]{3,8}' | grep -oE '#[0-9a-fA-F]+' | sort -u | head -10)

# Генерируем design-system.md
cat > "$OUTPUT" << DSEOF
# Design System — $URL
> Извлечено: $(date '+%Y-%m-%d %H:%M')
> Источник: $URL

## Палитра (hex)
\`\`\`
$COLORS
\`\`\`

## RGB/RGBA
\`\`\`
$RGBA
\`\`\`

## Background Colors
\`\`\`
$BGCOLORS
\`\`\`

## Шрифты
\`\`\`
$FONTS
\`\`\`

## Google Fonts
\`\`\`
$GFONTS
\`\`\`

## Размеры шрифтов
\`\`\`
$FSIZES
\`\`\`

## Border-radius (стиль кнопок)
\`\`\`
$BRADIUS
\`\`\`

## Использование
При создании КП/страницы для этого клиента:
1. Использовать цвета из палитры выше
2. Подключить те же шрифты
3. Соблюдать border-radius кнопок
4. НЕ использовать generic цвета от другого клиента
DSEOF

echo "✅ Дизайн-система сохранена в $OUTPUT"
echo "   Цветов: $(echo "$COLORS" | wc -l | tr -d ' ')"
echo "   Шрифтов: $(echo "$FONTS" | wc -l | tr -d ' ')"
