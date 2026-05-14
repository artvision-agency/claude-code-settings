#!/usr/bin/env bash
# stop-claim-no-rule-check.sh — Stop hook
# Если в последнем assistant-ответе есть фразы «в инструкциях нет X»,
# «правило не зафиксировано», «пробел в rules», «нигде нет правила» —
# обязательный grep по 3 источникам правил:
#   1. ~/.claude/rules/
#   2. ~/artvision-data/.claude/rules/
#   3. ~/.claude/projects/-Users-antonk/memory/
# + skills/*/SKILL.md
# Если ключевое слово/тема найдено в любом источнике — инжектируем warning,
# что утверждение «нет/пробел» было ложным и Claude должен исправить ответ.
#
# Bypass: NO_RULE_CHECK_OK=1
#
# Прецедент: 2026-05-11 я сказал «в rules/ нет SEMrush», но реально SEMrush
# был в artvision-data/.claude/rules/kp-brand.md, medical-kp.md, memory/MEMORY.md
# и 6 skills. Антон поймал руками.

set -uo pipefail

[[ "${NO_RULE_CHECK_OK:-0}" == "1" ]] && exit 0

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
[[ -z "$SESSION_ID" ]] && exit 0

TRANSCRIPT="$HOME/.claude/projects/-Users-antonk/${SESSION_ID}.jsonl"
[[ ! -f "$TRANSCRIPT" ]] && exit 0

# Извлечём последнее assistant-сообщение (text)
LAST_ASSISTANT=$(jq -r 'select(.message.role=="assistant") | .message.content[]? | select(.type=="text") | .text' "$TRANSCRIPT" 2>/dev/null | tail -100)

[[ -z "$LAST_ASSISTANT" ]] && exit 0

# Триггерные фразы (lowercase)
LAST_LOWER=$(echo "$LAST_ASSISTANT" | tr 'А-Я' 'а-я' | tr 'A-Z' 'a-z')

# Проверка на claim "нигде нет / пробел / не зафиксировано"
TRIGGER_REGEX='(нигде\s+(нет|не\s+упоминается|не\s+упомянуто))|(нет\s+правила)|(не\s+зафиксировано)|(пробел\s+в\s+(rules|правилах|инструкциях))|(в\s+(rules|правилах|инструкциях)\s+нет)|(в\s+ин(c|с)трукциях\s+(нет|пробел))|(no\s+rule\s+for)|(rule\s+(missing|absent))'

if ! echo "$LAST_LOWER" | grep -qE "$TRIGGER_REGEX"; then
    exit 0  # не было claim — пропускаем
fi

# Извлечём «тему» из ответа — берём 5 значимых слов вокруг trigger
# Простая эвристика — ищем CAPS-слова или известные tool names
TOPIC=$(echo "$LAST_ASSISTANT" | grep -oE '\b(SEMrush|SEMRUSH|Topvisor|TOPVISOR|Wordstat|Ahrefs|DataForSEO|GSC|Метрика|Вебмастер|PSI|Lighthouse|Webmaster)\b' | head -1)

[[ -z "$TOPIC" ]] && exit 0  # не нашли тему — не паниковать

# Проверим в 3 источниках + skills
FOUND=""
for src in "$HOME/.claude/rules" "$HOME/artvision-data/.claude/rules" "$HOME/.claude/projects/-Users-antonk/memory" "$HOME/.claude/skills"; do
    if [[ -d "$src" ]]; then
        if grep -ril "$TOPIC" "$src" 2>/dev/null | head -1 | grep -q .; then
            HITS=$(grep -ril "$TOPIC" "$src" 2>/dev/null | head -3)
            FOUND="$FOUND
  📁 $src:
$(echo "$HITS" | sed 's|^|    - |')"
        fi
    fi
done

if [[ -n "$FOUND" ]]; then
    cat >&2 <<EOF
⚠️  stop-claim-no-rule-check: ВНИМАНИЕ

Ты сказал что про «$TOPIC» нет правила / пробел / нигде не упомянуто.
НО реально упоминания НАЙДЕНЫ:
$FOUND

ДЕЙСТВИЕ: Перепроверь свой последний ответ.
- Если правило реально есть → исправь утверждение, сошлись на найденный файл.
- Если правило в найденных файлах НЕ актуально / устарело → так и скажи, не «нет», а «есть, но устарело».

Прецедент 2026-05-11: «в rules/ нет SEMrush» — оказалось SEMrush в kp-brand.md, medical-kp.md, memory, 6 skills.

Bypass: NO_RULE_CHECK_OK=1 (только если уверен что найденные упоминания не релевантны)
EOF
fi

exit 0  # Stop hook не блокирует — только warns
