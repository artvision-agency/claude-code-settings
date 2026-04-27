# Handover: Init + memory-lint fix → CAMEO prep

**Дата:** 2026-04-27 04:00
**Контекст:** ops
**Сессия:** c65000cb-5c32-4b90-972d-1b6534b9a1b0
**Статус:** завершено (init-часть), следующий шаг: DentalExpo CAMEO топ-3

## 🎯 Цель сессии

Закрыть open items из HANDOVER-2026-04-26-0345 + подготовить почву для DentalExpo CAMEO.

## ✅ Что сделано

- TaskCreate для 7 high-задач из system-reminder / TODO.md
- `~/.claude/projects/-Users-antonk/memory/MEMORY.md` — добавлен orphan `feedback_no_internal_markers_in_client_docs.md` + 7 системных файлов в "Прочее"
- `artvision-data/scripts/memory-lint.py` — catch-all marker recognition, SKIP_NAMES (.archive-*), hypothesis_ префикс → **138 critical → 0** (commit `bd5c89d28`)
- memory-lint exit 0, `pre-memory-lint.sh` хук теперь не блочит git commit

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| Вариант b: обновить lint под политику "fallback grep" | a: --fix-orphans (раздуть MEMORY.md до 300+ строк) | CLAUDE.md грузит первые 200 строк MEMORY.md — раздувать индексом 130+ файлов контрпродуктивно |
| 7 реальных orphans (active-tasks, deliverables и др.) → добавить в Прочее MEMORY.md вручную | Переименовать с нужным префиксом | Переименование изменяет историю поиска, добавление безопаснее |
| SKIP_NAMES включает `.archive-*` | Оставить в orphans | .archive-* системные файлы, не нужны в индексе |

## ❌ Что НЕ сделано

- **3 pending handovers разгрести** (b370f117, 18b982ab, 72ff7cda) — отложено: не блокеры CAMEO, отдельный заход
- **cc-name текущей сессии** — Антон делает в терминале (`cc-name ops`)
- **/ai-evolve W18** — W17 закрыт прошлой сессией; W18 (пн 27.04) ещё не запускали

## 📚 Уроки

- memory-lint: политика "catch-all fallback" эффективнее раздутого индекса — зафиксировать в lint комменте ✅ (уже в коде)

## 🔜 Следующие шаги

1. **🔥 HIGH (СЕГОДНЯ):** DentalExpo CAMEO топ-3 — Актеон / GC / Рокада
   - Путь: `clients/dentalexpo/` → `presale/` или `outreach/`
   - Нужно: 3 HTML-кейса с кастомизацией + intro-текст + контакты LPR
   - Вызвать: `/presale-kp` или `/cons` под клиента перед генерацией
   - Эталон дизайна: `clients/kamey/presale/kp/cameo_kp.html`
   - Старт: прочитать `clients/dentalexpo/context-log.md` + `README.md`

2. **WAIT Anton:** Дентикс/Aleksandra rev1, UNOtrans Денис Зыков
3. **WAIT Anton:** BluMart документ Юры, BluMart партия отзывов
4. **LOW:** 3 pending handovers (b370f117, 18b982ab, 72ff7cda)

## 🗺️ Карта файлов

```
~/.claude/
├── projects/-Users-antonk/memory/MEMORY.md  ← обновлён (+9 строк в Прочее)
└── handovers/                                ← текущий файл

artvision-data/
├── scripts/memory-lint.py                   ← feat: catch-all + skip-list (bd5c89d28)
└── clients/dentalexpo/
    ├── README.md
    ├── context-log.md                        ← ЧИТАТЬ ПЕРВЫМ
    ├── outreach/                             ← CAMEO кладём сюда
    ├── presale/
    └── seo/
```

## ⚠️ Гачи

- DentalExpo CAMEO дедлайн — **пн 27.04 утро** (т.е. СЕЙЧАС, уже пн)
- Pre-Task Protocol: ОБЯЗАТЕЛЬНО прочитать `clients/dentalexpo/CLAUDE.md` (если есть) + `context-log.md` + `patches/` перед первым Edit/Write
- Хук `pre-client-work.sh` блокирует Edit/Write в `clients/dentalexpo/` без маркера `/tmp/claude-client-context-clients-dentalexpo`
- Эталон дизайна: `clients/kamey/presale/kp/cameo_kp.html` — цвета/стиль CAMEO
- Для deploy: scp на VPS `root@80.90.181.152`, путь `/var/www/artvision/`, X-Robots-Tag: noindex для тестовых

## 🔗 Связанные ресурсы

- Прошлый handover: `HANDOVER-2026-04-26-0345-ops-init-and-evolve-W17.md`
- Commit lint: `bd5c89d28` (artvision-data feat/ops-crm-v1)
- Session recap: `artvision-data/sync/recaps/c65000cb-5c32-4b90-972d-1b6534b9a1b0.md`
