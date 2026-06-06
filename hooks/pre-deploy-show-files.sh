#!/usr/bin/env bash
# pre-deploy-show-files.sh — PreToolUse(Bash)
# Показывает ВСЕ файлы при любом деплое (scp/rsync/cp на сервер/git push клиентских HTML).
# warn-only: НЕ блокирует (exit 0), только выводит список Антону.
# Bypass: DEPLOY_SHOW_OFF=1
# Установлено: 2026-05-30 (запрос Антона «файлы все мне показывать всегда в деплое»).

[ "${DEPLOY_SHOW_OFF:-}" = "1" ] && exit 0

INPUT="$(cat)"

CMD="$(printf '%s' "$INPUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null)"
[ -z "$CMD" ] && exit 0

# Это деплой? scp / rsync / cp на /var/www|сервер / git push / deploy*.sh
echo "$CMD" | grep -qiE '(^|[;&| ])(scp|rsync)( |$)|cp .*(/var/www|@[0-9a-z.-]+:)|git +push|deploy[^ ]*\.sh|pm2 +(restart|reload)' || exit 0

# git push — показать изменённые файлы из неотправленных коммитов
if echo "$CMD" | grep -qiE 'git +push'; then
  CWD="$(printf '%s' "$INPUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("cwd",""))' 2>/dev/null)"
  [ -z "$CWD" ] && CWD="$PWD"
  RANGE="$(git -C "$CWD" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)"
  if [ -n "$RANGE" ]; then SPEC="@{u}..HEAD"; else SPEC="HEAD~1..HEAD"; fi
  STAT="$(git -C "$CWD" diff --stat $SPEC 2>/dev/null)"
  N="$(git -C "$CWD" diff --name-only $SPEC 2>/dev/null | grep -c .)"
  if [ -n "$STAT" ]; then
    echo "📦 GIT PUSH — изменённых файлов: ${N:-?} (неотправленные коммиты)"
    git -C "$CWD" diff --name-status $SPEC 2>/dev/null | sed 's/^/   /'
  else
    echo "📦 GIT PUSH обнаружен (репо: $CWD) — нет файлового diff (новые коммиты не определены)."
  fi
  exit 0
fi

printf '%s' "$INPUT" | DEPLOY_CMD="$CMD" python3 <<'PY'
import os, re, glob, shlex

cmd = os.environ.get("DEPLOY_CMD", "")
try:
    toks = shlex.split(cmd)
except Exception:
    toks = cmd.split()

files = []
seen = set()

def add(path):
    for p in sorted(glob.glob(path)) or [path]:
        ap = os.path.abspath(p)
        if ap in seen:
            continue
        seen.add(ap)
        if os.path.isdir(ap):
            for root, _, fs in os.walk(ap):
                for f in sorted(fs):
                    fp = os.path.join(root, f)
                    if fp not in seen:
                        seen.add(fp); files.append(fp)
        elif os.path.exists(ap):
            files.append(ap)
        else:
            files.append(p + "  (не найден локально)")

# собираем локальные пути-аргументы (не флаги, не remote host:path, не сама команда)
SKIP = {"scp","rsync","cp","ssh","git","push","pm2","restart","reload","sudo","bash","sh"}
for t in toks:
    if t in SKIP or t.startswith("-"):
        continue
    if re.search(r'@[\w.-]+:', t) or t.endswith(":"):   # remote target
        continue
    if "://" in t:
        continue
    # путь к локальному файлу/папке/glob
    if "/" in t or "*" in t or os.path.exists(t) or t.endswith((".html",".css",".js",".pdf",".png",".jpg",".md",".json")):
        add(t)

if not files:
    print("📦 ДЕПЛОЙ обнаружен — конкретные файлы не распознаны автоматически. Команда:")
    print("   " + cmd[:300])
    raise SystemExit(0)

print(f"📦 ДЕПЛОЙ — файлов: {len(files)}")
for f in files[:200]:
    sz = ""
    try:
        b = os.path.getsize(f)
        sz = f"  ({b//1024} KB)" if b >= 1024 else f"  ({b} B)"
    except Exception:
        pass
    print(f"   • {f}{sz}")
if len(files) > 200:
    print(f"   … и ещё {len(files)-200}")
PY

exit 0
