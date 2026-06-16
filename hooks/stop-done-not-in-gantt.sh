#!/usr/bin/env bash
# stop-done-not-in-gantt.sh — Stop хук (warn-only)
#
# Правило project-tasks-single-source Правило 6 (Антон 2026-06-16, HARD):
# «готово/сделано/закрыто» по задаче проекта → ОБЯЗАТЕЛЬНО отметить в ганте/worklist.
# Детект: ответ объявляет ЗАКРЫТИЕ задачи проекта, но в этом turn НЕ было Edit/Write
# в plan/gantt/worklist/tracker → warn.
#
# Консервативно: триггер = закрытие-задачи + project-контекст (не любой «готово»).
# warn-only (exit 0). Bypass: GANTT_DONE_OK=1

set -uo pipefail
[[ "${GANTT_DONE_OK:-0}" == "1" ]] && exit 0

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

last_user=-1
for i,o in enumerate(rows):
    if o.get("type")=="user" and not o.get("isSidechain"): last_user=i
turn=rows[last_user+1:] if last_user>=0 else rows

last_text=""
gantt_edit=False
for o in turn:
    if o.get("type")!="assistant" or o.get("isSidechain"): continue
    c=o.get("message",{}).get("content","")
    if isinstance(c,list):
        for b in c:
            if not isinstance(b,dict): continue
            if b.get("type")=="text": last_text=b.get("text","")
            if b.get("type")=="tool_use" and b.get("name") in ("Edit","Write","MultiEdit"):
                fp=(b.get("input",{}) or {}).get("file_path","").lower()
                if re.search(r'(gantt|гант|worklist|ворклист|tracker|/plan/|task-plan)',fp):
                    gantt_edit=True
    elif isinstance(c,str):
        last_text=c

if not last_text: sys.exit(0)
low=last_text.lower()

# закрытие задачи (не bare «готово»)
closure=any(re.search(p,low) for p in [
    r'задач\w*\s+(готов|закрыт|выполнен|сделан|завершен|заверш[её]н)',
    r'(закрыл|закрыт[аоы]?|выполнил|завершил|отметил)\s+задач',
    r'отмеч\w*\s+(выполненн|закрыт|готов|сделан)',
    r'готово по задаче',
    r'(task|задача)\b.{0,30}\b(completed|done|closed)\b',
])
# project-контекст (а не код/инфра «готово»)
proj=any(w in low for w in ['проект','клиент','client','гант','gantt','worklist','ворклист'])
# slug-маркеры клиентов (частые)
slug=re.search(r'\b(usmile|otido|blumart|творим|tvorim|madwave|avtoworld|burenie|geely|grelka|doctra|ant[\s-]?partners)\b',low)

if closure and (proj or slug) and not gantt_edit:
    sys.stderr.write(
"\n[VERIFY: Rule 6 — готово→гант] Объявлено закрытие задачи проекта, но Edit/Write в гант/worklist в этом turn не было.\n"
"  Правило (HARD, 16.06): «готово/сделано/закрыто» по задаче → ОБЯЗАТЕЛЬНО отметить в ганте/worklist (единый источник).\n"
"  Задача не закрыта, пока статус не в ганте. Bypass: GANTT_DONE_OK=1\n")
PY
exit 0
