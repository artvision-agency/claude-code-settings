# Challenge-Self — автоматический скептик против галлюцинаций

## Проблема

Claude в чате регулярно генерит "магические числа" ("30-40%", "обычно", "в среднем") без источников. Антон замечает руками, просит перепроверить. Это занимает его время и создаёт дрейф в решениях.

## Решение (с 2026-04-18)

**Автоматический pipeline:**

1. **Stop-хук** `stop-hallucination-detect.sh` — после КАЖДОГО ответа Claude парсит его на regex-флаги:
   - `magic_percent` — паттерн `\d+[-–]\d+%`
   - `vague_frequency` — "обычно", "как правило", "в среднем", "большинство"
   - `confident_no_source` — "работает так", "это факт", "исследования показывают"
   - `recommendation_pct` — "рекомендую X%" без URL
2. Если найдено — пишет флаг в `/tmp/self-challenge-needed.json`
3. **UserPromptSubmit-хук** `inject-challenge-reminder.sh` — в следующий turn читает флаг (TTL 15 мин) и инжектит `[SELF-CHALLENGE REQUIRED]` в контекст
4. Claude ОБЯЗАН вызвать Skill `challenge-self` до обработки нового запроса
5. Субагент-скептик (роль "Антон") возвращает KEEP / PATCH / REDO

## Исключения (self-challenge НЕ нужен)

- Пользователь уже сам оспорил ответ ("давай поспорим", "ты неправ", "я не верю") → он сделал работу за агента, просто очистить флаг
- Ответ был про код/конфиг/деплой (проверяется тестами)
- Challenge уже вызывался в этом turn
- Ответ краткий (<200 символов) или навигационный

## Файлы

| Компонент | Путь |
|---|---|
| Stop-хук | `~/.claude/hooks/stop-hallucination-detect.sh` |
| UserPromptSubmit-хук | `~/.claude/hooks/inject-challenge-reminder.sh` |
| Skill | `~/.claude/skills/challenge-self/SKILL.md` |
| Флаг-файл (эфемерный) | `/tmp/self-challenge-needed.json` |
| Лог срабатываний | `~/.claude/logs/challenge-self.log` |

## Метрика успеха

- **Kickoff-кейс (BluMart SERM 2026-04-18):** я сказал "30-40% отзывов с брендами на ЯК" без источника → Антон оспорил руками → оказалось 15-20%. Challenge-self должен был поймать это сам.
- **Цель:** <1 случай "магической цифры без источника" на 10 ответов клиенту/по research.

## Связь с другими механизмами

- `strict-factchecker` → пост-деплой HTML (другой домен)
- `crag-research` → если challenge вернул REDO, запустить новый ресерч
- `feedback_no_smoothing.md` → работает в паре (не сглаживать ≠ не галлюцинировать)
- `feedback_no_hallucinations.md` → общее правило, этот pipeline — реализация
