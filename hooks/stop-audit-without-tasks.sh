#!/usr/bin/env bash
# stop-audit-without-tasks.sh — Stop хук (warn-only)
#
# Правило audit-findings-to-tasks.md (HARD): аудит с находками ОБЯЗАН породить задачи.
# Детект: последний ответ содержит явные находки аудита (N CRITICAL / найдено N проблем/
# ошибок/gaps) НО в этом turn не было TaskCreate → warn «находки без задач».
#
# warn-only (exit 0) — НИКОГДА не блокирует. Bypass: AUDIT_TASKS_OK=1

set -uo pipefail
[[ "${AUDIT_TASKS_OK:-0}" == "1" ]] && exit 0

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

# 1) последний assistant-текст + 2) был ли TaskCreate ПОСЛЕ последнего user-промпта (этот turn)
last_user_idx=-1
for i,o in enumerate(rows):
    if o.get("type")=="user" and not o.get("isSidechain"): last_user_idx=i
turn=rows[last_user_idx+1:] if last_user_idx>=0 else rows

last_text=""
taskcreate=False
for o in turn:
    if o.get("type")!="assistant" or o.get("isSidechain"): continue
    c=o.get("message",{}).get("content","")
    if isinstance(c,list):
        for b in c:
            if not isinstance(b,dict): continue
            if b.get("type")=="text": last_text=b.get("text","")
            if b.get("type")=="tool_use" and b.get("name") in ("TaskCreate","mcp__asana__asana_create_task","mcp__claude_ai_Asana__create_tasks","mcp__claude_ai_Asana__create_task_confirm"):
                taskcreate=True
    elif isinstance(c,str):
        last_text=c

if not last_text:
    sys.exit(0)
low=last_text.lower()

# Узкий триггер находок аудита (не любой «готово»)
patterns=[
    r'\bcritical\b',
    r'найдено\s+\d+\s+(проблем|ошиб|критич|наруш|gap|замечан)',
    r'\d+\s+critical',
    r'обнаружен[оы]?\s+\d+\s+(проблем|ошиб|уязвим|критич)',
    r'\b\d+\s+(уязвимост|критичн[ыа])',
    r'найдены?\s+(проблем|ошибк|нарушен|уязвим)',
]
hit=any(re.search(p,low) for p in patterns)
# контекст аудита (а не просто слово critical в коде)
audit_ctx=any(w in low for w in ['аудит','audit','ревью','review','проверк','находк','finding','уязвим','severity'])

if hit and audit_ctx and not taskcreate:
    sys.stderr.write(
"\n[VERIFY: audit-findings-to-tasks] Похоже, в ответе есть находки аудита, но TaskCreate в этом turn не было.\n"
"  Правило (HARD): КАЖДАЯ находка → отдельная задача (TaskCreate + Asana если клиентская).\n"
"  Аудит без задач = «отчёт в стол». Bypass: AUDIT_TASKS_OK=1\n")
PY
exit 0
