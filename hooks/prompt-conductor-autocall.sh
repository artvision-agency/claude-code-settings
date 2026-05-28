#!/usr/bin/env bash
# prompt-conductor-autocall.sh — UserPromptSubmit hook
#
# Автовызов Conductor (Spec-Driven Development) для крупных task'ов:
# - >= 5 шагов / multi-step
# - "новая фича / новый КП с нуля / спроектируй систему"
# - >100 слов промпт
# - revenue-критичные клиентские задачи
#
# Инжектит system-reminder в Claude promptUseSubmit context чтобы Claude
# вызвал /conductor:new <description> ПЕРЕД implementation.
#
# Self-disable триггеры:
# - В transcript уже есть /conductor:* вызов в текущей сессии
# - Промпт <30 слов (короткое продолжение / уточнение)
# - Промпт в shorthand: "го", "да", "uj", "пуш", "синк", "stop", etc
# - В промпте уже есть /conductor: (явно вызван)
#
# Bypass: CONDUCTOR_AUTOCALL_OFF=1

set -uo pipefail

# Bypass
[ "${CONDUCTOR_AUTOCALL_OFF:-0}" = "1" ] && exit 0

# Read JSON stdin
INPUT=$(cat 2>/dev/null || true)
[ -z "$INPUT" ] && exit 0

SESSION_ID=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")
PROMPT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('prompt',''))" 2>/dev/null || echo "")

[ -z "$PROMPT" ] && exit 0
[ -z "$SESSION_ID" ] && exit 0

# Self-disable если уже вызывался Conductor в этой сессии
TRANSCRIPT="$HOME/.claude/projects/-Users-antonk/${SESSION_ID}.jsonl"
if [ -f "$TRANSCRIPT" ]; then
  if grep -q "/conductor:" "$TRANSCRIPT" 2>/dev/null; then
    exit 0
  fi
fi

# Skip явно вызван Conductor в текущем промпте
if echo "$PROMPT" | grep -qE "/conductor:"; then
  exit 0
fi

# Skip коротких промптов (shorthand / уточнения)
WORD_COUNT=$(echo "$PROMPT" | wc -w | tr -d ' ')
[ "$WORD_COUNT" -lt 30 ] && exit 0

# Skip shorthand-фраз (даже если они в составе длинного промпта в начале)
FIRST_LINE=$(echo "$PROMPT" | head -1 | tr -d '\r')
case "$FIRST_LINE" in
  "го"|"да"|"uj"|"da"|"стоп"|"stop"|"пуш"|"push"|"синк"|"sync"|"туду"|"что нового"|"all stuff ready"|"done?"|"готово?"|"finish"|"finish?"|"все"|"все?"|"go"|"go on"|"continue"|"продолжай"|"ok"|"ок"|"спасибо"|"thanks")
    exit 0
    ;;
esac

# Триггеры для автовызова Conductor:
TRIGGER_REASON=""

# A) Multi-step indicators (5+ шагов через нумерацию)
NUM_STEPS=$(echo "$PROMPT" | grep -cE "^\s*[0-9]+[).:] " 2>/dev/null)
NUM_STEPS=${NUM_STEPS:-0}
if [ "$NUM_STEPS" -ge 4 ] 2>/dev/null; then
  TRIGGER_REASON="$TRIGGER_REASON multi-step($NUM_STEPS)"
fi

# B) Большой промпт >100 слов
if [ "$WORD_COUNT" -gt 100 ]; then
  TRIGGER_REASON="$TRIGGER_REASON big-prompt($WORD_COUNT-words)"
fi

# C) Ключевые слова новой фичи / системы
if echo "$PROMPT" | grep -qiE "новая фича|спроектируй|спроектиров|сделай систему|design and implement|build from scratch|новый КП|новый клиент|нового клиента|onboard|новый продукт|новый продукт|архитектур|architecture|migration|миграция|реструктуриз|refactor.*проект|новый бот|новый скилл|весь pipeline|полный pipeline|с нуля|from scratch|новое приложение|новый сайт|новая страница|новая система"; then
  TRIGGER_REASON="$TRIGGER_REASON feature-keyword"
fi

# D) Множество глаголов императив (делай X, потом Y, затем Z)
IMPERATIVE_VERBS=$(echo "$PROMPT" | grep -oiE "сделай|собери|настрой|развернуть|добавь|удали|перенеси|интегрируй|переписать|задеплой|поправь|допили" | wc -l | tr -d ' ')
if [ "$IMPERATIVE_VERBS" -ge 5 ]; then
  TRIGGER_REASON="$TRIGGER_REASON $IMPERATIVE_VERBS-verbs"
fi

# Нет триггеров — не показываем
[ -z "$TRIGGER_REASON" ] && exit 0

# Snooze через флаг (если в последние 10 минут уже показывали)
SNOOZE_FILE="/tmp/conductor-autocall-snooze-${SESSION_ID}"
if [ -f "$SNOOZE_FILE" ]; then
  AGE=$(($(date +%s) - $(stat -f%m "$SNOOZE_FILE" 2>/dev/null || echo 0)))
  if [ "$AGE" -lt 600 ]; then
    exit 0  # snooze 10 мин
  fi
fi
touch "$SNOOZE_FILE"

# Инжект suggestion
cat <<EOF
[CONDUCTOR-AUTOCALL] Эта задача выглядит крупной (триггеры:$TRIGGER_REASON).

Рекомендую перед implementation вызвать **Spec-Driven Development**:
  → \`/conductor:new <короткое описание задачи>\`

Conductor создаст:
- spec.md — детальные требования
- plan.md — пошаговый checklist
- Потом implement по плану с проверкой каждого шага

Альтернатива: продолжай как обычно (hook молчит 10 мин).
Bypass на сессию: \`CONDUCTOR_AUTOCALL_OFF=1\`
EOF
exit 0
