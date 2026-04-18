# QA Enforcement — НИКОГДА не говорить "готово" без прогона

> **КОРНЕВАЯ ПРОБЛЕМА:** Claude в прошлом 3 раза подряд говорил "всё готово" после самооценки,
> а на самом деле тесты не прогонялись. Антон замечал → недоверие → переделка.
>
> **ЭТО ПРАВИЛО ДЕЙСТВУЕТ С 2026-04-18 — жёстко, без исключений.**

## Правило

Перед ЛЮБЫМ из следующих утверждений — **ОБЯЗАТЕЛЬНО** прогнать `qa-full.sh` соответствующего проекта:
- "фича готова"
- "всё работает"
- "можно закрывать сессию"
- "готов(о) к деплою"
- "production-ready"

**Если `qa-full.sh` возвращает FAIL → запрещено использовать выше фразы.**
Вместо них — честно: "PASS X/N, FAIL Y: <список что сломано>".

## Где лежит qa-full.sh

| Проект | Путь | Что проверяет |
|--------|------|---------------|
| artvision-tg-bot | `vps-bot/scripts/qa-full.sh` | Syntax + unit + static security + VPS deploy + E2E smoke |
| artvision-data | `scripts/qa-full.sh` | Shell syntax hooks + knowledge/ 7 domains + wiki hooks enabled + ai-evolve pipeline + memory lint + decisions/ + git state (85 checks) |
| devops-agent | (TODO) | — |

## Hook автоматики

`~/.claude/hooks/pre-push-qa-check.sh` — блокирует `git push` если qa-full.sh существует и FAIL.

Включается через settings.json:
```json
"hooks": {
  "PreToolUse": [
    {"matcher": "Bash", "hooks": [{"type": "command", "command": "~/.claude/hooks/pre-push-qa-check.sh"}]}
  ]
}
```

## Антипаттерны

| ❌ Делать | ✅ Делать вместо |
|-----------|------------------|
| "Smoke test прошёл — готово" | Прогнать `qa-full.sh` → PASS → тогда "готово" |
| "Код чистый, синтаксис OK — готово" | Unit + integration + E2E тоже нужны |
| "Security-агент прошёл по коду — готово" | PoC эксплойтов в реальной среде + `qa-full.sh` |
| "На локалке работает — в прод" | VPS deploy check в qa-full.sh должен пройти |

## История инцидентов этого правила

- **2026-04-18 (1):** "Smoke v1 прошёл — готово" → security агент нашёл 2 CRIT блокера (prompt injection RCE + no admin check)
- **2026-04-18 (2):** "Security блокеры закрыты — готово" → Антон спросил про тесты → 10% стресса, нет E2E, нет integration
- **2026-04-18 (3):** "Всё в git — готов" → Антон третий раз замечает что QA неполный
- **2026-04-19 (4):** Интеграция Wiki Карпатова + post-commit-learning → "factcheck 10/10 зелёный, всё работает". Антон спросил "должна ли система тестирования применяться здесь?" → признался что прогнал только факт-чек наличия файлов, не прогнал QA как системы. После создания `artvision-data/scripts/qa-full.sh` (PASS 85/85) **smoke-тест реального коммита поймал fork failure** — post-commit-learning.sh падает с `fork: Resource temporarily unavailable`, сигнал теряется silently (|| true в git hook). То есть декларативно подключено, фактически НЕ работает при нагрузке.

## Ответственность

Если правило нарушено — записать в `self-corrections.md` и добавить проверку в qa-full.sh чтобы в следующий раз поймать автоматически.
