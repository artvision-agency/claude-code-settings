#!/bin/bash
# Stop hook: детектит галлюцинации в последнем assistant-ответе
# Regex на "магические числа" и нефальсифицируемые утверждения без источника
# → пишет флаг в /tmp/self-challenge-needed.json
# → UserPromptSubmit хук в следующий turn прочитает и вставит system-reminder

set -euo pipefail

FLAG_FILE="/tmp/self-challenge-needed.json"
STDIN_JSON="$(cat)"

# Достаём transcript_path
TRANSCRIPT=$(echo "$STDIN_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('transcript_path',''))" 2>/dev/null || echo "")

if [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; then
  exit 0
fi

# Достаём последний assistant message (text content, не tool_use)
LAST_MSG=$(python3 - "$TRANSCRIPT" << 'PYEOF'
import json, sys
path = sys.argv[1]
last = ""
with open(path) as f:
    for line in f:
        try:
            obj = json.loads(line)
        except:
            continue
        if obj.get("type") != "assistant": continue
        if obj.get("isSidechain"): continue
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
            last = "\n".join(buf)
print(last)
PYEOF
)

if [ -z "$LAST_MSG" ] || [ ${#LAST_MSG} -lt 200 ]; then
  exit 0
fi

# Скипаем если ответ сам про challenge/self-check/research отчёт
if echo "$LAST_MSG" | grep -qiE "challenge-self|self-challenge|CRAG|фактчек|\[CONFIRMED\]|\[UNCONFIRMED\]|\[ESTIMATED\]"; then
  exit 0
fi

# Детект паттернов галлюцинации
python3 - << PYEOF > "$FLAG_FILE.tmp" 2>/dev/null || exit 0
import re, json, os, sys
from datetime import datetime

text = """$(echo "$LAST_MSG" | sed 's/"/\\"/g' | head -c 8000)"""

patterns = {
    "magic_percent": r"(?<!\d)(\d{1,3}[-–]\d{1,3})\s*%",
    "magic_number": r"(?<!\d)(\d{1,4})\s*(?:раз|человек|клиент|посетитель|отзыв|заказ|лид)",
    "vague_frequency": r"\b(обычно|как правило|в среднем|примерно|чаще всего|большинство|как известно|считается|общеизвестно)\b",
    "confident_no_source": r"\b(работает так|это факт|точно знаю|гарантирую|доказано|исследования показывают)\b",
    "recommendation_pct": r"(рекоменд\w+|оптимально|идеально)[^.]*?\d+\s*%",
}

# URL в том же параграфе снимает флаг magic_*
has_urls = bool(re.search(r"https?://", text))
flags = []
for name, pat in patterns.items():
    matches = re.findall(pat, text, re.IGNORECASE)
    if matches:
        # фильтруем magic_percent если рядом URL есть (грубо — в тексте вообще)
        if name == "magic_percent" and has_urls:
            # всё равно флагаем, но с low-severity
            flags.append({"type": name, "matches": matches[:5], "severity": "low"})
        else:
            flags.append({"type": name, "matches": matches[:5], "severity": "high"})

if not flags:
    sys.exit(1)  # нет флагов — не пишем файл

out = {
    "timestamp": datetime.now().isoformat(),
    "flags": flags,
    "reason": "Ответ содержит цифры/утверждения без явного источника. Рекомендуется self-challenge."
}
print(json.dumps(out, ensure_ascii=False, indent=2))
PYEOF

if [ -s "$FLAG_FILE.tmp" ]; then
  mv "$FLAG_FILE.tmp" "$FLAG_FILE"
else
  rm -f "$FLAG_FILE.tmp"
fi

exit 0
