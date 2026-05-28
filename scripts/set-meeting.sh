#!/usr/bin/env bash
# set-meeting.sh — создать событие в macOS Calendar через AppleScript
# Usage:
#   set-meeting.sh --date 2026-05-22 --time 10:30 --dur 60 --title "Встреча Univers Clinic" \
#                  [--calendar "Рабочий"] [--alarm-hours-before 22] [--desc "..."]
#
# Если у Антона добавлен Google-аккаунт через System Settings → Internet Accounts → Google
# (с включённым Calendars sync), событие можно ставить в Google-календарь:
#   --calendar "antoniokmr@gmail.com"  (или название Google-календаря)
# → автосинк в calendar.google.com через CalDAV.
#
# Если поставить в iCloud-календарь ("Рабочий"/"Домашний") — синк только в iPhone/iCloud.
#
# Прецедент: 2026-05-20 встреча Univers Clinic (session eefe3e2c).

set -euo pipefail

DATE=""
TIME=""
DUR_MIN=60
TITLE=""
CALENDAR=""
ALARM_HOURS_BEFORE=22
DESC=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --date) DATE="$2"; shift 2 ;;
    --time) TIME="$2"; shift 2 ;;
    --dur) DUR_MIN="$2"; shift 2 ;;
    --title) TITLE="$2"; shift 2 ;;
    --calendar) CALENDAR="$2"; shift 2 ;;
    --alarm-hours-before) ALARM_HOURS_BEFORE="$2"; shift 2 ;;
    --desc) DESC="$2"; shift 2 ;;
    -h|--help)
      grep -E "^#" "$0" | head -30
      exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$DATE" || -z "$TIME" || -z "$TITLE" ]]; then
  echo "ERROR: --date YYYY-MM-DD --time HH:MM --title <name> обязательны" >&2
  exit 1
fi

YEAR="${DATE%%-*}"
MM="${DATE#*-}"; MONTH="${MM%-*}"
DAY="${DATE##*-}"
HH="${TIME%:*}"
MIN="${TIME#*:}"

# Удалить ведущий ноль (AppleScript не любит "08")
MONTH=$((10#$MONTH))
DAY=$((10#$DAY))
HH=$((10#$HH))
MIN=$((10#$MIN))

# Маппинг номера месяца на AppleScript enum
MONTHS=(_ January February March April May June July August September October November December)
MONTH_NAME="${MONTHS[$MONTH]}"

ALARM_MIN=$((ALARM_HOURS_BEFORE * 60))
NEG_ALARM=$((-1 * ALARM_MIN))

# Fallback цепочка календарей если --calendar не задан
if [[ -z "$CALENDAR" ]]; then
  CAL_LIST='"Рабочий", "antoniokmr@gmail.com", "Домашний"'
else
  CAL_LIST="\"$CALENDAR\""
fi

TMPFILE=$(mktemp /tmp/set-meeting-XXXXXX.applescript)
cat > "$TMPFILE" <<APPLESCRIPT
tell application "Calendar"
    set targetCal to missing value
    set calNames to {$CAL_LIST}
    repeat with cn in calNames
        try
            set targetCal to calendar (cn as text)
            exit repeat
        end try
    end repeat
    if targetCal is missing value then
        set targetCal to calendar 1
    end if

    set startD to current date
    set year of startD to $YEAR
    set month of startD to $MONTH_NAME
    set day of startD to $DAY
    set hours of startD to $HH
    set minutes of startD to $MIN
    set seconds of startD to 0

    set endD to startD + ($DUR_MIN * 60)

    tell targetCal
        set newEvent to make new event with properties {summary:"$TITLE", start date:startD, end date:endD, description:"$DESC"}
        tell newEvent
            make new display alarm at end of display alarms with properties {trigger interval:$NEG_ALARM}
        end tell
    end tell

    log "OK: " & "$TITLE" & " in " & (title of targetCal) & " alarm -" & ($ALARM_HOURS_BEFORE) & "h"
end tell
APPLESCRIPT

osascript "$TMPFILE" 2>&1
rm -f "$TMPFILE"

# Дополнительно: если настроен Google Calendar OAuth — продублировать в Google
GCAL_TOKEN="$HOME/.claude/.cache/gcal-token.json"
GCAL_PY="$HOME/.claude/scripts/gcal.py"
if [[ -f "$GCAL_TOKEN" && -x "$GCAL_PY" ]]; then
  echo "→ дублирую в Google Calendar (primary)..."
  "$GCAL_PY" create \
    --calendar primary \
    --summary "$TITLE" \
    --start "$DATE $TIME" \
    --duration "$DUR_MIN" \
    --alarm-min "$ALARM_MIN" \
    --desc "$DESC" || echo "  gcal create failed (но macOS Calendar ОК)"
else
  echo "  Google Calendar: gcal-token нет → пропуск (одноразовая настройка: ~/.claude/scripts/gcal-bootstrap.sh)"
fi
