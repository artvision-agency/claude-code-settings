#!/usr/bin/env bash
# hook-interaction-lint.sh — статический анализатор взаимодействия PreToolUse-хуков.
#
# ЦЕЛЬ (Антон 30.05.2026): строгая проверка ЛОГИКИ контролей, не bypass.
# Ловит класс «дедлок матчерлесс-хуков»: несколько глобальных (matcher="") PreToolUse-хуков,
# каждый exit-2 с требованием РАЗНОГО tool-действия, причём хук НЕ пропускает (whitelist)
# действие-разблокировку другого → взаимная блокировка.
#
# Прецедент: 30.05.2026 skill-required ↔ block-no-taskcreate ↔ recap-goal-check зациклились
# (см. memory/feedback_hook_interaction_lint_needed.md).
#
# Это слой 2 из 5 (см. задачу #2). НЕ ослабляет контроли — только проверяет их связность.
#
# Запуск: bash ~/.claude/hooks/hook-interaction-lint.sh   → отчёт + exit 1 при найденных циклах.
# Расширение: дописать UNBLOCK-таблицу (хук → каким tool снимается его блокировка).

set -uo pipefail
SETTINGS="$HOME/.claude/settings.json"
HOOKS_DIR="$HOME/.claude/hooks"
FAIL=0

[[ ! -f "$SETTINGS" ]] && { echo "no settings.json"; exit 0; }

# Декларативная таблица: глобальный блокирующий хук → tool, которым снимается его блокировка.
# (Действие-разблокировка. Если другой глобальный хук НЕ пропускает этот tool — потенциальный цикл.)
# Формат: hook_basename|unblock_tool|unblock_detail
UNBLOCK_TABLE="
pre-tool-skill-required.sh|Skill|вызвать Skill ИЛИ touch snooze-marker
pre-tool-block-no-taskcreate.sh|TaskCreate|вызвать TaskCreate
pre-tool-recap-goal-check.sh|Edit|Edit recap-файла (заполнить Цель сессии)
"

# 1. Собрать глобальные (matcher пустой) PreToolUse-хуки, которые могут exit 2.
GLOBAL_HOOKS=()
while IFS= read -r line; do
  [[ -n "$line" ]] && GLOBAL_HOOKS+=("$line")
done < <(python3 - "$SETTINGS" <<'PY'
import json,sys,re
s=json.load(open(sys.argv[1]))
for grp in s.get("hooks",{}).get("PreToolUse",[]):
    if grp.get("matcher","")!="": continue  # только глобальные (на все tools)
    for hk in grp.get("hooks",[]):
        mo=re.search(r"([\w.-]+\.sh)",hk.get("command",""))
        if mo: print(mo.group(1))
PY
)

echo "=== hook-interaction-lint ==="
echo "Глобальных (matcher='') PreToolUse-хуков: ${#GLOBAL_HOOKS[@]}"
printf '  • %s\n' "${GLOBAL_HOOKS[@]}"
echo

# 2. Для каждой пары глобальных блокирующих хуков: пропускает ли хук A unblock-tool хука B?
#    Если хук A exit-2 на любой tool, но НЕ whitelist'ит unblock-tool хука B,
#    то когда B заблокировал и требует свой tool, A заблокирует и его → цикл.
unblock_tool(){ echo "$UNBLOCK_TABLE" | awk -F'|' -v h="$1" '$1==h{print $2}'; }
whitelists_tool(){ # хук_файл, tool → 0 если ПРОПУСКАЕТ (exit 0), 1 если блокирует
  local f="$HOOKS_DIR/$1" t="$2"
  [[ ! -f "$f" ]] && return 1
  # Tool считается пропущенным, если имя встречается как case-токен ('|TOOL|', '|TOOL)', 'TOOL|',
  # 'TOOL)', или с продолжением '\'), И в окне +5 строк есть 'exit 0'.
  # Покрывает: однострочные whitelist, МНОГОСТРОЧНЫЕ case с '\'-переносом, path-scoped exempt
  # (напр. 'Edit|Write)' → следом проверка пути → 'exit 0').
  awk -v t="$t" '
    function hastok(s){ return (s ~ ("[(| \t]" t "[|) \t]") || s ~ ("(^|[(| \t])" t "[\\\\]?$")) }
    {
      if (hastok($0)) win = 10         # нашли токен — открыли окно (case с \-переносом длинный)
      if (win > 0) { if ($0 ~ /exit[[:space:]]+0/) { found=1; exit } win-- }
    }
    END { exit (found?0:1) }
  ' "$f"
}

for A in "${GLOBAL_HOOKS[@]}"; do
  # A анализируем как блокировщик только если он — известный exit-2 хук (есть в UNBLOCK_TABLE).
  # Системные passthrough-хуки (claude-code.sh) не блокируют по своим правилам — пропускаем.
  [[ -z "$(unblock_tool "$A")" ]] && continue
  for B in "${GLOBAL_HOOKS[@]}"; do
    [[ "$A" == "$B" ]] && continue
    UT=$(unblock_tool "$B"); [[ -z "$UT" ]] && continue
    if ! whitelists_tool "$A" "$UT"; then
      echo "⚠️  ЦИКЛ-РИСК: '$A' НЕ пропускает '$UT' (разблокировку '$B')."
      echo "    → Когда '$B' блокирует и требует $UT, '$A' заблокирует это действие. Дедлок."
      echo "    Фикс: добавить '$UT' в whitelist '$A'."
      FAIL=1
    fi
  done
done

# 3. Спец-проверка: блокирующий хук должен пропускать СВОЙ snooze/bypass-механизм.
for H in "${GLOBAL_HOOKS[@]}"; do
  f="$HOOKS_DIR/$H"; [[ ! -f "$f" ]] && continue
  if grep -q "snooze\|skill-required-done\|-done-\|bypass\|FORCE" "$f"; then
    # если хук упоминает свой маркер-снуз — он должен пропускать команду его создания
    marker=$(grep -oE '[a-z-]+-done-' "$f" | head -1)
    if [[ -n "$marker" ]] && ! grep -q "\"command\".*$marker\|\$CMD\" == \*\"$marker\|== \*\"${marker}" "$f"; then
      echo "ℹ️  '$H': упоминает снуз-маркер '${marker}*', проверь что хук пропускает команду его создания (иначе дедлок снуза)."
    fi
  fi
done

echo
if [[ $FAIL -eq 0 ]]; then
  echo "✅ Циклов взаимной блокировки не найдено."
else
  echo "❌ Найдены риски дедлока. См. выше."
fi
exit $FAIL
