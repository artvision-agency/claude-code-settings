#!/bin/bash
# Обновляет кэш лимитов плана из /api/oauth/usage — тот же источник, что показывает /usage.
# Пишет ~/.claude/.usage-cache.json (raw-ответ). Вызывается статуслайном в фоне, не чаще ~раза в минуту.
# Портируемо (без flock): двойной запуск безвреден — побеждает последняя атомарная запись.
set -u
CACHE="$HOME/.claude/.usage-cache.json"
CREDS="$HOME/.claude/.credentials.json"

TOKEN=$(python3 -c "import json;print(json.load(open('$CREDS'))['claudeAiOauth']['accessToken'])" 2>/dev/null) || exit 0
[ -n "$TOKEN" ] || exit 0

TMP="$(mktemp "${TMPDIR:-/tmp}/cc-usage.XXXXXX")" || exit 0
if curl -s --max-time 6 https://api.anthropic.com/api/oauth/usage \
     -H "Authorization: Bearer $TOKEN" \
     -H "anthropic-beta: oauth-2025-04-20" \
     -H "anthropic-version: 2023-06-01" \
     -H "Content-Type: application/json" -o "$TMP" \
   && python3 -c "import json,sys;sys.exit(0 if 'five_hour' in json.load(open('$TMP')) else 1)" 2>/dev/null; then
    mv -f "$TMP" "$CACHE"
else
    rm -f "$TMP"
fi
