#!/bin/bash
# pre-scp-kp-strict-factcheck.sh — блокирует scp клиентского КП без strict-factcheck
# Прецедент: сессия adc5590f — 4 CRITICAL (Wink/0.62/Amazon EU) найдены ПОСЛЕ деплоя
# Bypass: FACTCHECK_STRICT_SKIP=1
set -euo pipefail
[[ "${FACTCHECK_STRICT_SKIP:-}" == "1" ]] && exit 0

INPUT=$(cat 2>/dev/null || true)
[[ -z "$INPUT" ]] && exit 0

# FAIL-CLOSED: обязательная зависимость python3 отсутствует — не можем выполнить проверку.
# Блокируем (exit 2), а не пропускаем молча.
if ! command -v python3 >/dev/null 2>&1; then
  echo "⛔ pre-scp-kp-strict-factcheck: python3 не найден — не можем проверить factcheck-отчёт." >&2
  echo "   Fail-closed: операция заблокирована." >&2
  echo "   Bypass: FACTCHECK_STRICT_SKIP=1" >&2
  exit 2
fi

TMPPY=$(mktemp /tmp/kp_factcheck_XXXXXX)
cat > "$TMPPY" << 'PYEOF'
import sys, json, re, os, glob
from datetime import datetime, timedelta

LOG_PATH = "/tmp/factcheck-hook-skip.log"
def log_skip(reason, cmd_preview=""):
    from datetime import datetime as _dt
    try:
        with open(LOG_PATH, "a") as f:
            f.write(f"[{_dt.now().isoformat()}] pre-scp-kp-strict-factcheck SKIP: {reason}\n")
            if cmd_preview:
                f.write(f"  cmd: {cmd_preview[:300]}\n")
    except Exception:
        pass

raw = sys.argv[1] if len(sys.argv) > 1 else ""
try:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("payload is not a JSON object")
    cmd = data.get("tool_input", {}).get("command", "")
except Exception as e:
    # FAIL-CLOSED: не смогли разобрать payload харнеса — не можем доказать,
    # что это безопасный (не-KP) scp. Блокируем (exit 2 для PreToolUse).
    log_skip(f"json.loads failed -> FAIL-CLOSED: {e}", raw[:200])
    print("⛔ pre-scp-kp-strict-factcheck: не удалось разобрать вход хука (JSON payload).", file=sys.stderr)
    print(f"   Причина: {e}", file=sys.stderr)
    print("   Fail-closed: операция заблокирована (не можем проверить, что это безопасный scp).", file=sys.stderr)
    print("   Bypass: FACTCHECK_STRICT_SKIP=1", file=sys.stderr)
    sys.exit(2)

if not cmd:
    # Нет команды в payload — scp этим вызовом не выполняется, классифицировать нечего.
    log_skip("empty cmd")
    sys.exit(0)

# Матчим scp по ДВУМ паттернам:
# 1) source path: presales/<slug>/kp/*.html
# 2) destination path: /var/www/artvision/kp/<slug>/
SRC_PAT = r"scp\s+.*presales/[\w-]+/kp/.*\.html"
DST_PAT = r"scp\s+.*/var/www/artvision/kp/[\w-]+/"
src_match = re.search(SRC_PAT, cmd, re.IGNORECASE)
dst_match = re.search(DST_PAT, cmd, re.IGNORECASE)
if not (src_match or dst_match):
    # Не KP-scp, тихо пропускаем
    sys.exit(0)

# Ищем slug — приоритет: source path → destination path
slug_m = re.search(r"presales/([\w-]+)/kp/", cmd) or re.search(r"/var/www/artvision/kp/([\w-]+)/", cmd)
slug = slug_m.group(1) if slug_m else None
if not slug:
    # FAIL-CLOSED: это точно KP-scp (совпал SRC/DST паттерн), но slug не извлечён —
    # не можем найти и проверить factcheck-отчёт. Блокируем (exit 2).
    log_skip("KP scp matched but slug not extracted -> FAIL-CLOSED", cmd[:200])
    print("⛔ pre-scp-kp-strict-factcheck: KP-scp обнаружен, но slug не извлечён из пути.", file=sys.stderr)
    print("   Fail-closed: не можем проверить наличие factcheck-отчёта.", file=sys.stderr)
    print(f"   cmd: {cmd[:200]}", file=sys.stderr)
    print("   Bypass: FACTCHECK_STRICT_SKIP=1", file=sys.stderr)
    sys.exit(2)

# Проверяем наличие свежего (< 2 часов) factcheck-отчёта
base = os.path.expanduser(f"~/artvision-data/presales/{slug}")
reports = glob.glob(f"{base}/factcheck-strict-*.md") + glob.glob(f"{base}/factcheck-*.md") + glob.glob(f"{base}/factcheck-{slug}*.md")
cutoff = datetime.now() - timedelta(hours=2)
fresh = []
for r in reports:
    try:
        if datetime.fromtimestamp(os.path.getmtime(r)) > cutoff:
            fresh.append(r)
    except OSError:
        # Не смогли прочитать mtime — не засчитываем как свежий (fail-closed по этому файлу).
        continue
if fresh:
    sys.exit(0)

print("⛔ pre-scp-kp-strict-factcheck: нет свежего factcheck-отчёта для KP!", file=sys.stderr)
if slug:
    print(f"   КП: {slug}", file=sys.stderr)
print("", file=sys.stderr)
print("   Запусти ПЕРЕД деплоем:", file=sys.stderr)
print("   strict-factchecker agent ИЛИ", file=sys.stderr)
print(f"   python3 ~/artvision-data/scripts/factcheck-v2.py --strict ~/artvision-data/presales/{slug or 'SLUG'}/kp/index.html", file=sys.stderr)
print("", file=sys.stderr)
print("   Bypass: FACTCHECK_STRICT_SKIP=1", file=sys.stderr)
# FAIL-CLOSED: PreToolUse блокирует только на exit 2 (exit 1 = warn-only).
sys.exit(2)
PYEOF

# Захватываем код выхода python без аборта от set -e.
STATUS=0
python3 "$TMPPY" "$INPUT" || STATUS=$?
rm -f "$TMPPY"

# Нормализация кодов: 0 = пропустить, 2 = блок (PreToolUse).
# Любой другой код (1, краш, segfault) трактуем как FAIL-CLOSED (exit 2),
# т.к. exit 1 для PreToolUse = warn-only и пропустил бы небезопасный scp.
if [[ "$STATUS" -eq 0 ]]; then
  exit 0
elif [[ "$STATUS" -eq 2 ]]; then
  exit 2
else
  echo "⛔ pre-scp-kp-strict-factcheck: проверка завершилась с непредвиденным кодом $STATUS — fail-closed (блок)." >&2
  echo "   Bypass: FACTCHECK_STRICT_SKIP=1" >&2
  exit 2
fi
