#!/usr/bin/env bash
set -euo pipefail

# memory-recall.sh — обёртка для memory-search.py
# Вызывается из SessionStart хука или вручную.
# Принимает контекст из stdin или аргументом.
# Возвращает JSON с additionalContext для инъекции в промпт.
# NEVER exits with code 1 — graceful degradation only.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SEARCH_SCRIPT="${SCRIPT_DIR}/memory-search.py"

if [[ ! -f "$SEARCH_SCRIPT" ]]; then
    echo '{"additionalContext": ""}'
    exit 0
fi

# Получаем query: из аргументов или stdin
if [[ $# -gt 0 ]]; then
    QUERY="$*"
elif [[ ! -t 0 ]]; then
    QUERY="$(timeout 3 cat 2>/dev/null || true)"
else
    echo '{"additionalContext": ""}'
    exit 0
fi

if [[ -z "${QUERY:-}" ]]; then
    echo '{"additionalContext": ""}'
    exit 0
fi

# UTF-8 safe truncation (Python, not head -c which can split multi-byte chars)
QUERY_CLEAN="$(printf '%s' "$QUERY" | python3 -c "import sys; print(sys.stdin.read()[:200].strip())" 2>/dev/null || printf '%s' "$QUERY" | head -c 200)"

# Single invocation: get both JSON and readable format, build output in Python
timeout 8 python3 -c "
import json, sys, subprocess

search_script = sys.argv[1]
query = sys.argv[2]

# Get readable results
try:
    readable = subprocess.check_output(
        [sys.executable, search_script, query],
        stderr=subprocess.DEVNULL, timeout=6
    ).decode().strip()
except Exception:
    readable = ''

if not readable or readable.startswith('MEMORY RECALL: no'):
    print(json.dumps({'additionalContext': ''}))
else:
    ctx = '## Memory Recall (auto)\n\n' + readable + '\n\nRead relevant files if needed.'
    print(json.dumps({'additionalContext': ctx}, ensure_ascii=False))
" "$SEARCH_SCRIPT" "$QUERY_CLEAN" 2>/dev/null || echo '{"additionalContext": ""}'
