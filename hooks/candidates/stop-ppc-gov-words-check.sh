#!/usr/bin/env bash
# stop-ppc-gov-words-check.sh — PostToolUse(Write|Edit) WARN-only
# Детект гос/бюджетных маркеров в KEEP-наборе PPC-семантики коммерч.клиники.
# Правило: ppc-negative-keywords-clinic.md кат.5 (гос-слова всегда в минус для коммерч-клиник).
#
# Матчит файлы: clients/*/ppc/*semantics*/*commander*.csv|*commercial-final*.{csv,json}
# Если в фразах найдены гос-маркеры (поликлиника/самозапис/ОМС/госуслуг/...) → WARN (не блок).
#
# Bypass: GOV_WORDS_OK=1
# Exit: всегда 0 (warn-only — stderr виден Claude, но не блокирует).
#
# ⚠️ НЕ ЗАРЕГИСТРИРОВАН в settings.json — ждёт approve Антона (хук на 3 аккаунта).
set -uo pipefail
[ "${GOV_WORDS_OK:-0}" = "1" ] && exit 0

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0

FP=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    d=json.load(sys.stdin); ti=d.get("tool_input",{}) or {}
    print(ti.get("file_path","") if d.get("tool_name") in ("Write","Edit","MultiEdit") else "")
except Exception: print("")' 2>/dev/null)

# Только PPC-семантика commander/commercial
case "$FP" in
  */clients/*/ppc/*semantics*commander*.csv|*/clients/*/ppc/*commander-final.csv|\
  */clients/*/ppc/*commercial-final.csv|*/clients/*/ppc/*commercial-final.json) : ;;
  *) exit 0 ;;
esac
[ -f "$FP" ] || exit 0

GOV='поликлиник|самозапис|регистратур|талон|госуслуг|горздрав|gorzdrav|\bомс\b|по полису|бесплатн|льготн|квот|по месту жительств|по прописк'
HITS=$(grep -ioE "$GOV" "$FP" 2>/dev/null | sort | uniq -c | sort -rn | head -8)
[ -z "$HITS" ] && exit 0

{
  echo "⚠️ [ppc-gov-words] В KEEP-наборе PPC-семантики найдены ГОС/бюджетные маркеры:"
  echo "$HITS" | sed 's/^/   /'
  echo "   Файл: $FP"
  echo "   Правило ppc-negative-keywords-clinic.md кат.5 — гос-слова в минус для коммерч-клиники."
  echo "   Проверь лемма-фильтр движка (GOV_SOFT) / добавь в минус. Bypass: GOV_WORDS_OK=1"
} >&2
exit 0
