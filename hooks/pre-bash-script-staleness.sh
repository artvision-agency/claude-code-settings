#!/usr/bin/env bash
# pre-bash-script-staleness.sh — PreToolUse(Bash) WARN если запускается старый/непроверенный python-скрипт.
#
# Идея: каждый запуск `python3 ~/artvision-data/scripts/<path>/<script>.py` сравнивается
# с маркером `.last-success-<script>.json` в `.claude_temp_scripts/staleness-markers/`.
#
# WARN если:
#   1. Скрипт никогда не имел успешного запуска (маркера нет) И mtime скрипта старше 7 дней.
#      Значит скрипт изменён или новый — но никто не подтверждал что он работает.
#   2. Скрипт не запускался успешно >30 дней. Endpoint мог устареть (как `topvisor_bootstrap.py` 2026-05-20:
#      API v2 quirks накопились, скрипт не работал пока не пропатчили — `feedback_topvisor_api_v2_quirks.md`).
#
# Не блокирует — только WARN в stderr.
#
# Маркер обновляется НЕ хуком (хук работает ДО запуска). Обновление должен делать сам
# скрипт при успехе ИЛИ сторонний wrapper (TODO: PostToolUse hook).
#
# Bypass: SCRIPT_STALENESS_SKIP=1
#
# Exit codes: всегда 0 (warn-only)

set -uo pipefail

# 0. Bypass
[ "${SCRIPT_STALENESS_SKIP:-0}" = "1" ] && exit 0

# 1. Read stdin
INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# 2. Извлечь команду и проверить
RESULT=$(INPUT="$INPUT" python3 - << 'PYEOF' 2>/dev/null
import os, sys, json, re, time
from pathlib import Path

raw = os.environ.get("INPUT", "")
try:
    d = json.loads(raw)
except Exception:
    print("OK_NOT_JSON")
    sys.exit(0)

if d.get("tool_name") != "Bash":
    print("OK_NOT_BASH")
    sys.exit(0)

cmd = (d.get("tool_input") or {}).get("command", "") or ""
if not cmd:
    print("OK_EMPTY")
    sys.exit(0)

# Ищем `python3 <path>/scripts/<...>.py` или `python <path>/scripts/<...>.py`
# Target paths:
#   ~/artvision-data/scripts/*.py
#   ~/artvision-data/scripts/presale/*.py
#   ~/artvision-data/scripts/<любой_subdir>/*.py
home = Path.home()
av_scripts = home / "artvision-data" / "scripts"

# Regex: python(3)? <space> <path>.py — допускаем флаги -u, -m не интересуют здесь
# Подходящие варианты:
#   python3 ~/artvision-data/scripts/foo.py ...
#   python3 /Users/antonk/artvision-data/scripts/foo.py ...
#   python3 scripts/foo.py     (если cwd = artvision-data)
patterns = [
    r'python3?\s+(~/artvision-data/scripts/[\w./\-]+\.py)',
    r'python3?\s+(/Users/[^/\s]+/artvision-data/scripts/[\w./\-]+\.py)',
    r'python3?\s+(\$HOME/artvision-data/scripts/[\w./\-]+\.py)',
]

matched_paths = []
for pat in patterns:
    for m in re.finditer(pat, cmd):
        p = m.group(1)
        # Раскрыть ~/ и $HOME
        p = p.replace("~/", str(home) + "/")
        p = p.replace("$HOME", str(home))
        matched_paths.append(p)

# Не наш случай — exit OK
if not matched_paths:
    print("OK_NO_SCRIPT")
    sys.exit(0)

# Проверка каждого скрипта
markers_dir = home / ".claude_temp_scripts" / "staleness-markers"
markers_dir.mkdir(parents=True, exist_ok=True)

now = time.time()
warns = []

for spath in matched_paths:
    sp = Path(spath)
    if not sp.exists():
        # Скрипт не найден — это не наша зона ответственности, ошибка вылезет
        # при попытке запуска python3. Skip.
        continue

    # Sanity: путь должен быть внутри ~/artvision-data/scripts/
    try:
        sp_real = sp.resolve()
    except Exception:
        continue
    if not str(sp_real).startswith(str(av_scripts.resolve())):
        continue

    # Имя маркера — относительный путь от scripts/ с подменой / на __
    rel = sp_real.relative_to(av_scripts.resolve())
    marker_name = ".last-success-" + str(rel).replace("/", "__") + ".json"
    marker_path = markers_dir / marker_name

    script_mtime = sp_real.stat().st_mtime
    script_age_days = (now - script_mtime) / 86400

    if not marker_path.exists():
        # Никогда не запускался успешно
        if script_age_days > 7:
            warns.append({
                "script": str(rel),
                "type": "never_succeeded",
                "script_age_days": int(script_age_days),
                "marker": str(marker_path),
            })
        # else: новый скрипт, < 7 дней — не warn, нормально для свежесозданного
    else:
        marker_mtime = marker_path.stat().st_mtime
        days_since_success = (now - marker_mtime) / 86400
        if days_since_success > 30:
            warns.append({
                "script": str(rel),
                "type": "stale",
                "days_since_success": int(days_since_success),
                "marker": str(marker_path),
            })
        # Также: если script_mtime > marker_mtime, значит скрипт изменён после
        # последнего успеха — но не считаем это "никогда не работал", только
        # info. Возможный TODO: добавить третий тип warn "modified_after_success".
        elif script_mtime > marker_mtime:
            mod_days = (now - script_mtime) / 86400
            success_days = (now - marker_mtime) / 86400
            # Только если изменён давно (>3 дней назад) и с тех пор не было успеха
            if mod_days > 3 and (script_mtime - marker_mtime) > 3 * 86400:
                warns.append({
                    "script": str(rel),
                    "type": "modified_after_success",
                    "modified_days_ago": int(mod_days),
                    "last_success_days_ago": int(success_days),
                    "marker": str(marker_path),
                })

if not warns:
    print("OK_FRESH")
    sys.exit(0)

# Compose warn message
lines = []
for w in warns:
    if w["type"] == "never_succeeded":
        lines.append(
            f"  • {w['script']} — НЕТ marker'а успешного запуска "
            f"(скрипт изменён {w['script_age_days']} дней назад)"
        )
    elif w["type"] == "stale":
        lines.append(
            f"  • {w['script']} — последний успех {w['days_since_success']} "
            f"дней назад (>30, endpoint мог устареть)"
        )
    elif w["type"] == "modified_after_success":
        lines.append(
            f"  • {w['script']} — изменён {w['modified_days_ago']} дней назад, "
            f"последний успех {w['last_success_days_ago']} дней назад "
            f"(после изменения не подтверждён)"
        )

print("WARN:" + "\n".join(lines))
PYEOF
)

case "$RESULT" in
  WARN:*)
    BODY="${RESULT#WARN:}"
    {
      echo ""
      echo "⚠️  WARN: запускается скрипт без свежего подтверждения работоспособности:"
      echo ""
      echo "$BODY"
      echo ""
      echo "   Прецедент: 2026-05-20 topvisor_bootstrap.py — endpoint v2 quirks"
      echo "   накопились за время простоя, скрипт молча не работал до патча"
      echo "   (см. memory/feedback_topvisor_api_v2_quirks.md)."
      echo ""
      echo "   После успешного запуска — touch marker:"
      echo "     touch ~/.claude_temp_scripts/staleness-markers/.last-success-<script>.json"
      echo ""
      echo "   Bypass: SCRIPT_STALENESS_SKIP=1"
      echo ""
    } >&2
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
