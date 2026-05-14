#!/usr/bin/env bash
# check-design-profile.sh — аудит design_profile у всех клиентов в clients/
#
# Использование: ~/.claude/scripts/check-design-profile.sh
#
# Проходит все clients/<name>/config.yaml, выводит таблицу:
#   клиент | профиль | reason | статус
# Помечает пустые/отсутствующие как ❌.

set -uo pipefail

CLIENTS_DIR="$HOME/artvision-data/clients"
[ ! -d "$CLIENTS_DIR" ] && { echo "Не найден $CLIENTS_DIR"; exit 1; }

printf "%-30s | %-22s | %-50s | %s\n" "Клиент" "Профиль" "Причина" "Статус"
printf -- "%.s-" {1..120}
printf "\n"

TOTAL=0
WITH_PROFILE=0
WITHOUT_CONFIG=0
WITHOUT_PROFILE=0

for dir in "$CLIENTS_DIR"/*/; do
  CLIENT=$(basename "$dir")
  case "$CLIENT" in _drafts|_template|_leads|_reports) continue ;; esac
  TOTAL=$((TOTAL+1))

  CONFIG="$dir/config.yaml"

  if [ ! -f "$CONFIG" ]; then
    printf "%-30s | %-22s | %-50s | %s\n" "$CLIENT" "—" "(нет config.yaml)" "❌"
    WITHOUT_CONFIG=$((WITHOUT_CONFIG+1))
    continue
  fi

  PROFILE=$(grep -A1 '^design_profile:' "$CONFIG" 2>/dev/null | grep -E '^[[:space:]]+type:' | sed -E 's/^[[:space:]]+type:[[:space:]]*"?([a-z0-9-]+)"?.*/\1/' | head -1)
  REASON=$(grep -A2 '^design_profile:' "$CONFIG" 2>/dev/null | grep -E '^[[:space:]]+reason:' | sed -E 's/^[[:space:]]+reason:[[:space:]]*"?(.*)/\1/' | sed -E 's/"[[:space:]]*$//' | head -1 | cut -c1-48)

  if [ -z "$PROFILE" ]; then
    printf "%-30s | %-22s | %-50s | %s\n" "$CLIENT" "—" "(design_profile не задан)" "❌"
    WITHOUT_PROFILE=$((WITHOUT_PROFILE+1))
  else
    printf "%-30s | %-22s | %-50s | %s\n" "$CLIENT" "$PROFILE" "${REASON:-—}" "✅"
    WITH_PROFILE=$((WITH_PROFILE+1))
  fi
done

printf -- "%.s-" {1..120}
printf "\n"
echo
echo "ИТОГО: $TOTAL клиентов"
echo "  ✅ С профилем:        $WITH_PROFILE"
echo "  ❌ Без config.yaml:   $WITHOUT_CONFIG"
echo "  ❌ Без design_profile: $WITHOUT_PROFILE"
echo
echo "Профили смотри в ~/.claude/rules/design-profile-routing.md"
echo "5 типов: enterprise | b2c-polished | lux-marketing | dashboard-relationship | mvp-prototype"
