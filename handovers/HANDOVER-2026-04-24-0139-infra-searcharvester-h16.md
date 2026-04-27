---
session_id: e6aa88e6-2f5b-480a-bf5a-cbf6b7e0ccba
context: infra
date: 2026-04-24
time: "01:39"
status: completed
---

# Handover: Оценка searcharvester (H16) — round_table + pilot-план

**Дата:** 2026-04-24 01:39
**Контекст:** infra (tool-adoption оценка)
**Сессия:** e6aa88e6-2f5b-480a-bf5a-cbf6b7e0ccba
**Статус:** завершено — отложено до триггера

## 🎯 Цель сессии

Оценить нужно ли внедрять searcharvester (self-hosted SearXNG+FastAPI+trafilatura) для замены WebSearch+WebFetch+Jina в research/fact-checking pipeline.

## ✅ Что сделано

- `knowledge/infrastructure/hypotheses.md` — добавлена **H16: searcharvester**, confirmations 0/3, verdict УСЛОВНО
- `TODO.md` → Backlog — добавлена trigger-активируемая задача pilot searcharvester
- TaskCreate #1 — Pilot searcharvester: Docker + 20-link benchmark vs Jina
- Прогнан round_table через llm-consilium (llama + qwen3; kimi-k2 был недоступен 404)
- Commits: `5ae2d81fd` (hypotheses), `eea998044` (TODO) — уже на origin/feat/ops-crm-v1 через auto-sync hook

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему выбрали это |
|---------|--------------|---------------------|
| УСЛОВНО с pilot, не в prod | Внедрить сразу в crag-research | Rule `tool-adoption-proof.md`: нужно 3 confirmations, сейчас 0/3 |
| Отложить до триггера, не делать сейчас | Сделать pilot в этой сессии | Не блокирует revenue-цели (2M→5M), есть работающая связка WebSearch+Jina, DevOps ресурс ограничен |
| Pilot use-case: link-processor, 20 ссылок | Pilot на crag-research или КП-pipeline | link-processor = низкий риск (не клиентский критпуть), есть готовая выборка в link_inbox |
| Критерий 1/3: ≥15% быстрее ИЛИ паритет качества | Только ≥15% быстрее | Паритет качества при self-hosted = уже выигрыш (нет лимитов) |
| Fallback на Tavily платный | Откат на статус-кво | При >20% блокировок Google/Yandex self-hosted теряет смысл, Tavily решает за $30-100/мес |

## ❌ Что НЕ сделано и почему

- Реальный docker-compose на VPS — отложено: нет триггера, ~2ч DevOps-окно нужно
- Замер baseline производительности WebSearch vs Jina до pilot — отложено, сделать вместе с pilot
- Проверка kimi-k2 (404 от groq) — не критично, llama+qwen3 согласованы

## 📚 Уроки

- Round_table с 2 моделями дал MEDIUM confidence — это НЕ блокер, можно принимать решение УСЛОВНО, но без RAMPUP до 3 моделей confidence не станет HIGH
- Tool-adoption-proof работает: за 10 минут получили внешнюю оценку вместо субъективного "о, клёвый инструмент"
- Новая запись в `MEMORY.md` НЕ нужна — H16 в hypotheses.md достаточно для lifecycle

## 🔜 Следующие шаги

1. **LOW (triggered):** При срабатывании триггера (лимиты WebSearch 3+/неделю ИЛИ свободное 2ч DevOps-окно) → запустить pilot по плану в H16
2. **АВТО:** Следующая сессия при старте должна увидеть H16 в hypotheses.md и TODO Backlog — триггер сработает через `[trigger:...]` маркер при соответствующей ситуации
3. Если через 3 месяца 0/3 confirmations останется → удалить гипотезу как «не нужно»

## 🗺️ Карта файлов

```
/Users/antonk/artvision-data/
├── knowledge/infrastructure/hypotheses.md  ← H16 (новая, строки ~250+)
├── TODO.md                                 ← Backlog секция (строка ~321)
└── sync/recaps/e6aa88e6-*.md               ← recap этой сессии

/Users/antonk/.claude/handovers/
└── HANDOVER-2026-04-24-0139-infra-searcharvester-h16.md  ← этот файл
```

## ⚠️ Гачи

- **НЕ внедрять searcharvester без pilot 1/3** — правило tool-adoption-proof
- **НЕ подключать к pipeline КП** даже после 2/3 — критпуть клиентов
- Бенчмарк Jina vs trafilatura делать на **одних и тех же 20 ссылках** (иначе несравнимо)
- При pilot обязательно проверить что SearXNG не блокируется Яндексом — это основной риск для RU-клиентов

## 🔗 Связанные ресурсы

- GitHub: https://github.com/vakovalskii/searcharvester (147★, MIT)
- Источник поста: TG-сообщение от Антона 2026-04-24 01:24
- Правило: `~/.claude/rules/tool-adoption-proof.md`
- Hypothesis tracker: `knowledge/infrastructure/hypotheses.md` (H1-H16)
- Предыдущая аналогичная оценка: H15 (Obsidian, вердикт: НЕ внедрять)
