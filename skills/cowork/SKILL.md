---
name: cowork
description: Cowork-style делегирование задач — опиши результат, уйди, вернись к готовому. Обёртка над /combine с фоновым запуском и TG-нотификацией по готовности. Аналог Anthropic Cowork. Триггеры — 'cowork', 'делегируй', 'опиши результат и уйди', 'фоновый комбайн', 'комбайн в фоне', 'запусти и уведоми', 'cowork <описание>'.
user-invocable: true
---

# /cowork — описал результат и ушёл

Аналог Anthropic Cowork в нашем workflow. Один прыжок: описание готового результата → запуск в фоне → TG-нотификация Антону когда готово. Антон может закрыть ноут, уйти на встречу или спать — комбайн доделает.

## Когда использовать

- Задача занимает 10+ минут и понятен «готовый результат»
- Готов закрыть ноут / уйти на встречу / на ночь
- Не нужны промежуточные approvals (или они на CONFIRM-уровне, тогда комбайн остановится сам)

## Когда НЕ использовать

- Нужна интерактивность / промежуточные решения
- Задача < 5 мин — overhead запуска не окупится, делай вручную
- Задача с нечётким результатом («сделай что-то с сайтом») — сначала `/goal` для проработки acceptance
- 2+ cowork параллельно в одной TODO — конфликты по git, ставь последовательно

## Алгоритм

### Шаг 1. Acceptance criteria (1 вопрос максимум)

Из `<описание результата>` извлечь:
- WHO — для кого (клиент / продукт / внутреннее)
- WHAT — что на выходе (файл / URL / коммит / Asana closed / отчёт)
- WHEN — дедлайн (если в описании нет — спросить **один раз**, иначе оставить без `due`)

Если в описании все 3 поля — пропустить вопрос, идти на Шаг 2.

### Шаг 2. Записать ready-задачу в нужный TODO

Определить TODO по контексту (`~/.claude/rules/todo-routing.md`):

| Тема | TODO |
|------|------|
| Клиент / КП / presale | `artvision-data/presale/TODO.md` |
| Бот / Telegram | `artvision-tg-bot/TODO.md` |
| VPS / деплой / мониторинг | `devops-agent/TODO.md` |
| Продукт / MVP | `artvision-data/products/TODO.md` |
| Ops / отчёты | `artvision-data/TODO.md` |

Формат строки (ready-чеклист из `session.md`):

```
- [ ] <описание> [client:X] [result:Y] [priority:high] [assignee:claude] [skill:auto] [due:YYYY-MM-DD]
```

### Шаг 3. Запуск /combine в background

```
Agent(
  subagent_type: "general-purpose",
  run_in_background: true,
  description: "cowork: <короткое имя>",
  prompt: """
  Запусти /combine для задачи: <task description>.

  Контекст: <client + result + ссылки на нужные файлы>.

  По завершении (PASS, PARTIAL или FAIL) — отправь итог Антону:

    ~/.claude/scripts/tg-send.sh anton "<URL артефакта>
    cowork done: <task>
    Status: ✅/⚠️/❌
    Что сделано: <bullets>
    Что не сделано: <bullets>
    Артефакты: <git commit hash, deploy URL, файлы>"

  Соблюдай все правила: factcheck перед scp, no AI/нейросети в публичных материалах,
  kp-brand для КП, qcomment guard, topvisor EQUALS [PID].

  Если упрёшься в CONFIRM-уровень (клиент, деньги, деструктив) — НЕ выполняй,
  пришли TG с запросом approval и пометь задачу `blocked-by:anton-confirm`.
  """
)
```

### Шаг 4. Подтверждение пользователю

```
🚀 Cowork запущен
   Задача: <task>
   TODO: <путь>
   Background agent: <id>
   TG-нотификация: @avportal_bot когда готово
   Дедлайн: <due> (если есть)

   Можешь закрыть терминал.
```

### Шаг 5. Recap-метка

В `sync/recaps/<session-id>.md` дописать в «Лог выполнения»:

```
- [HH:MM] /cowork: <task_id> → background, TG по готовности
```

## Примеры (10-словные промпты)

Идея: чем лучше file-system контекста — тем короче промпт. См. `~/.claude/rules/context-environment.md` (внедрение).

### Пример 1. КП клиенту (4 слова)

```
/cowork КП spadent v5
```

→ читает `clients/spadent/config.yaml` (палитра, дизайн-профиль, реквизиты)
→ читает `clients/spadent/presale/kp/spadent_kp_v4.html` (предыдущая версия)
→ читает `~/.claude/rules/{feedback_kp_layout_and_design.md, audit-kp-pipeline.md, kp-brand.md}`
→ запускает `/presale-kp` с config
→ deploy + factcheck + TG

### Пример 2. SEO-аудит (5 слов)

```
/cowork SEO audit site.com
```

→ читает `clients/<slug>/config.yaml` (регион, тип бизнеса, конкуренты)
→ запускает `audit-kp-pipeline` (18 шагов)
→ отчёт в `clients/<slug>/seo/<date>/audit.html`
→ TG

### Пример 3. Bug fix (7 слов)

```
/cowork tvorims voice handler crash >30s
```

→ читает `artvision-tg-bot/CLAUDE.md` (архитектура, secrets)
→ git log по voice handler
→ debug → fix → deploy → smoke test → TG

### Пример 4. Контент (6 слов)

```
/cowork SEO статья tvorimsovershenstvo брекеты
```

→ читает `clients/tvorimsovershenstvo/{config.yaml, brand-voice.md}`
→ `/content-writer` + `/tfidf-clustering`
→ publish через wp-rest-api → TG со ссылкой на live

## Ограничения

| Лимит | Поведение |
|------|----------|
| **CONFIRM-уровень** (клиент / деньги / деструктив) | Комбайн остановится на confirm-точке, пришлёт TG с запросом approval. Не выполнит сам. |
| **Rate-limit API** (Topvisor, OpenAI, SEMrush) | Задача помечается `blocked-by:rate-limit`, TG с предложением подождать или продолжить из чекпойнта. |
| **Параллельные cowork** | НЕ запускать 2+ одновременно с пересечением по файлам/git. Очередь. |
| **VPS лежит** | Background agent зависнет на scp. TG не дойдёт. Перед запуском — проверить `curl -sI https://artvision.pro/`. |
| **Время** | Background agent живёт пока Claude Code session активна. Если закрыть терминал — может прерваться. Для долгих задач (>2ч) использовать `/schedule` (cron) вместо `/cowork`. |

## Связь с другими механизмами

| Skill | Когда вместо /cowork |
|-------|---------------------|
| `/combine` | Если ты сидишь у терминала и видишь выполнение. /cowork = combine + background + TG. |
| `/goal` | Если результат нечёткий — сначала `/goal` для проработки acceptance, потом `/cowork`. |
| `/schedule` | Если задача повторяющаяся (cron). /cowork = одноразовая. |
| `/loop` | Если нужно polling до условия. /cowork = выполнить и доложить. |
| `/swarm` | Если 3+ независимых параллельных задач. /cowork = последовательная очередь. |

## Антипаттерны

- ❌ Cowork на нечётком результате («сделай что-то с сайтом») → комбайн не поймёт acceptance. Сначала `/goal`.
- ❌ Cowork на простую правку (опечатка, цена) → быстрее вручную.
- ❌ Cowork 2+ параллельно с пересечением файлов → git конфликты, оба упадут.
- ❌ Cowork без `[result:]` тега → комбайн не знает когда задача закрыта.
- ❌ Cowork на CONFIRM-задачи (платёж, рассылка клиенту) → остановится на approval-точке, время теряется. Сделай вручную с подтверждением.

## Связано: Context Environment

`/cowork` работает тем лучше, чем плотнее file-system контекста (Anthropic Cowork паттерн): «один день на построение context environment → промпт из 10 слов даёт результат клиенту».

См. внедрение: `~/.claude/rules/context-environment.md` (TBD — Этап 1 аудит).

## Прецедент

Установлено 2026-05-12 после вопроса Антона про аналог Anthropic Cowork. Cowork = их фишка delegate-and-leave. У нас собрано из 5 кусков (skills + TODO + Asana + git + TG-bot). Этот skill — один прыжок без выбора меню перекрёстка.
