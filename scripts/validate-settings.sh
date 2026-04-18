#!/bin/bash
# Валидатор ссылок в settings.json — проверяет что все hook-команды существуют.
#
# Режимы:
#   validate-settings.sh           — CI-режим: exit 1 если битые, exit 0 если ок
#   validate-settings.sh --warn    — SessionStart-режим: всегда exit 0, печатает warning
set -euo pipefail

MODE="${1:-strict}"
if [[ "$MODE" != "strict" && "$MODE" != "--warn" ]]; then
    echo "usage: $0 [--warn]" >&2
    exit 2
fi
export VALIDATE_MODE="$MODE"

python3 <<'PY'
import json, os, shlex, sys
from pathlib import Path

HOME = str(Path.home())
MODE = os.environ.get("VALIDATE_MODE", "strict")
settings = Path(HOME) / ".claude" / "settings.json"

if not settings.exists():
    print("settings.json not found"); sys.exit(2)

SKIP_PREFIXES = ("echo", "cat", "true", "false", ":", "#", "printf")
SCRIPT_MARKERS = (".sh", ".py", "/hooks/", "/scripts/")

broken = []

def check(cmd, ctx):
    if not isinstance(cmd, str) or not cmd.strip():
        return
    if cmd.strip().startswith(SKIP_PREFIXES):
        return
    try:
        first = os.path.expanduser(shlex.split(cmd)[0])
    except ValueError:
        return
    if not first.startswith("/") or not any(m in first for m in SCRIPT_MARKERS):
        return
    if not os.path.exists(first):
        broken.append((ctx, first, "MISSING"))
    elif first.endswith(".sh") and not os.access(first, os.X_OK):
        broken.append((ctx, first, "NOT EXECUTABLE"))

def walk(node, path="root"):
    if isinstance(node, dict):
        if node.get("type") == "command":
            check(node.get("command", ""), path)
        for k, v in node.items():
            walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f"{path}[{i}]")

walk(json.loads(settings.read_text()))

if not broken:
    if MODE != "--warn":
        print("OK: all hook/script references valid")
    sys.exit(0)

if MODE == "--warn":
    print(f"⚠️  settings.json: {len(broken)} битых ссылок")
    for _, path, why in broken:
        print(f"    [{why}] {path}")
    print("Исправь: восстанови из git или убери ссылку из settings.json")
    sys.exit(0)
else:
    print(f"BROKEN REFERENCES in settings.json: {len(broken)}")
    for ctx, path, why in broken:
        print(f"  [{why}] {path}\n    at: {ctx}")
    sys.exit(1)
PY
