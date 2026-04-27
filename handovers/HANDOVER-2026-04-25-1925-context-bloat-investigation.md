---
session_id: 72ff7cda
date: 2026-04-25 19:25
context: ops
status: в работе — план составлен, реализация в новой сессии
---

# Handover: Расследование раздутия контекста + план чистки MCP/хуков

## 🎯 Цель сессии (одна строка)

Найти ПОЧЕМУ контекст с ~10 дней назад резко стал съедаться (50% уже на старте, 89% на 6 промптах) и составить план чистки.

## ✅ Что сделано

- **Анализ SessionStart-инжекций** — посчитал что подкачивается до первого промпта (~25-35K токенов vs ~5-10K раньше = прирост 3-4×).
- **Виновники найдены** (см. таблицу ниже).
- **Аудит MCP-серверов и плагинов** через `~/.claude.json` + `~/.claude/settings.json` + видимые в текущей сессии connectors.
- **Антон одобрил план чистки** → следующая сессия = реализация.

## 🧠 Главное знание для следующей сессии

### Что инжектируется (топ источников токенов на старт)

| Источник | Токены/start | Когда добавлено | Действие |
|----------|--------------|-----------------|----------|
| Skills listing (~200 скиллов с full description) | ~5-8K | росло органически | lazy-load по триггеру |
| **PENDING HANDOVERS hook** (29 сессий с full детализацией) | ~3-5K | ~22-23.04 | урезать до count + path |
| **"Восстановление сессии"** (25 задач + TG отправки) | ~3-5K | ~20-22.04 | top-3 + ссылка на TODO.md |
| **MCP servers** (claude.ai web connectors + локальные) | ~5-8K | накопительно | отключить лишнее |
| **AUTOMATIC TASKCREATE hook** (10 задач full) | ~2-3K | 18-19.04 | seen-cache не работает, инжектит каждый resume |
| **superpowers:using-superpowers** (full skill text каждый старт) | ~1500 | плагин | оставить |
| Правила в CLAUDE.md (core+session+quality+security+...) | ~5-7K | расширилось 18-24.04 | load on-demand по cwd/триггеру |

### MCP-аудит (что подключено, что не используется)

**Локальные `~/.claude.json` mcpServers** (4):
- `asana` — ✅ оставить
- `pencil` — ❓ редко (отключить если не работаешь с .pen)
- `hex-ssh` — ❓ (отключить)
- `voicemode` — ❓ (отключить)

**Плагины Claude Code** (`~/.claude/settings.json` → `enabledPlugins`):
- `superpowers@superpowers-dev` — ✅ оставить
- `conductor@conductor-marketplace` — ❌ почти не используется → отключить
- `pyright-lsp@claude-plugins-official` — ❌ для ops-сессии не нужен
- `telegram@claude-plugins-official` — ❌ уже сам отвалился
- `frontend-design@claude-plugins-official` — оставить
- `codex@openai-codex` — оставить (rescue)

**claude.ai web connectors** (видны автоматически в каждой сессии — отключаются ТОЛЬКО через UI claude.ai → Settings → Connectors):
- `claude_ai_Asana` — **ДУБЛЬ** локального asana, отключить
- `claude_ai_Hugging_Face` — НЕТ → отключить (большой instruction блок!)
- `claude_ai_PubMed` — НЕТ (медицина) → отключить
- `healthcare-mcp` — НЕТ → отключить
- `medical-mcp` — НЕТ → отключить
- `claude_ai_Gmail`, `GoogleCalendar`, `GoogleDrive`, `GitHub_MCP` — оставить (редко но нужны)
- `llm-consilium` — оставить

## 🔜 Следующие шаги (приоритет HIGH → LOW)

### HIGH (быстрые wins)

1. **Антон руками в claude.ai → Settings → Connectors:**
   - Disconnect: Hugging Face, PubMed, healthcare-mcp, medical-mcp, дубль Asana
   - **Ожидаемая экономия:** −3-5K токенов/start

2. **Claude правит `~/.claude.json`** — удалить из `mcpServers`:
   - `pencil` (если Антон подтвердит что не нужен)
   - `hex-ssh`
   - `voicemode`
   - **Ожидаемая экономия:** −1K

3. **Claude правит `~/.claude/settings.json` → `enabledPlugins`**:
   ```json
   "conductor@conductor-marketplace": false,
   "pyright-lsp@claude-plugins-official": false,
   "telegram@claude-plugins-official": false
   ```
   - **Ожидаемая экономия:** −1-2K

### MEDIUM (хирургия хуков)

4. **Урезать PENDING HANDOVERS hook** — найти `~/.claude/hooks/*pending-handover*` (или похожий), показывать только count:
   ```
   ⚠️ 29 pending handovers — см. ~/.claude/handovers/.pending/
   ```
   вместо дампа 29 записей. Экономия ~3-5K.

5. **Урезать "Восстановление сессии" hook** — top-3 high задачи + ссылка на TODO.md, не дампить 25.

6. **Починить seen-cache AUTOMATIC TASKCREATE** — `/tmp/taskcreate-seen-ops.txt` существует, но всё равно инжектит. Проверить логику.

### LOW (рефакторинг правил)

7. **Skills lazy-load** — listing в SessionStart показывать только триггерные/часто используемые, остальные на запрос.

8. **CLAUDE.md правила load on-demand** — сейчас core+session+quality+security+git+antipatterns+... грузятся всегда. Сделать routing по cwd/контексту (ops vs bot vs infra).

## ❌ Что НЕ сделано

- Не отключил MCP — нужны действия Антона в UI claude.ai (web connectors) + подтверждение по pencil/voicemode/hex-ssh
- Не правил хуки — контекст был 89%, нужна свежая сессия

## ⚠️ Гачи

- **Контекст забивался катастрофически быстро** в этой сессии (89% на 6-7 промптах). После чистки нужно мерить заново — реальная экономия может отличаться от оценок.
- **Дисковое место и GitHub НИ ПРИ ЧЁМ** — Антон спрашивал. Контекст = токены в RAM, файлы только если хуки их инжектируют.
- **Антон попросил "доказывай ссылками/показывай"** — feedback на все цифры давать с командой воспроизведения (пример: `curl -sI URL → 200`), а не голые утверждения.
- **Антон 2 раза написал "не понял"** про задачу ANT — я тупил и задавал вопросы вместо проверки страницы. Запомнить: сначала **сам посмотреть код/страницу**, потом спрашивать.

## 🔗 Связанные задачи (висят в TODO ops, должны быть подняты)

- ANT Partners правки nashi-uslugi (NOT READY — ждёт решения Антона из 3 вариантов: убрать карточки / создать страницы / обернуть в `<a>` с риском 404)
- Asana sync падает 23x подряд — горящее
- Дентикс/Aleksandra rev1 — ждём ответа сегодня
- BluMart — ждём Юру Хаита
- Дентал-Салон CAMEO топ-3 к понедельнику

## 📂 Файлы для правки в новой сессии

```
~/.claude.json                          ← удалить ненужные mcpServers
~/.claude/settings.json                 ← enabledPlugins false для лишних
~/.claude/hooks/                        ← найти pending-handover hook, урезать
~/.claude/hooks/                        ← найти session-restore hook, урезать top-3
/tmp/taskcreate-seen-ops.txt            ← проверить почему не работает
```

## 🎬 Команда старта новой сессии

```
В новой сессии скажи: "продолжаем чистку MCP, читай HANDOVER-2026-04-25-1925-context-bloat-investigation.md"

Антон сначала сам отключит web connectors в claude.ai (5 штук), скажет "готово",
потом Claude правит локальные файлы и хуки.
```
