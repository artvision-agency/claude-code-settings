# hooks/candidates/ — кандидат-хуки, ждут approve Антона

Хуки здесь НАПИСАНЫ, но НЕ зарегистрированы в settings.json и НЕ активны.
Лежат тут (а не в `hooks/`), чтобы НЕ светиться в orphan-сканере
(`session-start-orphan-hooks.sh` сканирует только `hooks/*.sh` верхнего уровня) —
это не «ложная защита» (self-corrections #18), а осознанный pending-pool.

Перемещены сюда 2026-06-28 (repair settings.json hooks).

## Как активировать (когда Антон одобрит)
1. Тест: 3 кейса блок/warn + 3 пропуск + bypass-env (правило self-corrections #18).
2. `mv candidates/<hook>.sh ../`
3. Зарегистрировать в `~/.claude/settings.json` под нужным событием.
4. Дописать строку в таблицу «Активные защитные хуки» (self-corrections.md).
5. Sync на 3 аккаунта (git).

## Текущие кандидаты

| Хук | Событие | Правило | Bypass |
|-----|---------|---------|--------|
| `post-ppc-set-leak-check.sh` | PostToolUse Write\|Edit | WORKFLOW-SPEC-ppc-semantics ФАЗА 0.5, ppc-launch-playbook | `SET_LEAK_OK=1` |
| `stop-ppc-gov-words-check.sh` | PostToolUse Write\|Edit | ppc-negative-keywords-clinic кат.5 | `GOV_WORDS_OK=1` |
| `prompt-design-level-detect.sh` | UserPromptSubmit (inject-only) | design-complexity-switch.md | `DESIGN_LEVEL_OFF=1` |

Все три — blast-radius 3 аккаунта, регистрировать только с явным approve Антона + тест.
