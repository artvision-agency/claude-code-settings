---
session_id: 085c1e88
context: infra
date: 2026-04-25 20:08
status: завершено
commit: 387b7769
---

# Handover: защитные PreToolUse хуки против деструктивных операций

**Дата:** 2026-04-25 20:08
**Контекст:** infra (рабочая дир `~`, но трогали `~/.claude/`)
**Сессия:** 085c1e88 (Сессия без имени → infra по сути работы)
**Статус:** ✅ завершено, запушено (commit 387b7769)

## 🎯 Цель сессии

Антон спросил: «много ли скриптов сломалось при Bypass Permissions за месяц, и предотвратил бы это Auto mode?». Ответ привёл к корневой причине (моя память не работает в моменте) → построить детерминистичные хуки против 3 конкретных инцидентов.

## ✅ Что сделано

- `~/.claude/hooks/pre-vps-git-guard.sh` — новый. Блокирует `ssh + git rebase|reset --hard|push -f|clean -f|checkout -- .|pull без --ff-only`. Bypass: `VPS_GIT_FORCE=1`.
- `~/.claude/hooks/pre-tmp-write-guard.sh` — новый. Блокирует Write/Edit `*.py|.sh|.js|.ts|.rb|.go|.rs|.php|.java|.kt|.swift|.c|.cpp|.h` в `/tmp/*`, `/var/tmp/*`, `/private/tmp/*`. Bypass: `TMP_WRITE_FORCE=1`.
- `~/.claude/hooks/pre-cleanup-tokens-check.sh` — новый. Блокирует `rm -r*` на cache-директориях если внутри есть файлы с `token|credential|secret|*.pem|*.key|oauth`. Bypass: `CLEANUP_FORCE=1`.
- `~/.claude/hooks/prompt-taskcreate-nag.sh` — `chmod +x` + регистрация в `settings.json` UserPromptSubmit (был мёртвый — числился развёрнутым в правиле, но не работал).
- `~/.claude/rules/self-corrections.md` — мета-правило «инцидент → хук, не запомню» + таблица из 7 активных хуков-страховок.
- `~/.claude/settings.json` — забэкаплено в `.bak_20260425_195118` перед правкой.

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| Хуки, а НЕ Auto mode | переключить permissions с Bypass на Auto | Auto mode = моё же суждение, формализованное. В тех 3 инцидентах я в моменте операции опасной не считал — иначе бы не делал. Auto не помог бы. Хуки = детерминистичная проверка по regex, не зависит от внимания. |
| Exit 1 (блок) + bypass env | `additionalContext` warning без блока | Прецеденты дорогие (потеря коммита, потеря OAuth, 30 мин работы). Лучше раздражать чем терять. Bypass через env даёт явный escape для исключений. |
| Регистрация в settings.json через python script | Edit вручную | Гарантирует JSON-валидность + проверку дубликатов + бэкап. Settings.json — критичный файл, ручная правка опасна. |
| Не блокировать `.txt|.json|.log` в /tmp | блокировать любой Write в /tmp | False-positives на легитимные temp fixtures. Скриптовые файлы (.py/.sh) — намеренный сигнал «это работа, не выкинуть». |
| Не коммитить чужие изменения в `~/.claude` | `git add -A` | В рабочем дереве 20+ файлов от другой сессии Антона (удаления rules/*.md, M CLAUDE.md). `git add` точечно по моим 6 файлам. |

## ❌ Что НЕ сделано

- **Хуки не протестированы вживую** — тесты прогнаны на синтетических командах. Реальная проверка будет когда я случайно попробую `ssh ... git pull --rebase` или `Write /tmp/xxx.py`. Тогда станет ясно работает ли.
- **Слой 2 для TaskCreate** (PreToolUse-блок всех tools кроме TaskCreate при pending>0) — не сделан. Слой 1 (`prompt-taskcreate-nag.sh`) теперь работает, этого должно хватить. Если повторится пропуск — делать Слой 2.
- **2 reminder инцидента** (#3 TaskCreate-логический пропуск, #5 cleanup-без-backup) — частично покрыты, но не на 100% (Auto mode тут не помог бы, хуки покрывают только частный случай).

## 📚 Уроки

- **Правило в md ≠ срабатывание правила.** Доказано трижды (#8 QA, #9 TaskCreate, 23.04 git rebase) — все три имели правило, я его не вспомнил в моменте. Перевод в хук = единственный способ защиты.
- **«Хук развёрнут» нужно проверять.** `prompt-taskcreate-nag.sh` числился активированным с 19.04, но не имел `chmod +x` и не был в settings.json. Self-corrections.md ввёл меня в заблуждение. Сделана таблица «активных защитных хуков» — обновлять при каждом добавлении.
- **Bypass-env обязателен.** Жёсткий блок без escape = я попаду в тупик при легитимной операции. `VPS_GIT_FORCE=1` / `TMP_WRITE_FORCE=1` / `CLEANUP_FORCE=1` / `QA_SKIP=1` / `CLEANUP_FORCE=1` — единый паттерн.
- **Auto mode vs хуки — концептуально разные слои.** Auto mode на 5 инцидентов перехватил бы 2/5 (40%). Хуки покрывают 3/5 на 100% по конкретному паттерну. Третий путь — добавить хуки и оставить Bypass Permissions.
- → сохранить как `feedback_rules_need_hooks.md` в memory.

## 🔜 Следующие шаги

1. **HIGH (due пн 2026-04-27):** Дентал-Салон — пакет CAMEO топ-3 (Актеон/GC/Рокада) для Антона на LinkedIn/email/TG. См. предыдущие handover-ы `HANDOVER-2026-04-24-*-ops.md` (есть готовые материалы по DentalExpo).
2. **HIGH:** UNOtrans — Антону связаться с Денисом Зыковым в пн (КП v04 у клиента с 15.04, ответа нет).
3. **HIGH:** BluMart — ждём Юру Хаита (assignee:anton, due 25.04 = сегодня).
4. **MEDIUM:** Asana «10 заказов» — ждёт от Антона assignee/due/project/контекст.
5. **MEDIUM:** Puratos — верификация UNCONFIRMED чисел.
6. **LOW:** 29 pending HANDOVER-маркеров в `~/.claude/handovers/.pending/` — разгрести (можно отдать агенту в фоне).
7. **LOW:** через 7 дней — собрать статистику что блокировали новые хуки. Если 0 срабатываний — значит работают (нет инцидентов). Если >0 — посмотреть false positives.

## 🗺️ Карта файлов

```
~/.claude/
├── hooks/
│   ├── pre-vps-git-guard.sh          ← НОВЫЙ (95 строк)
│   ├── pre-tmp-write-guard.sh        ← НОВЫЙ (40 строк)
│   ├── pre-cleanup-tokens-check.sh   ← НОВЫЙ (85 строк)
│   ├── prompt-taskcreate-nag.sh      ← chmod +x, был мёртвый
│   └── pre-push-qa-check.sh          ← (уже работал) для понимания паттерна
├── rules/
│   └── self-corrections.md           ← +мета-правило +таблица 7 хуков
├── settings.json                     ← +4 регистрации
└── settings.json.bak_20260425_195118 ← backup перед правками
```

## ⚠️ Гачи

- **Если хук блокирует и я не могу понять почему** → читать stderr (там подробное сообщение + bypass instruction).
- **Если в `~/.claude` куча uncommitted changes** — это другая сессия Антона. НЕ делать `git add -A`. Только точечно по своим файлам.
- **Settings.json правится через python3** (не Edit вручную) — гарантирует JSON-валидность.
- **prompt-taskcreate-nag.sh self-disable** работает: после первого TaskCreate в сессии или после 10 turns. Лог пока не пишет (лога нет в `~/.claude/logs/`) — добавить если понадобится debug.

## 🔗 Связанные

- Commit: `387b7769` в `~/.claude` (запушено в `artvision-agency/claude-code-settings`)
- Аналитика инцидентов от Explore-агента (в транскрипте сессии 085c1e88)
- Правила: `~/.claude/rules/self-corrections.md` — добавлена секция «МЕТА-ПРАВИЛО + Активные защитные хуки»
- Bulletproof: `~/.claude/rules/bulletproof-patterns.md` (40% rule сработал на 54%, я сделал handover)
- Предыдущие handover: `HANDOVER-2026-04-25-1925-context-bloat-investigation.md`

## 📊 TaskList на момент закрытия

Из 18 созданных в этой сессии:
- ✅ #1-6: защитные хуки (закрыто)
- ⏸ #7-18: клиентские/гигиена сессии — переходят в следующую
