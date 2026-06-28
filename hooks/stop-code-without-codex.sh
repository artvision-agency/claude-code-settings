#!/usr/bin/env bash
# stop-code-without-codex.sh — Stop hook (warn-only). КАНДИДАТ — НЕ зарегистрирован в settings.json.
# Детектит: в сессии менялся код (.py/.js/.ts/.sh/.jsx/.tsx/.vue/.go) И нет признака Codex-ревью
# (нет вызова codex:codex-rescue / "codex review" / code-finisher / codex-dev-lifecycle) → warn.
# Правило: codex-dev-lifecycle.md (enforcement-primitives). Bypass: CODEX_LOOP_OK=1
set -euo pipefail
[ "${CODEX_LOOP_OK:-0}" = "1" ] && exit 0

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

printf '%s' "$INPUT" | python3 -c '
import sys, json

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tpath = data.get("transcript_path", "")
if not tpath:
    sys.exit(0)

CODE_EXT = (".py", ".js", ".ts", ".sh", ".jsx", ".tsx", ".vue", ".go")
CODEX_MARKERS = (
    "codex:codex-rescue", "codex-rescue", "codex review", "codex-ревью",
    "code-finisher", "codex-dev-lifecycle", "codex-петл", "кодекс-петл", "кодекс ревью",
)

code_changed = False
code_files = set()
codex_seen = False

try:
    f = open(tpath, "r")
except Exception:
    sys.exit(0)

with f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        raw = json.dumps(d, ensure_ascii=False).lower()
        if any(m in raw for m in CODEX_MARKERS):
            codex_seen = True
        msg = d.get("message", {})
        content = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") in ("Edit", "Write", "NotebookEdit"):
                    inp = c.get("input", {}) or {}
                    fp = (inp.get("file_path") or inp.get("notebook_path") or "").lower()
                    if fp.endswith(CODE_EXT):
                        code_changed = True
                        code_files.add(fp.rsplit("/", 1)[-1])

if code_changed and not codex_seen:
    files = ", ".join(sorted(code_files)[:5])
    sys.stderr.write("[CODEX-LOOP] ⚠️ В сессии менялся код (" + files + "), но нет признака Codex-ревью.\n")
    sys.stderr.write("Правило codex-dev-lifecycle: нетривиальный код (прод/клиент/инфра или >~50 строк) — через Codex-ревью. "
                     "Прогони /code-finisher (Workflow code-finisher) или codex:codex-rescue. "
                     "Тривиалка/конфиг/опечатка — игнорируй. Bypass: CODEX_LOOP_OK=1\n")
sys.exit(0)
' || true

exit 0
