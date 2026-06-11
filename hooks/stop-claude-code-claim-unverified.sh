#!/bin/bash
# Stop hook: детектит уверенные утверждения о механике Claude Code БЕЗ сверки со справкой.
# Прецедент: self-corrections.md #22 (EDUCATION session 2026-05-28) — 5 неверных утверждений
# про hooks/skills/CLAUDE.md из памяти, опровергнуты code.claude.com/docs.
# → пишет флаг /tmp/cc-claim-unverified-{session}.json + systemMessage warning
# Bypass: CC_CLAIM_OK=1

set -uo pipefail

if [ "${CC_CLAIM_OK:-}" = "1" ]; then
  exit 0
fi

STDIN_JSON="$(cat 2>/dev/null || echo '{}')"

TRANSCRIPT=$(echo "$STDIN_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('transcript_path',''))" 2>/dev/null || echo "")
SESSION=$(echo "$STDIN_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id','x'))" 2>/dev/null || echo "x")

if [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; then
  exit 0
fi

python3 - "$TRANSCRIPT" "$SESSION" << 'PYEOF'
import json, sys, re

path = sys.argv[1]
session = sys.argv[2]

# Собираем последний assistant text-ответ + проверяем был ли WebFetch на code.claude.com в этом turn
last_assistant = ""
turn_had_ccdocs_fetch = False

with open(path) as f:
    lines = f.readlines()

# Идём с конца: находим последний assistant message, и смотрим был ли в недавних
# tool_use WebFetch на code.claude.com (в пределах последних ~40 записей = текущий turn)
recent = lines[-60:] if len(lines) > 60 else lines
for line in recent:
    try:
        obj = json.loads(line)
    except Exception:
        continue
    # WebFetch на code.claude.com / docs.claude.com
    msg = obj.get("message", {})
    content = msg.get("content", "")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "tool_use":
                    inp = block.get("input", {})
                    url = str(inp.get("url", ""))
                    if "code.claude.com" in url or "docs.claude.com" in url or "docs.anthropic.com" in url:
                        turn_had_ccdocs_fetch = True
                # tool_result от WebFetch тоже может содержать docs
                if block.get("type") == "tool_result":
                    rc = str(block.get("content", ""))[:500]
                    if "code.claude.com" in rc or "docs.claude.com" in rc:
                        turn_had_ccdocs_fetch = True

# Последний assistant text
for line in lines:
    try:
        obj = json.loads(line)
    except Exception:
        continue
    if obj.get("type") != "assistant":
        continue
    if obj.get("isSidechain"):
        continue
    msg = obj.get("message", {})
    content = msg.get("content", "")
    buf = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                buf.append(block.get("text", ""))
    elif isinstance(content, str):
        buf.append(content)
    if buf:
        last_assistant = "\n".join(buf)

if not last_assistant or len(last_assistant) < 80:
    sys.exit(0)

# Если в ответе УЖЕ есть ссылка на справку — не флагаем
if re.search(r"code\.claude\.com|docs\.claude\.com|docs\.anthropic\.com", last_assistant):
    sys.exit(0)

# Если в этом turn был WebFetch справки — не флагаем
if turn_had_ccdocs_fetch:
    sys.exit(0)

# Термины механики Claude Code
cc_terms = re.compile(
    r"\b(hook|hooks|хук|хуки|skill|skills|скилл|subagent|субагент|"
    r"CLAUDE\.md|settings\.json|/compact|/clear|--resume|path-scoped|"
    r"PreToolUse|PostToolUse|SessionStart|file watcher|hot-swap)\b",
    re.IGNORECASE
)

# Модальность уверенного утверждения
modality = re.compile(
    r"\b(нужно|нужен|обязательн|требуется|не работает|только|нельзя|"
    r"не подхватыв|не перечит|перечитыва|выживает|не выживает|загружа|"
    r"require|must|always|never|cannot|reload|restart|рестарт)\b",
    re.IGNORECASE
)

cc_hits = cc_terms.findall(last_assistant)
mod_hits = modality.findall(last_assistant)

# Флагаем только если ОБА класса присутствуют (механика + уверенная модальность)
if len(cc_hits) >= 1 and len(mod_hits) >= 1:
    flag = {
        "type": "cc_claim_unverified",
        "cc_terms": list(set([h.lower() for h in cc_hits]))[:8],
        "modality": list(set([h.lower() for h in mod_hits]))[:8],
        "reason": "Утверждение о механике Claude Code без WebFetch на code.claude.com в этом turn. См. self-corrections #22.",
    }
    flag_file = f"/tmp/cc-claim-unverified-{session}.json"
    with open(flag_file, "w") as wf:
        json.dump(flag, wf, ensure_ascii=False, indent=2)

    out = {
        "systemMessage": (
            "[VERIFY: утверждение о механике Claude Code без сверки со справкой]\n"
            f"Термины: {', '.join(flag['cc_terms'])}. "
            "Прецедент self-corrections #22: 5 неверных утверждений из памяти (5 events→30+, "
            "рестарт hooks→file watcher и др.). Перед утверждением о hooks/skills/rules/CLI — "
            "WebFetch code.claude.com/docs. Bypass: CC_CLAIM_OK=1"
        )
    }
    print(json.dumps(out, ensure_ascii=False))

sys.exit(0)
PYEOF

exit 0
