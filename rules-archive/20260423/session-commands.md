# Session Commands — дерево решений

> Когда какую команду использовать. Не угадывать — следовать таблице.

## Главное правило: НИКОГДА `/compact` без `focus`

```
❌ /compact                    → теряет приоритеты, сжимает что попало
✅ /compact focus on {task}   → сохраняет важное по фокусу
✅ /clear                     → лучше чем /compact для смены задачи
```

**Источник правила:** community best practice (MindBranches на x.com), bulletproof-patterns 40% Rule.

## Дерево решений по контексту

| Ситуация | Команда | Почему |
|----------|---------|--------|
| Контекст < 40% | продолжать | Cache warm, нет деградации |
| Контекст 40-50% | `handover` skill → `/compact focus` | Перед "Dumb Zone", сохранить ПОЧЕМУ |
| Контекст 50-80% | СТОП → handover → `/clear` | /compact уже теряет важное |
| Контекст > 80% | handover → `/clear` (не /compact!) | Compact на 80% = катастрофа |
| Сменить тему | `handover` → `/clear` | Чистый контекст быстрее compact |
| Возобновить вчерашнее | `claude --resume` | Полный контекст возвращается |
| Откатиться на 5 шагов | `/rewind` | Точечный откат, не потеря всего |
| Закрыть сессию | `handover` → git push → закрыть | Следующий день поднимешь за 30 сек |

## Различия команд

### `--continue` vs `--resume`
- **`--continue`** — продолжить ПОСЛЕДНЮЮ сессию (любой проект)
- **`--resume`** — выбрать ЛЮБУЮ из истории (показывает список)

### `/clear` vs `/compact focus`
- **`/clear`** — выкинуть весь контекст, начать с нуля. Быстрее, чище.
- **`/compact focus on X`** — сжать оставив фокус на X. Медленнее, но сохраняет.

**Правило:** если задача СМЕНИЛАСЬ → `/clear`. Если ТА ЖЕ задача → `/compact focus`.

### `/rewind` vs `/clear`
- **`/rewind`** — откатить N шагов назад в текущей сессии
- **`/clear`** — обнулить полностью

**Правило:** ошибка в последних 3-5 шагах → `/rewind`. Ушли не туда совсем → `/clear`.

## Workflow длинной сессии (>4 часов)

```
[start] → работа → 40% контекст → handover → /compact focus → работа
                                                            → 80% → handover → /clear → ──┐
                                                                                          │
[next session] ←── claude --resume ←── handover.md ←── git pull ←──────────────────────────┘
```

## Команды для обоих аккаунтов

**Лимит достигнут:**
1. Проверить `/status` → Usage tab (точные цифры от Anthropic)
2. Если 95%+ → переключить аккаунт:
   ```
   claude auth logout
   claude auth login --email adw.artvision.pro@gmail.com
   ```
3. Сессии между аккаунтами не видны — handover в git нужен ОБЯЗАТЕЛЬНО

## Анти-паттерны

| ❌ Делать | ✅ Делать вместо |
|-----------|------------------|
| `/compact` без focus | `/compact focus on {task}` |
| Ждать 80% контекста | Compact на 50%, handover на 40% |
| Закрыть без handover | handover ВСЕГДА перед закрытием |
| Использовать `/compact` для смены задачи | `/clear` + новая сессия |
| Игнорировать recap при resume | Прочитать recap → исправить если устарел |

## Автоматика

- **Хук pre-compact.sh** — напоминает создать handover ПЕРЕД /compact
- **Хук session-start** — показывает recap + меню перекрёстка
- **Хук stop** — записывает в context-log + предлагает handover если контекст >40%

## Связь с другими правилами

- `bulletproof-patterns.md` — 40% Rule (источник правила про /compact на 50%)
- `session-crossroads.md` — меню при старте сессии
- `~/.claude/skills/handover/` — структурированный handover
- `git.md` — sync между аккаунтами через handover в git
