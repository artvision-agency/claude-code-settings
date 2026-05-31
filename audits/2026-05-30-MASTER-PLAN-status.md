# MASTER — план и статус (сессия 72749b60, 30.05.2026)

> Единый файл: что планировали, что сделано ✅, что НЕ сделано ❌.
> Темы: Грелка (правила проекта + мониторинг РК) + целостность хуков/правил (аудит + фиксы).
> Полное состояние: handover'ы + `audits/` + задачи #3/#4/#5.

═══════════════════════════════════════════════════════════
ASCII-обзор
═══════════════════════════════════════════════════════════
```
ТЕМА 1 — ГРЕЛКА
  Г1 Актуализация CLAUDE.md (presale→клиент)   [██████████] 100% ✅
  Г2 Handover                                  [██████████] 100% ✅
  Г3 Правило «старые РК до 30.06»              [██████████] 100% ✅
  Г4 Спека мониторинга РК+бюджета+авто-счёт    [██████████] 100% ✅ (правило)
  Г5 РЕАЛИЗАЦИЯ мониторинга (liveness/бюджет)  [░░░░░░░░░░]   0% ⏳ #5

ТЕМА 2 — ЦЕЛОСТНОСТЬ ХУКОВ/ПРАВИЛ
  Х1 Фикс дедлок-триады хуков                  [██████████] 100% ✅
  Х2 hook-interaction-lint + тест 4/4          [██████████] 100% ✅
  Х3 Аудит 94 хука + 91 правило                [██████████] 100% ✅
  Х4 Wire stop-smoothing (no-smoothing ожил)   [██████████] 100% ✅
  Х5 Слой 0: 7 fail-open → fail-CLOSED          [████░░░░░░]  40% ⏳ #3 (6/7 черновиков, НЕ на live)
  Х6 Wire 3 orphan-guardrail                   [░░░░░░░░░░]   0% ⏳ #4
  Х7 Rerun rule-conflict (48/91 упало)         [░░░░░░░░░░]   0% ⏳ #4
```
Легенда: ✅ done · ⏳ open(#задача) · 🔒 blocked

═══════════════════════════════════════════════════════════

## ✅ СДЕЛАНО

### Грелка
- **Г1** `clients/grelka-gudelka/CLAUDE.md` — статус presale → ✅ КЛИЕНТ: договор 22.05 (v4-signed), Этап-1 70К оплачен 29.05, учёт (70К revenue, 50К/мес в MRR с конца июня). Commit `2062fb7e`.
- **Г2** Handover `~/.claude/handovers/HANDOVER-2026-05-30-1530-grelka.md`.
- **Г3** Правило 🔴 «старые РК (Я.Директ+ВК прошлого подрядчика) держать живыми до 30.06.2026, новые рядом, аудит = только чтение».
- **Г4** Спека мониторинга в CLAUDE.md (раздел «Мониторинг РК и бюджета»). Commit `704d4083`.

### Хуки/правила
- **Х1** Дедлок-триада (`skill-required` ↔ `block-no-taskcreate` ↔ `recap-goal`) устранена. Commits `e0f1fbcc`, `e4395e20`.
- **Х2** `hooks/hook-interaction-lint.sh` + `hooks/tests/test-hook-interaction-lint.sh` (4/4 PASS, ловит искусственный цикл). Commits `6782fc2e`, `cc46b8b8`.
- **Х3** Аудит целостности 94 хука + 91 правило (workflow 33 агента) → `audits/2026-05-30-hook-rule-integrity.md`. Commit `34251521`. Итог: 0 циклов, **30 fail-open путей**, 9 orphans.
- **Х4** `stop-smoothing-check` зарегистрирован под Stop — no-smoothing детектор работал вхолостую (consumer был, producer нет). Commit `dd2dfb99`.

## ❌ НЕ СДЕЛАНО / ОТКРЫТО

### Задача #3 — Слой 0: 7 fail-open guardrail → fail-CLOSED (40%)
Guardrail'ы молча пропускают ровно тот инцидент, ради которого созданы.
- **Готово:** 6/7 черновиков в git `audits/failopen-drafts/` (commit `de39a4f6`), `bash -n` чисто. НА LIVE НЕ ПРИМЕНЕНО.
  - ✅ полный verdict+тест: `pre-finance-deploy` (7/7), `pre-outbound-gate` (12/12), `stop-deploy-url-check` (9/9).
  - 🟡 черновик есть, тест добить: `pre-strip-script-guard` (тест есть), `pre-cleanup-tokens-check`, `pre-scp-kp-strict-factcheck`.
  - 🔴 redraft: `pre-deploy-coords-verify.py` (не сдрафтился).
- **Осталось:** per-hook — diff vs live → прогнать hooktest → independent review → cp на live → проверить регистрацию в settings.json → commit. P0 первыми (strip-guard data-loss, cleanup-tokens OAuth-wipe).
- **Почему не доделано:** blast-radius (always-on на 3 аккаунта) + independent-verify в workflow не слинковался (баг join) + контекст был исчерпан. Осознанный стоп, не забывчивость.

### Задача #4 — Wire orphan + rerun rule-conflict (0%)
- Wire: `post-websearch-factcheck` (PostToolUse WebSearch|WebFetch), `post-ui-agent-strict` (SubagentStop), `pre-design-without-brand-source` (PreToolUse Edit|Write, проверить overlap с pre-kp-brand-extract-check).
- НЕ wire: `pre-scp-medical-aggregator` (правило disabled), `_disabled_inject-knowledge`, `post-deploy-qa-smoke`, `save_session.py`, `hook-interaction-lint` (standalone).
- Rerun rule-conflict: в аудите 6/12 батчей RuleDirectives + оба RuleConflicts агента упали → обработано 48/91 правил. «0 противоречий» НЕдостоверно.

### Задача #5 — Грелка: реализация мониторинга РК+бюджета (0%)
- **Liveness** оба источника (Директ+ВК) через Я.Метрика 97513054 (гостевой) — **доступно сейчас**.
- **Budget** достаточность месячного бюджета (Директ balance API; ВК Vitamin Tools).
- **Проактивный алёрт** заранее (остаток < 5-7 дней расхода).
- **Авто-счёт** на пополнение по истории прошлых сумм (`/finance-ops`, отправка = CONFIRM).
- **Блокеры:** ВК-баланс ждёт Vitamin/VK креды; Я.Директ balance — доступ к старому кабинету; liveness через Метрику — без блокера.

## Карта файлов
```
~/.claude/
├── audits/
│   ├── 2026-05-30-hook-rule-integrity.md      ← полный аудит (Х3)
│   ├── 2026-05-30-MASTER-PLAN-status.md       ← ЭТОТ файл
│   └── failopen-drafts/                        ← 6 черновиков + тесты + STATUS.md (#3)
├── hooks/hook-interaction-lint.sh + tests/     ← Х2
└── handovers/HANDOVER-2026-05-30-1530-grelka.md
artvision-data/clients/grelka-gudelka/CLAUDE.md ← Г1-Г4 (+ context-log.md)
```

## Следующий шаг (в чистом контексте)
1. **#3** применить fail-CLOSED черновики per-hook (P0: strip-guard, cleanup-tokens) — diff → тест → review → live → регистрация → commit.
2. **#5** запустить liveness-мониторинг Грелки через Метрику (доступно без блокеров).
3. **#4** wire 3 orphan + rerun rule-conflict.
