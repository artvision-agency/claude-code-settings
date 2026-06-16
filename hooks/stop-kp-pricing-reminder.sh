#!/usr/bin/env bash
# stop-kp-pricing-reminder.sh — Stop хук (warn-only, дедуп раз/сессию)
#
# Правила client-pricing-policy + revenue-accounting (HARD). ТОЧНЫЙ gate невозможен:
# выручка клиента не доступна программно → это РЕМАЙНДЕР, не проверка.
# Детект: в ответе фигурирует КП/тариф клиента с ценой (₽/тариф/пакет) → один раз
# за сессию напомнить сверить цену vs выручка (0.5-1.5%) + passthrough≠MRR + источник.
#
# warn-only (exit 0), дедуп /tmp/kp-pricing-warned-$SESSION. Bypass: KP_PRICING_OK=1

set -uo pipefail
[[ "${KP_PRICING_OK:-0}" == "1" ]] && exit 0

STDIN_JSON="$(cat 2>/dev/null || true)"
SID=$(printf '%s' "$STDIN_JSON" | python3 -c "import sys,json
try: print(json.load(sys.stdin).get('session_id',''))
except: print('')" 2>/dev/null || echo "")
TRANSCRIPT=$(printf '%s' "$STDIN_JSON" | python3 -c "import sys,json
try: print(json.load(sys.stdin).get('transcript_path',''))
except: print('')" 2>/dev/null || echo "")
[[ -z "$TRANSCRIPT" || ! -f "$TRANSCRIPT" ]] && exit 0
# дедуп раз/сессию
MARK="/tmp/kp-pricing-warned-${SID:-nosess}"
[[ -f "$MARK" ]] && exit 0

python3 - "$TRANSCRIPT" <<'PY'
import json, sys, re
path=sys.argv[1]; last=""
rows=[]
with open(path) as f:
    for line in f:
        try: rows.append(json.loads(line))
        except: pass
for o in rows:
    if o.get("type")!="assistant" or o.get("isSidechain"): continue
    c=o.get("message",{}).get("content","")
    if isinstance(c,list):
        tx=" ".join(b.get("text","") for b in c if isinstance(b,dict) and b.get("type")=="text")
        if tx: last=tx
    elif isinstance(c,str): last=c
if not last: sys.exit(1)
low=last.lower()
# КП/тариф-контекст + цена
kp_ctx=any(w in low for w in ['кп','коммерческое предложение','тариф','пакет','presale-kp','стоимость услуг'])
price=bool(re.search(r'\d[\d\s.,]*\s*(₽|руб|k\b|к/мес|тыс|000)', low)) or 'к/мес' in low
if kp_ctx and price:
    sys.exit(0)   # триггерим
sys.exit(1)
PY
rc=$?
if [[ $rc -eq 0 ]]; then
  touch "$MARK" 2>/dev/null || true
  cat >&2 <<EOF

[VERIFY: client-pricing] В ответе — КП/тариф клиента с ценой. Сверь (HARD-правила):
  • цена ≈ 0.5-1.5% годовой выручки клиента (ФНС/checko) — согласовать с Антоном ДО отправки
  • passthrough (рекламный бюджет) НЕ в MRR (revenue-accounting)
  • каждая цена/число — источник + дата (медицина: «от», ФЗ-323)
  Это напоминание (выручка не проверяется автоматически). Bypass: KP_PRICING_OK=1
EOF
fi
exit 0
