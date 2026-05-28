#!/usr/bin/env bash
# gcal-bootstrap.sh — one-time OAuth для Google Calendar API
# После прогона refresh_token сохраняется в ~/.claude/.cache/gcal-token.json
# Дальше ~/.claude/scripts/gcal.py работает без UI годами.
#
# Использует уже существующий OAuth client (тот же что для YouTube):
#   /Users/antonk/artvision-data/scripts/client_secret_v2.json
#
# Требует: в GCP project 599931128448 включён Google Calendar API
# (https://console.cloud.google.com/apis/library/calendar-json.googleapis.com
#  → проект voice-87003 → ENABLE — 1 клик. Если ошибка scope при run — сделай это.)

set -euo pipefail

CLIENT_SECRET="/Users/antonk/artvision-data/scripts/client_secret_v2.json"
TOKEN_OUT="$HOME/.claude/.cache/gcal-token.json"

if [[ ! -f "$CLIENT_SECRET" ]]; then
  echo "ERR: client_secret_v2.json not found at $CLIENT_SECRET" >&2
  exit 1
fi

mkdir -p "$(dirname "$TOKEN_OUT")"

if [[ -f "$TOKEN_OUT" ]]; then
  echo "Token already exists at $TOKEN_OUT"
  echo "Чтобы пересоздать: rm $TOKEN_OUT && повтори"
  exit 0
fi

python3 << PYEOF
from google_auth_oauthlib.flow import InstalledAppFlow
import json, os

SCOPES = ['https://www.googleapis.com/auth/calendar']

flow = InstalledAppFlow.from_client_secrets_file("$CLIENT_SECRET", SCOPES)
# Console flow вместо local server — работает в любом TTY
creds = flow.run_local_server(port=0, prompt='consent', open_browser=True)

with open("$TOKEN_OUT", 'w') as f:
    f.write(creds.to_json())

print(f"OK: token saved to $TOKEN_OUT")
print(f"  expiry: {creds.expiry}")
print(f"  refresh_token: {'YES' if creds.refresh_token else 'NO'}")
PYEOF
