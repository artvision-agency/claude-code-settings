---
session_id: 085c1e88
date: 2026-04-25 20:25
context: infra
status: частично — защитные хуки + MCP audit + medical reminder завершены; чистка MCP в UI на Антоне
---

# Handover: MCP audit + защитные хуки + medical reminder

## 🎯 Цель

(1) Понять причины раздутия контекста за последний месяц. (2) Построить детерминистичные защиты против 3 деструктивных инцидентов 17–23.04. (3) Дать план отключения неиспользуемых MCP.

## ✅ Что сделано (commit 387b7769 + af6ca705 + текущий)

### Защитные хуки (commit 387b7769, af6ca705)
- `pre-vps-git-guard.sh` — ssh+git rebase/reset/push --force/clean (#1 потеря 9973dc3)
- `pre-tmp-write-guard.sh` — Write/Edit `.py|.sh|.js|...` в `/tmp/*` (#4 gen_dental_reports.py)
- `pre-cleanup-tokens-check.sh` — `rm -rf ~/.cache|~/.npm` если есть токены (#5 YouTube OAuth)
- `prompt-taskcreate-nag.sh` — был мёртвый, активирован (chmod +x + регистрация)
- `self-corrections.md` — мета-правило «инцидент → хук» + таблица 7 активных хуков

### MCP audit (этот же сessии)
Через анализ 353 transcript-файлов выявлена timeline:

| Дата | MCP | Δ | Что подключилось |
|------|----:|---|------------------|
| 26.03 | 2 | base | asana + дубль |
| 02.04 | 11 | **+6** | GitHub_MCP, Gmail, Calendar, **Hugging_Face**, **PubMed**, **healthcare-mcp**, **medical-mcp**, pencil, telegram |
| 13.04 | 16 | **+5** | Figma, Asana_2 (дубль), GitHub_Skills, Vercel, hex-ssh, llm-consilium |
| 17.04 | **21 пик** | **+5** | chrome-devtools, Google_Drive, **Stripe**, **voicemode**, GitHub_Skills_10_01_26 |
| 25.04 | 16 | −5 | telegram отвалился сегодня |

**За последнюю неделю (с 18.04) — нового НЕ подключалось**, только убыль. Жирные скачки были 02.04 и 13–17.04.

### Medical MCP reminder (текущий ещё не закоммичен)
- `prompt-medical-mcp-reminder.sh` — UserPromptSubmit hook. Триггер: keywords `медицин|врач|клиник|пациент|болезн|лечен|лекарств|pubmed|FDA|ICD|symptoms|diagnosis|...`. Инжектит инструкцию включить PubMed + healthcare-mcp + medical-mcp в claude.ai. Self-disable per session (флаг `/tmp/medical-mcp-reminded.<sid>`).
- Зарегистрирован в `~/.claude/settings.json` UserPromptSubmit.
- Тестирован: медицинский → инжект, повторный → молчит, немедицинский → молчит.

### Хирургия хуков (НАЧАТО, не докоммичено)
- `start-handover-pending.sh` — урезан с дампа full content всех 29 маркеров до count + top-5. **Изменения не закоммичены**, бэкап в `start-handover-pending.sh.bak`.

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| Защитные хуки, не Auto mode | переключить permissions | Auto mode = моё суждение. В 3 инцидентах я опасности не видел. Хуки = детерминистично. |
| Disabled, не Delete для MCP | удалить из конфига | Антон попросил. Reconnect/enable одним флагом, токены сохранены. |
| Hook на медицинский контент | чек-лист в правилах | Правило в md = моя память, в моменте не срабатывает. |
| PubMed оставить включённым | disconnect все 3 mediCal | Антон просил. healthcare-mcp + medical-mcp — disconnectable, PubMed — постоянно. |

## ❌ Что НЕ сделано

- **Чистка MCP в UI claude.ai** — на Антоне (только через UI):
  1. Disconnect: `Hugging_Face`, `healthcare-mcp`, `medical-mcp`, `claude_ai_Asana` (дубль)
  2. PubMed — оставить
- **Локальные MCP disable** в `~/.claude.json` — НЕ сделано, ждёт подтверждения по `pencil`, `hex-ssh`, `voicemode` (можно `"disabled": true` без удаления).
- **start-restore-session.sh** — 277 строк дампит ~25 задач + TG логи, **не урезан**.
- **AUTOMATIC TASKCREATE seen-cache** — `/tmp/taskcreate-seen-ops.txt` не работает, инжектит каждый resume — **не починено**.
- **Skills lazy-load** — listing 200+ скиллов в SessionStart — **не сделано**.
- **start-handover-pending.sh урезанный — не закоммичен**, надо проверить и `git add`.

## 🔜 Следующие шаги (для следующей сессии)

### HIGH (быстрые wins по контексту)
1. **Антон руками в claude.ai → Settings → Connectors:**
   - Disconnect: `Hugging_Face`, `healthcare-mcp`, `medical-mcp`, дубль `claude_ai_Asana`
   - Экономия: ~3-5K токенов/start
2. **Claude в `~/.claude.json`** — добавить `"disabled": true` для `pencil`, `hex-ssh`, `voicemode` (после подтверждения)
3. **Закоммитить** `start-handover-pending.sh` (урезан) + новый `prompt-medical-mcp-reminder.sh`
4. **Урезать `start-restore-session.sh`** до top-3 high задач

### MEDIUM
5. Починить seen-cache `start-todo-taskcreate.sh`
6. Skills listing → lazy-load по триггеру
7. CLAUDE.md правила → load on-demand по cwd

### Клиентские (не про контекст)
8. **HIGH due пн:** DentalExpo CAMEO топ-3 (Актеон/GC/Рокада)
9. **HIGH:** UNOtrans / BluMart Юра Хаит / Дентикс Александра

## 🗺️ Файлы

```
~/.claude/hooks/
├── pre-vps-git-guard.sh           ← новый
├── pre-tmp-write-guard.sh         ← новый
├── pre-cleanup-tokens-check.sh    ← новый
├── prompt-medical-mcp-reminder.sh ← новый, зарегистрирован
├── prompt-taskcreate-nag.sh       ← активирован
├── start-handover-pending.sh      ← УРЕЗАН (не закоммичен!)
└── start-handover-pending.sh.bak  ← бэкап оригинала

~/.claude/rules/self-corrections.md ← мета-правило + таблица 7 хуков
~/.claude/settings.json             ← +5 регистраций hooks (бэкап .bak_20260425_195118)

Этот handover: HANDOVER-2026-04-25-2025-infra-mcp-audit-and-hooks.md
Предыдущий:    HANDOVER-2026-04-25-2008-infra-protective-hooks.md
До него:       HANDOVER-2026-04-25-1925-context-bloat-investigation.md (там полный план чистки)
```

## ⚠️ Гачи

- **Контекст 81% уже** — следующая сессия СРАЗУ /clear, читать handover, не /compact.
- **start-handover-pending.sh** — уже урезан, при тестах должен показать только count + top-5 (не дампить 29 записей). Если не работает — `start-handover-pending.sh.bak` рядом, откатить.
- **MCP timeline** — все цифры из jsonl transcript-ов (`grep -hoE 'mcp__[a-zA-Z_-]+__'`), не из git/конфигов.
- **claude.ai web connectors даты** не доступны программно — только UI claude.ai.

## 🎬 Старт следующей сессии

```
1. /clear
2. cat ~/.claude/handovers/HANDOVER-2026-04-25-2025-infra-mcp-audit-and-hooks.md
3. Антон: подтверди по pencil/hex-ssh/voicemode (disable?)
4. Антон: отключил ли connectors в claude.ai? (HF, healthcare, medical, дубль Asana)
5. Если оба да → правлю файлы + коммит, проверяем экономию контекста на следующем старте
6. Параллельно: DentalExpo CAMEO топ-3 (due пн)
```
