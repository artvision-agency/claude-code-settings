# Research → Memory: каждый внешний факт записывается со свежим источником

> **Принцип:** знания не берутся из training data. Всегда подтверждаются свежим fetch/search, маркируются источником и датой, сохраняются там, где переживут сессию.

## Когда срабатывает

Любой из инструментов возвращает данные, которые станут основой для решений/карточек/документов:

| Инструмент | Триггер |
|---|---|
| `WebFetch` | Любой fetch внешнего URL |
| `WebSearch` | Поисковая выдача |
| `Grep`/`Glob` по чужим исходникам | Только если копируешь паттерн из OSS |
| Jina Reader (`r.jina.ai/`) | Любой ответ |
| MCP-серверы (Asana/Supabase/etc.) | Числа, даты, статусы |

## Обязательный чек-лист ПОСЛЕ получения данных

1. **Свежесть** — запиши `fetched: <ISO datetime>` рядом с данными.
2. **Источник** — полный URL (не главная, а конкретная страница).
3. **Версии продуктов** — если упоминается Claude/GPT/LLaMA/фреймворк — ПРОВЕРЬ текущую версию на дату fetch (WebSearch "latest X model 2026"). Не доверяй имени в training data.
4. **Факт-чек** для чисел/утверждений:
   - `CONFIRMED` — ≥2 независимых источника
   - `UNCONFIRMED` — один источник / только заявление автора
   - `WRONG` — противоречит другим источникам → **не использовать**
5. **Durable?** — если применимо дольше 6 мес и/или влияет на 2+ сценария → в `memory/`.

## Где сохранять

| Тип | Куда | Формат |
|---|---|---|
| Факт из ссылки/поста | `~/.claude/projects/-Users-antonk/memory/trend_<slug>.md` | frontmatter + Факт + Применимость + Проверено |
| Наше применение/вывод | `~/artvision-data/learning/links/YYYY-MM.md` | markdown секция (append) |
| Мета-урок ("паттерн X работает везде") | `~/.claude/rules/lessons.md` | короткая строка + пример |
| Сырой контент (перепроверить) | `link_inbox.raw_content` в Supabase | как есть |

## Шаблон memory-файла (обязательные поля)

```markdown
---
name: trend_claude_code_local_llm
description: Claude Code работает с локальными LLM через ANTHROPIC_BASE_URL — для privacy-sensitive клиентов
type: reference
source: https://instagram.com/p/DXD9TpDF05y/
fetched: 2026-04-17T00:45:00Z
fetched_via: WebFetch | Jina
author: @dailydoseofds_
confirmed_by:
  - https://docs.anthropic.com/claude-code/
  - https://github.com/ggerganov/llama.cpp
---

## Факт
Claude Code поддерживает override через ENV `ANTHROPIC_BASE_URL`.
llama.cpp server даёт OpenAI-совместимый endpoint, поэтому связка рабочая.

## Применимость
- AIvision: privacy-demo для клиентов из регулируемых отраслей
- Risk: нужен A/B качества vs Opus 4.7

## Проверено
2026-04-17, 2 независимых источника (docs.anthropic.com, github.com/ggerganov/llama.cpp)
```

## Запрещено

- Писать факт в `memory/` **без** `source` и `fetched`.
- Использовать цифру/версию из training data без перепроверки через WebSearch.
- Создавать `trend_*.md` для разовой новости хайпа — это `artvision-data/learning/`, не memory.
- Классификация `CONFIRMED` по одному источнику — строго ≥2 независимых.

## Связка с рабочими pipeline

- **Link-processor** (автомат) — обязан проходить этот чек-лист перед UPDATE строки.
- **КП-генерация** — каждое число в КП = строка с источником (cross-reference с `feedback_factcheck_after_parsing.md`).
- **Анализ конкурентов** — каждый факт = URL конкретной страницы.
- **Дашборды клиентов** — данные из Метрики/Директа/Топвизора с меткой `fetched: <datetime>`.

## Самопроверка

Если после работы не появилось ни одной записи в `memory/`/`learning/`/`lessons.md` — спроси себя: **действительно не узнал ничего нового**? Чаще ответ "нет, просто забыл записать".
