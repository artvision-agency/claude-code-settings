#!/usr/bin/env bash
# pre-scp-no-assignees.sh — PreToolUse Bash hook (BLOCK)
#
# Правило client-plan-no-assignees-full-scope + project-tasks-single-source Правило 2 (HARD):
# в КЛИЕНТСКИХ планах/гантах/worklist НЕ показывать имена внутренних исполнителей.
# Детект: scp планового HTML клиента (plan/gantt/worklist/tracker) на review-URL,
# а файл СОДЕРЖИТ имена исполнителей (Андрей/Антон/Стас/Студент + «исполнитель») → BLOCK.
#
# Прецедент: USmile day-гант с «Исполнители: Антон/Андрей» — Антон: убрать, это для заказчика.
# Bypass: NO_ASSIGNEES_OK=1 (если это внутренняя версия, не для клиента)

set -uo pipefail
[[ "${NO_ASSIGNEES_OK:-0}" == "1" ]] && { cat; exit 0; }

INPUT="$(cat || true)"
CMD="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except: print("")' 2>/dev/null || true)"

# только scp клиентского планового HTML
echo "$CMD" | grep -qE 'scp' || { printf '%s' "$INPUT"; exit 0; }
LOCAL="$(echo "$CMD" | grep -oE 'clients/[^ ]+\.html' | head -1 || true)"
[[ -z "$LOCAL" ]] && { printf '%s' "$INPUT"; exit 0; }
# только planning-артефакты (plan/gantt/worklist/tracker)
echo "$LOCAL" | grep -qiE '(plan/|gantt|гант|worklist|ворклист|tracker)' || { printf '%s' "$INPUT"; exit 0; }

# резолв полного пути
FULL="$HOME/artvision-data/$LOCAL"
[[ -f "$FULL" ]] || FULL="$LOCAL"
[[ -f "$FULL" ]] || { printf '%s' "$INPUT"; exit 0; }

# грубый strip тегов → ищем имена ИСПОЛНИТЕЛЕЙ (не в произвольном тексте)
# триггер: «Исполнитель: <Имя>» / «Андрей/Антон/Стас/Студент» как who-метка
if grep -qiE '(исполнитель[^:]{0,3}:|assignee|who-name)' "$FULL" 2>/dev/null && \
   grep -qE 'Андрей|Антон|Стас|Студент' "$FULL" 2>/dev/null; then
  cat >&2 <<EOF
⛔ BLOCKED: клиентский плановый файл содержит имена внутренних исполнителей.

   Файл: $LOCAL
   Найдено: метка исполнителя + имя (Андрей/Антон/Стас/Студент).

   Правило (HARD): заказчик НЕ видит исполнителей. Сгенерируй КЛИЕНТСКУЮ версию
   (без имён, бейдж = «🟩 Artvision») из единого источника. Имена — только во
   внутренней версии / Asana / worklist-internal.

   Если это ВНУТРЕННЯЯ версия (не для клиента) — bypass: NO_ASSIGNEES_OK=1
EOF
  exit 2
fi

printf '%s' "$INPUT"
exit 0
