#!/usr/bin/env bash
# prompt-correction-detector.sh — UserPromptSubmit хук.
# Детектит correction-сигналы Антона («опять / постоянно прошу / уже говорил»).
# Инжектит напоминание что правило есть — нужно превратить в хук.
# Источник: prompt-pattern-analysis-2026-05-13.md (21 случай за 6 мес)
# Bypass: CORRECTION_DETECT_OFF=1

[[ "${CORRECTION_DETECT_OFF:-}" == "1" ]] && exit 0

INPUT=$(cat 2>/dev/null || echo '{}')
PROMPT=$(echo "$INPUT" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("prompt",""))' 2>/dev/null)
[[ -z "$PROMPT" ]] && exit 0

# Regex: correction-сигналы
if echo "$PROMPT" | grep -iqE "(опять|постоянно (про)?шу|снова забыл|уже говорил|я же говорил|почему ты|не учёл|не учитываешь|каждый раз|просил тебя|сколько раз)"; then
    cat <<'NOTICE'
[CORRECTION DETECTED]
Антон только что дал correction-сигнал. По prompt-pattern-analysis 2026-05-13 у нас 21 такой случай за 6 мес — большинство означают «правило есть, но не enforce'ится автоматически».

ПРОТОКОЛ (см. ~/.claude/rules/self-corrections.md, МЕТА-ПРАВИЛО):
1. Найди существующее правило — grep ~/.claude/rules/ и memory/feedback_*.md
2. Если правило есть, но нет хука → создай PreToolUse/Stop хук под него
3. Если правила нет → добавь в self-corrections.md или нужный feedback_*.md
4. Зафиксируй ситуацию в TaskCreate чтобы не потерять

Не отделайся ответом «учту» — это уже не сработало 21 раз. Нужна автоматика.
NOTICE
fi
exit 0
