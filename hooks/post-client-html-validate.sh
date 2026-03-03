#!/bin/bash
# PostToolUse (Edit/Write): глубокая валидация HTML клиентов
# Проверяет: бренд-цвета из config.yaml, полноту контента, адаптивность
# Работает ТОЛЬКО для файлов в clients/*/

FILE_PATH="${CLAUDE_FILE_PATH:-$1}"

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

# Только HTML файлы
EXT="${FILE_PATH##*.}"
if [ "$EXT" != "html" ]; then
  exit 0
fi

# Только файлы в clients/
if ! echo "$FILE_PATH" | grep -q "clients/"; then
  exit 0
fi

# Определяем клиента из пути
CLIENT_DIR=$(echo "$FILE_PATH" | sed 's|.*clients/\([^/]*\)/.*|clients/\1|')
ARTVISION_DIR="/Users/antonk/artvision-data"
CONFIG="$ARTVISION_DIR/$CLIENT_DIR/config.yaml"
BASENAME=$(basename "$FILE_PATH")
WARNINGS=""

# === 1. Бренд-цвета из config.yaml ===
if [ -f "$CONFIG" ]; then
  # Извлекаем цвета из config.yaml (поддерживаем оба формата: brand.primary_color и styles.color_accent)
  BRAND_COLORS=$(python3 -c "
import yaml, sys
try:
    with open('$CONFIG') as f:
        c = yaml.safe_load(f)
    colors = []
    # Новый формат (шаблон)
    brand = c.get('brand', {})
    if brand:
        for k,v in brand.items():
            if 'color' in k and v and v.startswith('#'):
                colors.append(v.lower())
    # Старый формат (ant-partners style)
    styles = c.get('styles', {})
    if styles:
        for k,v in styles.items():
            if 'color' in k and v and str(v).startswith('#'):
                colors.append(str(v).lower())
    print(' '.join(set(colors)))
except:
    pass
" 2>/dev/null)

  if [ -n "$BRAND_COLORS" ]; then
    # Проверяем что хотя бы один бренд-цвет присутствует в HTML
    FOUND=0
    for COLOR in $BRAND_COLORS; do
      if grep -qi "$COLOR" "$FILE_PATH" 2>/dev/null; then
        FOUND=1
        break
      fi
    done
    if [ "$FOUND" -eq 0 ]; then
      WARNINGS="${WARNINGS}[brand] $BASENAME: НЕ НАЙДЕНЫ бренд-цвета клиента! Ожидаются: $BRAND_COLORS\n  config: $CONFIG\n  Используй цвета клиента, а не generic.\n\n"
    fi
  fi

  # Извлекаем имя клиента
  CLIENT_NAME=$(python3 -c "
import yaml
try:
    with open('$CONFIG') as f:
        c = yaml.safe_load(f)
    print(c.get('name', c.get('client', '')))
except:
    pass
" 2>/dev/null)
else
  WARNINGS="${WARNINGS}[config] $BASENAME: config.yaml не найден для этого клиента ($CLIENT_DIR). Создай из _template/config.yaml.\n\n"
fi

# === 2. Полнота контента (H2 секции) ===
H2_COUNT=$(grep -ciE '<h2[ >]' "$FILE_PATH" 2>/dev/null)
if [ -z "$H2_COUNT" ] || [ "$H2_COUNT" = "" ]; then H2_COUNT=0; fi
H2_COUNT=$(echo "$H2_COUNT" | tr -d '[:space:]')
if [ "$H2_COUNT" -lt 3 ]; then
  WARNINGS="${WARNINGS}[content] $BASENAME: только $H2_COUNT секций H2. Минимум 3 для полноценной страницы (услуга, преимущества, цены/FAQ).\n\n"
fi

# === 3. CTA кнопка ===
CTA_COUNT=$(grep -ciE '(btn|button|cta|submit|заказ|связат|оставить|получить|рассчитать)' "$FILE_PATH" 2>/dev/null)
if [ -z "$CTA_COUNT" ]; then CTA_COUNT=0; fi
CTA_COUNT=$(echo "$CTA_COUNT" | tr -d '[:space:]')
if [ "$CTA_COUNT" -lt 1 ]; then
  WARNINGS="${WARNINGS}[cta] $BASENAME: не найдена CTA-кнопка. Каждая страница клиента должна иметь призыв к действию.\n\n"
fi

# === 4. Контактная информация ===
if [ -f "$CONFIG" ]; then
  PHONE=$(python3 -c "
import yaml
try:
    with open('$CONFIG') as f:
        c = yaml.safe_load(f)
    contacts = c.get('contacts', {})
    print(contacts.get('phone', contacts.get('phone_raw', '')))
except:
    pass
" 2>/dev/null)
  if [ -n "$PHONE" ] && ! grep -q "$PHONE" "$FILE_PATH" 2>/dev/null; then
    # Проверяем хотя бы частично (последние 7 цифр)
    PHONE_SHORT=$(echo "$PHONE" | tr -d ' ()-+' | tail -c 8)
    if ! grep -q "$PHONE_SHORT" "$FILE_PATH" 2>/dev/null; then
      WARNINGS="${WARNINGS}[contacts] $BASENAME: телефон клиента ($PHONE) не найден на странице.\n\n"
    fi
  fi
fi

# === 5. Размер файла ===
FILE_SIZE=$(wc -c < "$FILE_PATH" | tr -d ' ')
if [ "$FILE_SIZE" -gt 512000 ]; then
  SIZE_KB=$((FILE_SIZE / 1024))
  WARNINGS="${WARNINGS}[size] $BASENAME: ${SIZE_KB}KB — превышает лимит 500KB. Оптимизируй base64 картинки.\n\n"
fi

# === 6. Emoji в HTML (MODX CMS ломает кодировку) ===
EMOJI_RESULT=$(python3 -c "
import re, sys

EMOJI_RANGES = re.compile(
    '['
    '\U0001F600-\U0001F64F'  # Emoticons
    '\U0001F300-\U0001F5FF'  # Misc Symbols and Pictographs
    '\U0001F680-\U0001F6FF'  # Transport and Map
    '\U0001F700-\U0001F77F'  # Alchemical Symbols
    '\U0001F780-\U0001F7FF'  # Geometric Shapes Extended
    '\U0001F800-\U0001F8FF'  # Supplemental Arrows-C
    '\U0001F900-\U0001F9FF'  # Supplemental Symbols and Pictographs
    '\U0001FA00-\U0001FA6F'  # Chess Symbols
    '\U0001FA70-\U0001FAFF'  # Symbols and Pictographs Extended-A
    '\U00002600-\U000026FF'  # Misc Symbols (☀☆♠ и др.)
    '\U00002700-\U000027BF'  # Dingbats (✂✈✔ и др.)
    '\U0000FE00-\U0000FE0F'  # Variation Selectors
    '\U0001F1E0-\U0001F1FF'  # Flags
    '\U00002300-\U000023FF'  # Misc Technical (⌚⌛⏰ и др.)
    '\U000024C2-\U0001F251'  # Enclosed characters
    ']',
    re.UNICODE
)

hits = []
try:
    with open('$FILE_PATH', encoding='utf-8', errors='replace') as f:
        for lineno, line in enumerate(f, 1):
            for m in EMOJI_RANGES.finditer(line):
                char = m.group(0)
                col = m.start() + 1
                codepoint = 'U+{:04X}'.format(ord(char))
                hits.append('  строка {:d}, col {:d}: {} ({})'.format(lineno, col, char, codepoint))
                if len(hits) >= 10:
                    break
            if len(hits) >= 10:
                break
except Exception as e:
    pass

if hits:
    print('\n'.join(hits))
" 2>/dev/null)

if [ -n "$EMOJI_RESULT" ]; then
  WARNINGS="${WARNINGS}[emoji] $BASENAME: найдены emoji — MODX CMS может сломать кодировку страницы!\n$EMOJI_RESULT\n  Замени на HTML entities (&#128512; и т.п.) или текстовые альтернативы.\n\n"
fi

# === 7. Напоминание о Playwright проверке ===
if [ -n "$WARNINGS" ] || [ "$H2_COUNT" -ge 3 ]; then
  # Если страница достаточно крупная — напомнить о проверке адаптивности (Playwright)
  HAS_MEDIA=$(grep -c "@media" "$FILE_PATH" 2>/dev/null)
  if [ -z "$HAS_MEDIA" ]; then HAS_MEDIA=0; fi
  HAS_MEDIA=$(echo "$HAS_MEDIA" | tr -d '[:space:]')
  if [ "$HAS_MEDIA" -lt 2 ]; then
    WARNINGS="${WARNINGS}[responsive] $BASENAME: менее 2 @media queries. Проверь адаптивность на 375px/768px/1440px через Playwright.\n\n"
  fi
fi

# === Вывод ===
if [ -n "$WARNINGS" ]; then
  echo "=== ВАЛИДАЦИЯ КЛИЕНТСКОГО HTML ==="
  echo -e "$WARNINGS"
  echo "==================================="
fi

exit 0
