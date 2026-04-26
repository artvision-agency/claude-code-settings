# Handover: Init сессии + AI Evolve W17

**Дата:** 2026-04-26 03:45
**Контекст:** ops
**Сессия:** ae559394-b898-4116-ae1d-5cf65c3e7cf9
**Статус:** завершено

## 🎯 Цель сессии
Init сессии (handovers, asana, recap, memory) + /ai-evolve weekly.

## ✅ Что сделано
- 5 pending handovers разгребли (2 rm trivial, 3 HANDOVER.md написаны)
- Asana sync FAIL ×23 — self-healed ночью, run 408 OK
- /ai-evolve W17: 30 patches → 7 improvements applied → commit `605f8b70` (~/.claude) + sync `a12baebd3` (artvision-data)
- Новый хук `pre-strip-script-guard.sh` (тесты 4/4 PASS, bypass `STRIP_FORCE=1`)
- Recap goal заполнен в sync/recaps/ae559394...md

## 🧠 Решения и ПОЧЕМУ
| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| 7/7 evolve улучшений (вариант "a") | b/c/d/e | Все предложения traceable к patches, прецедент Антоном проверен |
| `pre-client-work.sh` НЕ регистрировать на Bash | расширить логику хука | Хук читает TOOL_INPUT_FILE_PATH (Edit/Write), для Bash не применим — бесполезно |
| Коммит mixed (мой evolve + pre-existing reorg) | расщеплять | quality.md был new file (реструктуризация прошлых сессий), отдельный коммит создал бы путаницу |

## ⚠️ Открытые вопросы
- Memory lint: 1 critical (orphan `feedback_no_internal_markers_in_client_docs.md` не в MEMORY.md) — не закрыто
- cc-name сессии — Антон делает в терминале (не закрыто, текущая сессия ae559394 без имени)

## ➡️ Следующий шаг
🔥 **CAMEO топ-3** (Актеон/GC/Рокада) — DentalExpo, дедлайн пн 27.04 (37ч). Вызвать `/clear` → новая сессия → читать `clients/dentalexpo/`.

## Очередь после CAMEO (high)
- Дентикс/Aleksandra rev1 — wait Anton
- UNOtrans/Денис Зыков пн — wait Anton
- BluMart/Юра Хаит — wait Anton
- Визитка + письмо Наталье (просрочена 21.04) — wait Anton

## ❌ Что НЕ сделано
- Memory lint critical: `feedback_no_internal_markers_in_client_docs.md` orphan (не в MEMORY.md) — оставлено на следующую итерацию
- cc-name текущей сессии — Антон делает в терминале вручную (не у Claude в полномочиях)
- AI-Evolve Memory section не обработана (148 файлов, 24 warn) — отдельная задача

## 📚 Уроки
- pre-client-work.sh имеет matcher Edit/Write, но логика читает `TOOL_INPUT_FILE_PATH` — для Bash matcher бесполезно. → если хочешь блочить bash-команды на clients/* — пиши отдельный hook с парсингом `CLAUDE_BASH_COMMAND`
- ai-evolve W17 показал: 30 patches, top boilerplate = ant-partners (10 incidents). Их паттерны теперь enforced хуком `pre-strip-script-guard.sh`
- Asana sync FAIL ×23 (25.04) — self-healed без вмешательства; tg-send.sh передавал ломаный heredoc. Если повторится — починить параметризацию команд в `~/.claude/scripts/tg-send.sh`

## 🗺️ Карта файлов (что трогали)
```
~/.claude/
├── rules/quality.md          ← +Pre-Task gate, +🎨 Замена шаблона CMS
├── rules/antipatterns.md     ← +DOM не grep, +strip без --dry-run, +чужой бренд
├── rules/core.md             ← +strip-скрипты ужесточение
├── rules/self-corrections.md ← +инцидент #10, +2 хука в таблицу
├── hooks/pre-strip-script-guard.sh   ← НОВЫЙ
├── settings.json             ← +pre-strip-script-guard на Bash
├── ai-evolve-suggestions/2026-W17.md ← отчёт
└── handovers/                ← +3 за сессию
artvision-data/
├── sync/recaps/ae559394-...md  ← цель заполнена
└── context/decisions/        ← evolve W17 logged
```

## ⚠️ Гачи (gotchas)
- `pre-strip-script-guard.sh` теперь активен — если запустишь strip/clean/fix_*.py в clients/* без `--dry-run` → exit 1. Bypass: `STRIP_FORCE=1 python3 ...`
- `~/.claude/` git repo имеет накопленные D-удаления (.archive-20260423, прежняя реструктуризация) — НЕ коммитить их в общий push, разбираться отдельно
- Asana sync — после FAIL streak счётчик `/tmp/asana-sync.fails` нужно очищать ручно если хук не сделал; healthcheck `~/.claude/...asana-sync-health.sh`

## 🔗 Связанные ресурсы
- Commit: `605f8b70` (~/.claude) — evolve W17 push
- Commit: `a12baebd3` (artvision-data feat/ops-crm-v1) — memory+rules sync
- Прошлые handovers сегодня: `HANDOVER-2026-04-26-0235-ops-products-matrix-scout.md`, `HANDOVER-2026-04-26-0258-ops-session-crash-diag.md`, `HANDOVER-2026-04-26-0220-handover-pending.md`
- Evolve report: `~/.claude/ai-evolve-suggestions/2026-W17.md`
- Recap: `artvision-data/sync/recaps/ae559394-b898-4116-ae1d-5cf65c3e7cf9.md`
