#!/usr/bin/env bash
# net-failover-phone.sh — приоритет хотспоту телефона при старте/wake.
# Логика: если НЕ на телефоне И (нет инета ИЛИ captive-портал) → переключиться на телефон.
# Если уже на телефоне и инет есть — ничего не делаем.
# SSID телефона: "TG @Antonkamer - SEO, marketing" (Антон раздаёт с телефона).
# Статус: ИНЕРТЕН до подключения в bootstrap (ждёт «го»). Запуск вручную для теста безопасен.

set -euo pipefail
PHONE_SSID="TG @Antonkamer - SEO, marketing"
IFACE="en0"
LOG="$HOME/Library/Logs/artvision-net-failover.log"
exec >> "$LOG" 2>&1
echo "=== net-failover $(date '+%F %T') ==="

current_ssid() {
  networksetup -getairportnetwork "$IFACE" 2>/dev/null | sed -E 's/^Current Wi-Fi Network: //'
}

has_internet() {
  ping -c1 -W1500 8.8.8.8 >/dev/null 2>&1 || return 1
  # captive-портал: настоящий инет вернёт тело "Success"
  local body
  body=$(curl -s -m 4 http://captive.apple.com/hotspot-detect.html 2>/dev/null || true)
  echo "$body" | grep -qi "Success" || return 1
  return 0
}

CUR="$(current_ssid)"
echo "current SSID: $CUR"

if [ "$CUR" = "$PHONE_SSID" ]; then
  if has_internet; then echo "on phone + internet OK → nothing to do"; exit 0
  else echo "on phone but no internet (телефон без сети?) → ждём, не трогаем"; exit 0; fi
fi

# Не на телефоне. Приоритет телефону: если инета нет/captive — пробуем телефон.
if has_internet; then
  echo "не на телефоне, но инет на '$CUR' рабочий. (Приоритет телефону — переключим только если телефон виден.)"
fi

if ! has_internet; then
  echo "НЕТ инета/captive на '$CUR' → пробую телефон '$PHONE_SSID'"
fi

# Виден ли телефон в эфире?
SCAN=$(/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -s 2>/dev/null || true)
if echo "$SCAN" | grep -qF "$PHONE_SSID" || [ -z "$SCAN" ]; then
  echo "переключаюсь на $PHONE_SSID"
  # пароль берётся из Keychain (сеть preferred). Если потребует — добавить 3-м аргументом.
  networksetup -setairportnetwork "$IFACE" "$PHONE_SSID" 2>&1 || echo "setairportnetwork failed (нужен пароль?)"
  sleep 6
  if has_internet; then echo "OK: на телефоне, инет есть"; else echo "WARN: переключился, инета пока нет"; fi
else
  echo "телефон '$PHONE_SSID' не виден в эфире — остаюсь на '$CUR'"
fi
