#!/bin/bash
# PreToolUse(Write|Edit): блокирует client KP с CRITICAL bred (финансовка/internal markers/AI)
# Bypass: KP_BRED_OK=1
INPUT=$(cat)
TOOL=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)
FP=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin).get('tool_input',{}); print(d.get('file_path',''))" 2>/dev/null)
[ -z "$FP" ] && exit 0

# Только client KP файлы
case "$FP" in
  */clients/*/kp/*.html|*/clients/*/presale/kp/*.html|*/presales/*/kp/*.html|*/presale/*/kp/*.html|*/clients/*/presale/*kp*.html) ;;
  *) exit 0 ;;
esac

[ "$KP_BRED_OK" = "1" ] && exit 0

# После применения Edit — проверим финальный контент
CONTENT=$(echo "$INPUT" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('tool_input',{})
print(d.get('content') or d.get('new_string') or '', end='')
" 2>/dev/null)
[ -z "$CONTENT" ] && exit 0

# Quick check на CRITICAL паттерны в новом контенте
HITS=$(echo "$CONTENT" | python3 -c "
import sys, re
text = sys.stdin.read()
# Strip script/style/tags
text = re.sub(r'<script.*?</script>',' ',text,flags=re.S|re.I)
text = re.sub(r'<style.*?</style>',' ',text,flags=re.S|re.I)
text = re.sub(r'<[^>]+>',' ',text)
critical = []
if re.search(r'(Выручка\s*/\s*мес|ΔВыручк|чистая\s+прибыль|маржинальн[а-я]+\s+\d+\s*%|break.?even|точк[аи]\s+окупаем)', text, re.I):
    critical.append('FINANCIALS')
if re.search(r'\+\d{2,3}\s*\d{3}\s*₽', text):
    critical.append('REVENUE_DELTA')
if re.search(r'\bUNCONFIRMED\b|\bWebFetch\b|Topvisor\s+API|Wordstat\s+API', text):
    critical.append('INTERNAL_MARKERS')
if re.search(r'\bartvision\.pro\b', text):
    critical.append('ARTVISION_PRO')
if re.search(r'\bArtvision\s+(Flow|Watch|Radar|Scout|LinkForge|Insight|Leads|Content\s+Lab|Pulse|VoxRate|Lens|Funnel)\b', text):
    critical.append('ARTVISION_BRAND')
print(' '.join(critical))
")

if [ -n "$HITS" ]; then
  cat <<EOF
⛔ pre-kp-bred-block: ЗАБЛОКИРОВАНО

Файл: $FP
Критические нарушения в записываемом контенте: $HITS

Правила:
  • FINANCIALS — выручка/прибыль/ROI клиента в рублях запрещены в КП (feedback_no_client_financials_in_kp.md)
  • INTERNAL_MARKERS — UNCONFIRMED/CONFIRMED/WebFetch/curl/Topvisor API в видимом тексте (feedback_no_internal_markers_in_client_docs.md)
  • ARTVISION_PRO — упоминания artvision.pro в КП партнёра (AdvertMed)
  • ARTVISION_BRAND — Artvision Flow/Watch/Radar/etc в AdvertMed-материалах

Исправить до записи. Bypass на свой риск: KP_BRED_OK=1
EOF
  exit 2
fi

exit 0
