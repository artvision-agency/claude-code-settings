#!/usr/bin/env bash
# stop-unapproved-done.sh — Stop хук (warn-only)
#
# Правило explicit-approval-tracking.md (HARD): «deploy ≠ одобрено». Артефакт одобрен
# ТОЛЬКО после явного ОК Антона. Детект: ответ объявляет клиентский артефакт
# ОДОБРЕННЫМ/финальным/готовым-к-отправке-клиенту, НО в transcript сессии нет
# явного одобрения Антона → warn «помечай 'на ревью' пока нет ОК».
#
# Консервативно: триггер = утверждение приёмки клиентского артефакта (не bare «готово»).
# warn-only (exit 0). Bypass: APPROVED_OK=1

set -uo pipefail
[[ "${APPROVED_OK:-0}" == "1" ]] && exit 0

STDIN_JSON="$(cat 2>/dev/null || true)"
TRANSCRIPT=$(printf '%s' "$STDIN_JSON" | python3 -c "import sys,json
try: print(json.load(sys.stdin).get('transcript_path',''))
except: print('')" 2>/dev/null || echo "")
[[ -z "$TRANSCRIPT" || ! -f "$TRANSCRIPT" ]] && exit 0

python3 - "$TRANSCRIPT" <<'PY'
import json, sys, re
path=sys.argv[1]
rows=[]
with open(path) as f:
    for line in f:
        try: rows.append(json.loads(line))
        except: pass

# последний assistant-текст + все user-тексты сессии (для поиска одобрения)
last_text=""
user_texts=[]
for o in rows:
    t=o.get("type")
    if o.get("isSidechain"): continue
    c=o.get("message",{}).get("content","")
    def textof(c):
        if isinstance(c,list):
            return " ".join(b.get("text","") for b in c if isinstance(b,dict) and b.get("type")=="text")
        return c if isinstance(c,str) else ""
    if t=="user":
        user_texts.append(textof(c).lower())
    elif t=="assistant":
        tx=textof(c)
        if tx: last_text=tx

if not last_text: sys.exit(0)
low=last_text.lower()

# 1) утверждение ПРИЁМКИ клиентского артефакта (узко, не bare «готово»)
approve_claim=any(re.search(p,low) for p in [
    r'одобрен[оаы]',
    r'можно отправлять клиенту',
    r'готов[оа]?\s+к\s+отправке\s+клиенту',
    r'финальн\w*\s+верси',
    r'принят[оаы]\b',
    r'отправляй\w*\s+клиенту',
    r'(pass|verdict).{0,20}отправ',
])
# 2) клиентский контекст (КП/лендинг/деплой/клиент)
client_ctx=any(w in low for w in ['кп','лендинг','клиент','deploy','задеплоен','артвижн','artvision.pro/','review-url','на прод'])

# 3) было ли явное одобрение Антона в сессии?
anton_ok=any(re.search(r'\b(ок|окей|ok|good|гуд|принято|одобряю|отлично|то что нужно|годится|👍|апрув)\b',u) for u in user_texts)

if approve_claim and client_ctx and not anton_ok:
    sys.stderr.write(
"\n[VERIFY: explicit-approval — deploy≠одобрено] Ответ объявляет клиентский артефакт одобренным/финальным,\n"
"  но явного ОК Антона в сессии не было.\n"
"  Правило (HARD): артефакт = «на ревью» до явного одобрения. Деплой/PASS ≠ одобрение.\n"
"  Bypass: APPROVED_OK=1\n")
PY
exit 0
