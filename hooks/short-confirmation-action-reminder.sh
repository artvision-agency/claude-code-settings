#!/bin/bash
# UserPromptSubmit hook: если пользователь пишет короткое подтверждение
# (го/делай/да/ок/+/yes/делай сам) И в моём предыдущем ответе было меню (A/B/C/D
# или "что выбираем" / "выбирай"), инжектит reminder ВЫПОЛНИТЬ предложение,
# а не давать новое меню.
#
# Прецедент 02.05.2026: 6+ меню подряд → Антон "запутался" + "не понимаю что мы делаем".
# Memory: feedback_short_confirmations_action_not_choice.md

set -euo pipefail

# Читаем JSON со stdin (UserPromptSubmit hook input)
INPUT=$(cat)

# Извлекаем prompt текущего пользователя (короткий?)
USER_PROMPT=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('prompt', '').strip())
except Exception:
    pass
" 2>/dev/null)

# Если prompt длиннее 30 символов — не короткое подтверждение, выходим
if [ -z "$USER_PROMPT" ] || [ ${#USER_PROMPT} -gt 30 ]; then
  exit 0
fi

# Проверка: prompt — короткое подтверждение?
# Регекс ловит: го/да/ок/yes/+/делай/делай сам/да го/го да/комбинации с пробелами и пунктуацией
if ! echo "$USER_PROMPT" | grep -qiE '^[[:space:]]*(го|да|ок|ok|yes|y|\+|делай([[:space:]]+сам)?|да[[:space:]]+го|го[[:space:]]+да|давай|погнали)[[:space:]!.?]*$'; then
  exit 0
fi

# Извлекаем последний ответ Claude из transcript (если возможно)
TRANSCRIPT_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('transcript_path', ''))
except Exception:
    pass
" 2>/dev/null)

if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
  exit 0
fi

# Берём последнее сообщение assistant — было ли там меню?
# Признаки меню: "что выбираем", "выбирай", "A/B/C", "**A**", "**B**", "1.", "2.", таблица с колонками
LAST_ASSISTANT=$(python3 - "$TRANSCRIPT_PATH" << 'PYEOF' 2>/dev/null
import json, sys
path = sys.argv[1]
last_assistant = ""
try:
    with open(path) as f:
        for line in f:
            try:
                msg = json.loads(line)
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        for block in content:
                            if block.get("type") == "text":
                                last_assistant = block.get("text", "")
                    elif isinstance(content, str):
                        last_assistant = content
            except Exception:
                continue
    print(last_assistant[-2000:])  # last 2000 chars only
except Exception:
    pass
PYEOF
)

# Эвристика: содержит ли ответ маркеры меню
if ! echo "$LAST_ASSISTANT" | grep -qiE '(что[[:space:]]+(выбираем|делаем)|выбирай|выбери|какой[[:space:]]+вариант|\*\*A\*\*|\*\*B\*\*|\*\*C\*\*|\*\*D\*\*|\| \*\*A\*\* \||\| \*\*B\*\* \||option [abcd])'; then
  # Меню не обнаружено — обычное короткое подтверждение, ничего не инжектим
  exit 0
fi

# Меню было И пользователь дал короткое подтверждение → инжектим reminder
cat <<EOF
[ACTION REQUIRED — короткое подтверждение пользователя]
Пользователь написал "${USER_PROMPT}" — это команда ВЫПОЛНЯТЬ предыдущее предложение, НЕ давать новое меню.

Если в предыдущем ответе было меню без явного default — выбери разумный default (самый безопасный/дешёвый/контекстуальный) и СРАЗУ ИСПОЛНЯЙ. Сообщи одной строкой: «Выбрал X — делаю» и переходи к действию.

ЗАПРЕЩЕНО: давать ещё одно меню A/B/C, спрашивать "что именно", уточнять выбор повторно.

Memory: feedback_short_confirmations_action_not_choice.md
EOF
