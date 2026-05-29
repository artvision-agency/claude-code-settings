#!/bin/bash
# Stop hook: детектит негативные утверждения «нет / не нашёл / не существует»
# БЕЗ признаков multi-source поиска (grep/find/Read/cred-get/find-anywhere) в turn.
# Прецеденты false-negative: avprocontext пароль, SEMrush правило (#16), п/ф словарь (#11).
# → systemMessage warning. Bypass: FALSE_NEG_OK=1
# Связано: rules/no-false-negative.md, skills/find-anywhere, credentials-index.md

set -uo pipefail
[ "${FALSE_NEG_OK:-}" = "1" ] && exit 0

STDIN_JSON="$(cat 2>/dev/null || echo '{}')"
TRANSCRIPT=$(echo "$STDIN_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('transcript_path',''))" 2>/dev/null || echo "")
SESSION=$(echo "$STDIN_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id','x'))" 2>/dev/null || echo "x")

[ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ] && exit 0

python3 - "$TRANSCRIPT" "$SESSION" << 'PYEOF'
import json, sys, re

path, session = sys.argv[1], sys.argv[2]
try:
    lines = open(path).readlines()
except Exception:
    sys.exit(0)

# Был ли в текущем turn (последние ~50 записей) multi-source поиск?
turn_had_search = False
recent = lines[-50:] if len(lines) > 50 else lines
for line in recent:
    try:
        obj = json.loads(line)
    except Exception:
        continue
    msg = obj.get("message", {})
    content = msg.get("content", "")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                name = block.get("name", "")
                inp = json.dumps(block.get("input", {}), ensure_ascii=False).lower()
                # grep/glob/read multi или явные источники доступов
                if name in ("Grep", "Glob"):
                    turn_had_search = True
                if name == "Bash" and re.search(r"grep -ril|grep -il|find .*-name|cred-get|git log -s|git log -s", inp, re.I):
                    turn_had_search = True
                if name == "Skill" and ("find-anywhere" in inp or "shorthand" in inp):
                    turn_had_search = True

# Последний assistant text
last = ""
for line in lines:
    try:
        obj = json.loads(line)
    except Exception:
        continue
    if obj.get("type") != "assistant" or obj.get("isSidechain"):
        continue
    content = obj.get("message", {}).get("content", "")
    buf = []
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                buf.append(b.get("text", ""))
    elif isinstance(content, str):
        buf.append(content)
    if buf:
        last = "\n".join(buf)

if not last or len(last) < 30:
    sys.exit(0)
if turn_had_search:
    sys.exit(0)

# Если ответ уже честно перечисляет ГДЕ искал — не флагаем
if re.search(r"не найдено в:|искал по:|проверил источник", last, re.I):
    sys.exit(0)

# Негативные утверждения (категоричные, без оговорки источников)
neg = re.compile(
    r"(нет доступа|не нашёл|не нашел|не существует|нигде нет|"
    r"нет токена|нет пароля|нет такого правила|нет правила|пробел в правил|"
    r"не зафиксировано|такого нет|этого нет у нас|"
    r"\bnot found\b|\bno such\b|doesn't exist|does not exist)",
    re.IGNORECASE
)
hits = neg.findall(last)
if hits:
    flag = {"type": "false_negative", "matches": list({h.lower() if isinstance(h,str) else h for h in hits})[:5]}
    with open(f"/tmp/false-negative-{session}.json", "w") as wf:
        json.dump(flag, wf, ensure_ascii=False)
    out = {"systemMessage": (
        "[VERIFY: «нет/не нашёл» без multi-source поиска?]\n"
        "Перед негативным выводом — /find-anywhere или cred-get.sh (tokens.json + access.md + "
        "memory + jsonl + Keychain + git log -S). Прецеденты #11/#16/#20: «нет» оказывалось «есть». "
        "Если реально пусто — указать ГДЕ искал, не «нет». Bypass: FALSE_NEG_OK=1"
    )}
    print(json.dumps(out, ensure_ascii=False))

sys.exit(0)
PYEOF

exit 0
