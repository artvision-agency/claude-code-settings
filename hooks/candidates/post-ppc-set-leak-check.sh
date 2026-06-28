#!/usr/bin/env bash
# post-ppc-set-leak-check.sh — PostToolUse(Write|Edit) WARN-only
# Детект протечек ТОВАР/ИНФО в KEEP-наборе PPC-семантики (должны быть OUT движком).
# Правило: WORKFLOW-SPEC-ppc-semantics ФАЗА 0.5 (7 фильтров OUT), ppc-launch-playbook.
#
# Матчит: clients/*/ppc/*commander-final.csv | *commercial-final.{csv,json}
# Товар/инфо в фразах → WARN (значит лемма-фильтр движка протёк).
#
# Bypass: SET_LEAK_OK=1
# Exit: всегда 0 (warn-only).
#
# ⚠️ НЕ ЗАРЕГИСТРИРОВАН в settings.json — ждёт approve Антона.
set -uo pipefail
[ "${SET_LEAK_OK:-0}" = "1" ] && exit 0

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0

FP=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    d=json.load(sys.stdin); ti=d.get("tool_input",{}) or {}
    print(ti.get("file_path","") if d.get("tool_name") in ("Write","Edit","MultiEdit") else "")
except Exception: print("")' 2>/dev/null)

case "$FP" in
  */clients/*/ppc/*commander-final.csv|*/clients/*/ppc/*commercial-final.csv|\
  */clients/*/ppc/*commercial-final.json) : ;;
  *) exit 0 ;;
esac
[ -f "$FP" ] || exit 0

# Товар (DIY/предметы) + инфо-маркеры — должны быть OUT движком
TOVAR='купить|паст[аы]|щётк|щетк|ирригатор|ополаскиват|зубочистк|ёршик|ершик|алиэкспресс|озон\b|вайлдберриз|wildberries|карандаш для отбел|полоск.*отбел'
INFO='что такое|как выбрать|больно ли|сколько служит|отзыв|рейтинг|реферат|пошагов|своими руками|в домашних'
TH=$(grep -ioE "$TOVAR" "$FP" 2>/dev/null | sort | uniq -c | sort -rn | head -6)
IH=$(grep -ioE "$INFO" "$FP" 2>/dev/null | sort | uniq -c | sort -rn | head -6)
[ -z "$TH" ] && [ -z "$IH" ] && exit 0

{
  echo "⚠️ [ppc-set-leak] В KEEP-наборе PPC-семантики возможны протечки ТОВАР/ИНФО (должны быть OUT):"
  [ -n "$TH" ] && { echo "   ТОВАР:"; echo "$TH" | sed 's/^/     /'; }
  [ -n "$IH" ] && { echo "   ИНФО:";  echo "$IH" | sed 's/^/     /'; }
  echo "   Файл: $FP"
  echo "   Проверь лемма-фильтры движка (TOVAR/INFO). Bypass: SET_LEAK_OK=1"
} >&2
exit 0
