#!/usr/bin/env bash
# pre-seo-task.sh — PreToolUse-хук: предупреждает о работе с SEO без свежих SF/Lighthouse артефактов.
#
# Триггер: Bash-команда вида `scp .../kp/<client>...`, `factcheck-v2.py`, или Edit/Write
# файлов в `clients/*/seo/*` либо `clients/*/*.html` без свежих артефактов SF/Lighthouse
# в `clients/<name>/seo/sf-out/` (mtime < 7 дней).
#
# Поведение: WARN, не блокирует (экзит 0). Печатает предупреждение в stderr —
# Claude увидит его в результате tool call и должен либо прогнать `sf` + `seo-toolkit.py`,
# либо явно подтвердить пропуск (через env SEO_FRESH_SKIP=1).
#
# Bypass: SEO_FRESH_SKIP=1
#
# Логика клиента:
# 1. Из tool_input достаём путь.
# 2. Если в нём `clients/<name>/` — определяем клиента.
# 3. Проверяем `clients/<name>/seo/sf-out/` mtime > now-7d (или другие SF-артефакты).
# 4. Проверяем `clients/<name>/seo/lighthouse-*.json` mtime > now-7d.
# 5. Если нет — печатаем WARN с командой что запустить.
#
# Не блокирует. Если хочешь блокирующее — переключи EXIT_CODE на 2.
set -euo pipefail

if [[ "${SEO_FRESH_SKIP:-0}" == "1" ]]; then
  exit 0
fi

# Читаем JSON tool_input из stdin
INPUT=$(cat)
TOOL=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")

# Извлекаем путь — для разных tool_name по-разному
PATH_ARG=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
tname = d.get('tool_name','')
ti = d.get('tool_input', {})
if tname in ('Edit','Write','Read'):
    print(ti.get('file_path',''))
elif tname == 'Bash':
    print(ti.get('command',''))
else:
    print('')
" 2>/dev/null || echo "")

# Извлекаем клиента из пути
CLIENT=$(echo "$PATH_ARG" | grep -oE 'clients/[a-z0-9_-]+' | head -1 | sed 's|clients/||')

# Если не клиентский путь — пропускаем
if [[ -z "$CLIENT" ]]; then
  exit 0
fi

# Проверяем что это SEO-релевантный контекст: HTML или путь содержит /seo/ или /kp/
SEO_CTX=0
if echo "$PATH_ARG" | grep -qE '\.html$|/seo/|/kp/|factcheck-v2\.py'; then SEO_CTX=1; fi
if [[ $SEO_CTX -eq 0 ]]; then exit 0; fi

CLIENT_DIR="$HOME/artvision-data/clients/$CLIENT"
SF_DIR="$CLIENT_DIR/seo/sf-out"
SF_DIFF_DIR="$CLIENT_DIR/seo/diff/sf-out"
EU_DIR="$CLIENT_DIR/eu/sf-out"
LH_DIR="$CLIENT_DIR/seo"

# Свежий SF (любая из локаций, mtime < 7 дней)
FRESH_SF=0
for d in "$SF_DIR" "$SF_DIFF_DIR" "$EU_DIR"; do
  if [[ -d "$d" ]] && find "$d" -name "*.csv" -mtime -7 2>/dev/null | grep -q .; then
    FRESH_SF=1; break
  fi
done

# Свежий Lighthouse (json в seo/ за неделю)
FRESH_LH=0
if find "$LH_DIR" -maxdepth 3 -name "lighthouse-*.json" -mtime -7 2>/dev/null | grep -q .; then
  FRESH_LH=1
fi

if [[ $FRESH_SF -eq 1 && $FRESH_LH -eq 1 ]]; then
  exit 0
fi

# Печатаем WARN
{
  echo ""
  echo "⚠️  pre-seo-task: для клиента '$CLIENT' нет свежих SEO-артефактов (<7 дней)"
  [[ $FRESH_SF -eq 0 ]] && echo "   • Screaming Frog (sf-out/*.csv) — НЕ найден или устарел"
  [[ $FRESH_LH -eq 0 ]] && echo "   • Lighthouse (lighthouse-*.json) — НЕ найден или устарел"
  echo ""
  echo "Запусти ОДНУ из команд перед SEO-работой (или подтверди пропуск SEO_FRESH_SKIP=1):"
  echo ""
  CLIENT_URL=$(grep -oE 'https?://[^"[:space:]]+' "$CLIENT_DIR/config.yaml" 2>/dev/null | head -1)
  if [[ -z "$CLIENT_URL" ]]; then
    CLIENT_URL=$(grep -E '^(domain|site|url):' "$CLIENT_DIR/config.yaml" 2>/dev/null | head -1 | sed -E 's/^[a-z]+:[[:space:]]*//; s/^"//; s/"$//; s/[[:space:]]+$//')
    [[ -n "$CLIENT_URL" && "$CLIENT_URL" != http* ]] && CLIENT_URL="https://$CLIENT_URL"
  fi
  CLIENT_URL=${CLIENT_URL:-https://EXAMPLE.RU}
  echo "  # Полный аудит (SF + Lighthouse + PageSpeed + SSL + W3C):"
  echo "  python3 ~/artvision-data/scripts/seo-toolkit.py --url $CLIENT_URL --tools screaming-frog,lighthouse --output-folder $CLIENT_DIR/seo/$(date +%Y-%m-%d)/"
  echo ""
  echo "  # Только SF:"
  echo "  sf $CLIENT_URL --output-folder $CLIENT_DIR/seo/sf-out"
  echo ""
  echo "Bypass: SEO_FRESH_SKIP=1 <команда>  (если знаешь зачем)"
  echo ""
} >&2
exit 0
