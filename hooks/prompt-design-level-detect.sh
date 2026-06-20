#!/usr/bin/env bash
# prompt-design-level-detect.sh — UserPromptSubmit hook (INJECT-ONLY, никогда не блокирует)
#
# Детектит ВИЗУАЛЬНО-ДИЗАЙНЕРСКУЮ задачу и инжектит напоминание:
# дизайн по умолчанию = L1 СТАНДАРТ (frontend-design + дизайн-система клиента),
# уровень меняется СЛОВАМИ L0-L3. Не «голый» frontend-агент.
#
# Rule: ~/.claude/rules/design-complexity-switch.md (+ design-specialist-auto-attach.md)
# Bypass: DESIGN_LEVEL_OFF=1
# Анти-спам: один раз за сессию (/tmp/design-level-done-<session_id>)

set -uo pipefail
[[ "${DESIGN_LEVEL_OFF:-0}" == "1" ]] && exit 0

INPUT=$(cat 2>/dev/null) || exit 0
PROMPT=$(printf '%s' "$INPUT" | jq -r '.prompt // empty' 2>/dev/null) || exit 0
SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null) || true
[[ -z "$PROMPT" ]] && exit 0

# нижний регистр для матча
LP=$(printf '%s' "$PROMPT" | tr '[:upper:]' '[:lower:]')

# триггеры визуально-дизайнерской задачи (рус/eng)
if printf '%s' "$LP" | grep -qiE 'лендинг|ленд |ленд$|посадочн|лэндинг|landing|дизайн|редизайн|design|вёрстк|версток|hero|hero-|баннер|banner|мокап|mockup|макет|страниц[уа] услуг|карточк[ауи] товар|кп |коммерческ.* предложен|дашборд|dashboard|hyperframe|figma|фигма|креатив'; then
  : # match
else
  exit 0
fi

# один раз за сессию
if [[ -n "$SESSION_ID" ]]; then
  FLAG="/tmp/design-level-done-${SESSION_ID}"
  [[ -f "$FLAG" ]] && exit 0
  touch "$FLAG" 2>/dev/null || true
fi

cat <<'MSG'
[DESIGN-LEVEL] Задача похожа на ВИЗУАЛЬНО-ДИЗАЙНЕРСКУЮ. Правило design-complexity-switch.md:
• ПО УМОЛЧАНИЮ = L1 СТАНДАРТ — НЕ «голый» frontend-агент, а: frontend-design + дизайн-система клиента (analyzed-project-design-system) + эталон (template-selection-map) + mobile-first + самопроверка скриншотом.
• Уровень меняется СЛОВАМИ (не слэш):
   L0 черновик («по-быстрому/набросок») · L1 стандарт (default) · L2 сильный («интересный/вау/премиум» → +site-clone реф + bencium + Figma MCP + model-bakeoff + круглый стол) · L3 макс («без ограничений» → +tournament/≥5 вариантов).
• Покажи выбранный уровень в строке [РАЗВЁРТКА: … дизайн: L1/L2 …].
Bypass: DESIGN_LEVEL_OFF=1
MSG
exit 0
