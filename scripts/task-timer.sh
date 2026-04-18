#!/bin/bash
set -euo pipefail
# Таймер работы над задачей с паузами и скриншотами
# Использование:
#   task-timer.sh start "Название задачи"   — начать
#   task-timer.sh pause                       — пауза
#   task-timer.sh resume                      — продолжить
#   task-timer.sh stop                        — остановить
#   task-timer.sh status                      — показать статус
#   task-timer.sh screenshot                  — сделать скриншот вручную

TIMER_DIR="$HOME/.claude/timer"
TIMER_FILE="$TIMER_DIR/current.json"
SCREENSHOTS_DIR="$TIMER_DIR/screenshots"

mkdir -p "$TIMER_DIR" "$SCREENSHOTS_DIR"

take_screenshot() {
    local task_name="${1:-task}"
    local safe_name
    safe_name=$(echo "$task_name" | tr ' /' '_' | tr -cd '[:alnum:]_-')
    local ts
    ts=$(date +%Y%m%d_%H%M%S)
    local file="$SCREENSHOTS_DIR/${safe_name}_${ts}.png"
    screencapture -x "$file" 2>/dev/null
    echo "$file"
}

calc_elapsed() {
    local now
    now=$(date +%s)
    local start_ts paused_total is_paused pause_start
    start_ts=$(python3 -c "import json; d=json.load(open('$TIMER_FILE')); print(d['start_ts'])")
    paused_total=$(python3 -c "import json; d=json.load(open('$TIMER_FILE')); print(d.get('paused_total',0))")
    is_paused=$(python3 -c "import json; d=json.load(open('$TIMER_FILE')); print(d.get('is_paused', False))")

    local elapsed=$(( now - start_ts - paused_total ))

    if [ "$is_paused" = "True" ]; then
        pause_start=$(python3 -c "import json; d=json.load(open('$TIMER_FILE')); print(d.get('pause_start',0))")
        local current_pause=$(( now - pause_start ))
        elapsed=$(( elapsed - current_pause ))
    fi

    echo "$elapsed"
}

format_time() {
    local secs=$1
    printf "%02d:%02d:%02d" $((secs/3600)) $(((secs%3600)/60)) $((secs%60))
}

case "${1:-status}" in
    start)
        local_task="${2:-Без названия}"
        local now_ts
        now_ts=$(date +%s)
        python3 << PYEOF
import json
data = {
    "task": "$local_task",
    "start_ts": $now_ts,
    "start_time": "$(date '+%Y-%m-%d %H:%M:%S')",
    "paused_total": 0,
    "is_paused": False,
    "pause_start": 0,
    "screenshots": [],
    "pauses": []
}
with open("$TIMER_FILE", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
PYEOF
        # Первый скриншот
        local ss
        ss=$(take_screenshot "$local_task")
        python3 << PYEOF
import json
with open("$TIMER_FILE") as f:
    d = json.load(f)
d["screenshots"].append({"time": "$(date '+%H:%M:%S')", "file": "$ss"})
with open("$TIMER_FILE", "w") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
PYEOF
        echo "TIMER START: $local_task ($(date '+%H:%M:%S'))"
        echo "Скриншот: $ss"
        ;;

    pause)
        if [ ! -f "$TIMER_FILE" ]; then
            echo "Нет активного таймера"
            exit 1
        fi
        local now_ts
        now_ts=$(date +%s)
        python3 << PYEOF
import json
with open("$TIMER_FILE") as f:
    d = json.load(f)
if d.get("is_paused"):
    print("Уже на паузе")
else:
    d["is_paused"] = True
    d["pause_start"] = $now_ts
    d["pauses"].append({"start": "$(date '+%H:%M:%S')"})
    with open("$TIMER_FILE", "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    print("PAUSED ($(date '+%H:%M:%S'))")
PYEOF
        ;;

    resume)
        if [ ! -f "$TIMER_FILE" ]; then
            echo "Нет активного таймера"
            exit 1
        fi
        local now_ts
        now_ts=$(date +%s)
        python3 << PYEOF
import json
with open("$TIMER_FILE") as f:
    d = json.load(f)
if not d.get("is_paused"):
    print("Не на паузе")
else:
    pause_duration = $now_ts - d["pause_start"]
    d["paused_total"] = d.get("paused_total", 0) + pause_duration
    d["is_paused"] = False
    d["pause_start"] = 0
    if d["pauses"]:
        d["pauses"][-1]["end"] = "$(date '+%H:%M:%S')"
        d["pauses"][-1]["duration_sec"] = pause_duration
    with open("$TIMER_FILE", "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    mins = pause_duration // 60
    print(f"RESUMED (пауза {mins} мин)")
PYEOF
        ;;

    stop)
        if [ ! -f "$TIMER_FILE" ]; then
            echo "Нет активного таймера"
            exit 1
        fi
        local elapsed
        elapsed=$(calc_elapsed)
        local formatted
        formatted=$(format_time "$elapsed")

        # Финальный скриншот
        local task_name
        task_name=$(python3 -c "import json; print(json.load(open('$TIMER_FILE'))['task'])")
        local ss
        ss=$(take_screenshot "$task_name")

        python3 << PYEOF
import json
with open("$TIMER_FILE") as f:
    d = json.load(f)
d["end_time"] = "$(date '+%Y-%m-%d %H:%M:%S')"
d["total_work_seconds"] = $elapsed
d["total_work_formatted"] = "$formatted"
d["screenshots"].append({"time": "$(date '+%H:%M:%S')", "file": "$ss"})

# Сохранить в архив
archive = f"$TIMER_DIR/completed_{d['task'].replace(' ','_')[:30]}_{d['start_time'][:10]}.json"
with open(archive, "w") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)

print(f"TIMER STOP: {d['task']}")
print(f"Начало:  {d['start_time']}")
print(f"Конец:   $(date '+%Y-%m-%d %H:%M:%S')")
print(f"Работа:  $formatted")
print(f"Пауз:   {len(d['pauses'])}")
print(f"Скриншотов: {len(d['screenshots'])}")
PYEOF
        rm -f "$TIMER_FILE"
        ;;

    screenshot)
        if [ ! -f "$TIMER_FILE" ]; then
            echo "Нет активного таймера"
            exit 1
        fi
        local task_name
        task_name=$(python3 -c "import json; print(json.load(open('$TIMER_FILE'))['task'])")
        local ss
        ss=$(take_screenshot "$task_name")
        python3 << PYEOF
import json
with open("$TIMER_FILE") as f:
    d = json.load(f)
d["screenshots"].append({"time": "$(date '+%H:%M:%S')", "file": "$ss"})
with open("$TIMER_FILE", "w") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
print("Screenshot: $ss")
PYEOF
        ;;

    status)
        if [ ! -f "$TIMER_FILE" ]; then
            echo "Нет активного таймера"
            exit 0
        fi
        local elapsed
        elapsed=$(calc_elapsed)
        local formatted
        formatted=$(format_time "$elapsed")
        python3 << PYEOF
import json
with open("$TIMER_FILE") as f:
    d = json.load(f)
status = "PAUSED" if d.get("is_paused") else "RUNNING"
print(f"Task:    {d['task']}")
print(f"Status:  {status}")
print(f"Started: {d['start_time']}")
print(f"Elapsed: $formatted")
print(f"Pauses:  {len(d['pauses'])}")
print(f"Screenshots: {len(d['screenshots'])}")
PYEOF
        ;;

    *)
        echo "Usage: task-timer.sh {start|pause|resume|stop|status|screenshot} [task name]"
        ;;
esac
