#!/usr/bin/env bash
# stop-finance-gate.sh — Stop hook. Hard-enforce финанс-гейта (finance-password-gate.md).
# Детектит суммы/MRR/стоимость в последнем ответе БЕЗ маркера разблокировки сессии → warn.
# Маркер: /tmp/finance-unlocked-<session_id> (создаётся при вводе пароля 151064).
# Bypass: FINANCE_GATE_OK=1
set -uo pipefail
[ "${FINANCE_GATE_OK:-0}" = "1" ] && exit 0

INPUT="$(cat 2>/dev/null || true)"
SID=$(printf '%s' "$INPUT" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("session_id",""))' 2>/dev/null)
TRANSCRIPT=$(printf '%s' "$INPUT" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("transcript_path",""))' 2>/dev/null)

# разблокировано в этой сессии → пропускаем
[ -n "$SID" ] && [ -f "/tmp/finance-unlocked-${SID}" ] && exit 0

# взять последний assistant-текст (хвост транскрипта, не весь файл)
[ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ] && exit 0
LAST=$(tail -c 60000 "$TRANSCRIPT" 2>/dev/null | python3 -c '
import sys,json
last=""
for line in sys.stdin:
    line=line.strip()
    if not line: continue
    try:
        d=json.loads(line)
    except: continue
    if d.get("type")=="assistant":
        msg=d.get("message",{})
        for c in (msg.get("content") or []):
            if isinstance(c,dict) and c.get("type")=="text":
                last=c.get("text","")
print(last)
' 2>/dev/null)
[ -z "$LAST" ] && exit 0

# финансовые паттерны: суммы с ₽/руб, "N К/мес", MRR, "стоимость ... N", тыс.руб
if printf '%s' "$LAST" | grep -qiE '[0-9][0-9 .,]*[KКkК]?[ ]*(₽|руб|RUB|/мес|К/мес|тыс)|MRR|выручк[аи][^a-zа-я]*[0-9]|стоимост[ьи][^.]{0,40}[0-9]{3,}'; then
  echo "[FINANCE-GATE] ⚠️ В ответе похоже есть финансовые цифры (суммы/MRR/стоимость), а пароль в этой сессии НЕ введён (нет /tmp/finance-unlocked-${SID})." >&2
  echo "Правило finance-password-gate.md: показ финансов на экране — только после пароля. Если это была ЗАПИСЬ факта (не показ) или ложное срабатывание — игнорируй. Bypass: FINANCE_GATE_OK=1" >&2
fi
exit 0
