# Agent #3 — Social (VK + Telegram public preview)

**Subagent type:** `general-purpose` (нужен Bash + WebFetch + WebSearch)

## Задача

Собрать сигналы из социальных сетей по каждой организации из `<base>/data/seed-orgs.json`:
- VK группа (официальная + неофициальная)
- Telegram канал/чат (если public)
- Свежий тон 2024-2026 в комментариях
- Топики которые обсуждают (хвалят / ругают)

## Метод

1. Прочитать `<base>/data/seed-orgs.json`
2. Для каждой:
   - `WebSearch`: `<название> <город> VK` → vk.com/<group>
   - WebFetch vk.com часто блокирован → fallback на snippet из WebSearch + поиск упоминаний в открытых группах района (`vk.com/petrogradka_spb` и т.п.)
   - `WebSearch`: `<название> <город> Telegram` → t.me/<channel>
   - `WebFetch t.me/s/<channel>` — public preview (работает без авторизации)
3. Распознать:
   - **Официальный канал** vs **родительский/пациентский чат** (тон разный)
   - **Tone trend 2024-2026** — улучшение / ухудшение / стабильно
   - **Топ-3 темы** в постах и комментариях

## Выход

Записать в `<base>/data/social-research.json`:

```json
{
  "collected": "YYYY-MM-DD",
  "agent": "social-research",
  "note": "WebFetch vk.com часто блокирован — данные через snippets и t.me/s/...",
  "vk": {
    "org_groups": [
      {
        "org_id": "<seed-id>",
        "org_name": "...",
        "vk_url": "https://vk.com/...",
        "open": true,
        "vk_found": true,
        "vk_official": true | false,
        "recent_posts_summary": "<краткое описание>",
        "tone_trend_2024_2026": "<тон + примеры цитат>",
        "topics": ["топик 1", "топик 2"]
      }
    ]
  },
  "telegram": {
    "channels": [
      {
        "org_id": "<seed-id>",
        "tg_url": "https://t.me/...",
        "public_preview_ok": true | false,
        "members_estimate": null,
        "tone_trend": "...",
        "topics": [...]
      }
    ],
    "regional_chats": [
      {"url": "https://t.me/...", "name": "Чат района X", "mentions_of_orgs": [...]}
    ]
  }
}
```

## Антипаттерны

- ❌ Записать «VK не найден» при первом отказе WebFetch → попробовать WebSearch с цитатой группы
- ❌ Смешать тон официальной группы и родительского чата — разный сигнал
- ❌ Игнорировать районные чаты — там часто живой сигнал «куда отдают»
- ❌ Делать вывод о тренде по одному скриншоту/посту — нужен diff 2022-2024 vs 2024-2026
