#!/usr/bin/env bash
# rotate-portal-bot.sh — детерминированный редеплой нового токена portal_bot после @BotFather /revoke.
#
# КОНТЕКСТ: токен 8399522625:* был в публичной git-истории claude-code-settings (утечка #31).
# Старый токен захардкожен в ~100 файлах. Этот скрипт меняет его на новый ВЕЗДЕ + верифицирует.
#
# ЧЕЛОВЕК делает ОДИН шаг вручную: @BotFather → /revoke → выбрать бота 8399522625 → скопировать новый токен.
# Потом: bash ~/.claude/scripts/rotate-portal-bot.sh '<НОВЫЙ_ТОКЕН>'
#
# Что делает: бэкап → sed замена old→new в tokens.json + всех файлах → verify grep old=0 → test нового токена.
set -uo pipefail

OLD='8399522625:AAGeVvP1WeyijXTcRByiynPOXncBFUwLKQ4'
OLD_ID='8399522625'
NEW="${1:-}"
TS=$(date +%Y%m%d-%H%M%S)
BK=~/secrets-rotate-backup-$TS

if [[ -z "$NEW" ]]; then
  echo "ОШИБКА: передай новый токен от @BotFather:"
  echo "  bash $0 '1234567890:AAxxxxx...'"
  exit 1
fi
if [[ ! "$NEW" =~ ^[0-9]{8,12}:[A-Za-z0-9_-]{30,}$ ]]; then
  echo "ОШИБКА: '$NEW' не похож на bot-токен (формат <id>:<35+ симв>)."; exit 1
fi

echo "=== 0. Проверка нового токена в Telegram ДО замены ==="
GETME=$(curl -s "https://api.telegram.org/bot${NEW}/getMe" 2>/dev/null)
echo "$GETME" | grep -q '"ok":true' || { echo "❌ новый токен не отвечает getMe — revoke не завершён? ответ: $GETME"; exit 1; }
echo "✅ новый токен валиден: $(echo "$GETME" | grep -oE '"username":"[^"]+"')"

echo "=== 1. Список файлов с СТАРЫМ токеном (поверхность) ==="
mapfile -t FILES < <(grep -rl "$OLD" ~/.claude ~/artvision-data 2>/dev/null | grep -vE '/\.git/')
echo "файлов к правке: ${#FILES[@]}"
[[ ${#FILES[@]} -eq 0 ]] && { echo "старого токена нигде нет — нечего менять"; exit 0; }

echo "=== 2. Бэкап ==="
mkdir -p "$BK"
for f in "${FILES[@]}"; do
  d="$BK/$(dirname "${f#/Users/antonk/}")"; mkdir -p "$d"; cp "$f" "$d/" 2>/dev/null || true
done
echo "бэкап → $BK (${#FILES[@]} файлов)"

echo "=== 3. Замена old → new во всех файлах (sed -i '') ==="
ESC_OLD=$(printf '%s' "$OLD" | sed 's/[\/&]/\\&/g')
ESC_NEW=$(printf '%s' "$NEW" | sed 's/[\/&]/\\&/g')
cnt=0
for f in "${FILES[@]}"; do
  sed -i '' "s/${ESC_OLD}/${ESC_NEW}/g" "$f" 2>/dev/null && cnt=$((cnt+1))
done
echo "обработано: $cnt"

echo "=== 4. ВЕРИФИКАЦИЯ — старого токена не осталось ==="
LEFT=$(grep -rl "$OLD" ~/.claude ~/artvision-data 2>/dev/null | grep -vE '/\.git/' | wc -l | tr -d ' ')
echo "файлов со старым токеном осталось: $LEFT (ждём 0)"
NEWCNT=$(grep -rl "$NEW" ~/.claude ~/artvision-data 2>/dev/null | grep -vE '/\.git/' | wc -l | tr -d ' ')
echo "файлов с новым токеном: $NEWCNT"

echo "=== 5. Тест: новый токен шлёт сообщение Антону (161261562) ==="
R=$(curl -s -X POST "https://api.telegram.org/bot${NEW}/sendMessage" \
  -d chat_id=161261562 --data-urlencode text="✅ portal_bot ротирован ${TS}. Старый токен (утёкший #31) отозван, новый задеплоен в ${cnt} файлов." 2>/dev/null)
echo "$R" | grep -q '"ok":true' && echo "✅ тест-сообщение доставлено" || echo "⚠️ тест не прошёл: $R"

echo
echo "=== ИТОГ ==="
echo "  • новый токен задеплоен в $cnt файлов, старого осталось: $LEFT"
echo "  • бэкап: $BK (откат: cp -r \$BK/* в нужные пути)"
echo "  • ⚠️ git: проверь что новый токен НЕ уходит в публичный claude-code-settings"
echo "    (pre-commit-secret-guard должен заблокировать; токен → только в gitignored/tokens.json)"
echo "  • git история claude-code-settings всё ещё содержит СТАРЫЙ токен — но он уже отозван (мёртв), не опасен"
[[ "$LEFT" == "0" ]] && echo "  ✅ РОТАЦИЯ УСПЕШНА" || echo "  ⚠️ остались файлы со старым — разобрать вручную"
