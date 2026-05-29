#!/usr/bin/env bash
# cred-get.sh — multi-source поиск доступа/токена/пароля
# Защита от false-negative: ищет ВЕЗДЕ перед выводом «не найдено».
#
# Usage:
#   cred-get.sh <запрос>          # grep по всем источникам
#   cred-get.sh --json <key>      # значение из tokens.json по top-level ключу
#   cred-get.sh --keychain <svc>  # пароль из macOS Keychain
#
# Источники: tokens.json + access.md + memory + jsonl + Keychain + git log -S
# Связано: ~/.claude/credentials-index.md, rules/no-false-negative.md

set -uo pipefail

TOKENS="$HOME/artvision-data/tokens.json"
CLIENTS="$HOME/artvision-data/clients"
MEMORY="$HOME/.claude/projects/-Users-antonk/memory"
JSONL="$HOME/.claude/projects/-Users-antonk"

usage() { grep -E '^#( |$)' "$0" | sed 's/^# \{0,1\}//'; exit 0; }
[[ $# -eq 0 || "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

# --- режим: значение из tokens.json ---
if [[ "$1" == "--json" ]]; then
  [[ -z "${2:-}" ]] && { echo "нужен ключ"; exit 1; }
  python3 -c "import json,sys; d=json.load(open('$TOKENS')); print(json.dumps(d.get('$2','<ключ не найден>'), ensure_ascii=False, indent=2))"
  exit 0
fi

# --- режим: Keychain ---
if [[ "$1" == "--keychain" ]]; then
  [[ -z "${2:-}" ]] && { echo "нужен service name"; exit 1; }
  security find-generic-password -s "$2" -w 2>/dev/null || echo "<не найдено в Keychain: $2>"
  exit 0
fi

# --- режим по умолчанию: multi-source grep ---
Q="$1"
echo "🔍 Поиск «${Q}» по всем источникам:"
echo

echo "── 1. tokens.json (top-level ключи) ──"
python3 -c "import json; d=json.load(open('$TOKENS')); ks=[k for k in d if '$Q'.lower() in k.lower()]; print('  '+(', '.join(ks) if ks else '(нет совпадений в ключах)'))" 2>/dev/null
echo "  (значения:) "
grep -io "\"[^\"]*${Q}[^\"]*\"[[:space:]]*:" "$TOKENS" 2>/dev/null | head -10 | sed 's/^/    /' || true
echo

echo "── 2. access.md клиентов ──"
grep -ril "$Q" "$CLIENTS"/*/access.md 2>/dev/null | sed 's/^/  /' || echo "  (нет)"
echo

echo "── 3. memory ──"
grep -ril "$Q" "$MEMORY" 2>/dev/null | head -10 | sed 's/^/  /' || echo "  (нет)"
echo

echo "── 4. jsonl сессий (последние 30 дней, до 10 файлов) ──"
find "$JSONL" -name "*.jsonl" -mtime -30 2>/dev/null | while read -r f; do
  grep -il "$Q" "$f" 2>/dev/null
done | head -10 | sed 's/^/  /' || echo "  (нет)"
echo

echo "── 5. macOS Keychain (по имени службы) ──"
security find-generic-password -s "$Q" 2>/dev/null | grep -E 'svce|acct' | sed 's/^/  /' || echo "  (точного service '$Q' нет — попробуй --keychain)"
echo

echo "── 6. git log -S (вычищено ли из tokens.json) ──"
( cd "$HOME/artvision-data" && git log --oneline -S"$Q" -- tokens.json 2>/dev/null | head -5 | sed 's/^/  /' ) || echo "  (нет в истории tokens.json)"
echo

echo "✅ Если всё пусто — честный вывод: «не найдено в 6 источниках», НЕ «нет/не существует»."
