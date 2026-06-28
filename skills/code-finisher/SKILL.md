---
name: code-finisher
description: Прогнать петлю «реализация → Codex-ревью → рефакторинг → Codex re-verify → verify-гейт» для нетривиальной разработки кода. Codex (другое семейство, GPT-5.4) ловит слепые пятна Claude, шаг ревью нельзя пропустить. Триггеры — 'code-finisher', 'прогони кодекс-петлю', 'codex review loop', 'codex-петля', 'ревью+рефакторинг', 'кодекс ревью и рефакторинг', 'доведи код кодексом', 'review and refactor loop', 'finish the code'. Вызывать при разработке/правке кода в прод/клиент/инфра ИЛИ >~50 строк.
---

# code-finisher — Codex-ревью + рефакторинг как привычка

Оборачивает named workflow `code-finisher` (`~/artvision-data/.claude/workflows/code-finisher.js`) в одну команду. Делает привычку «Codex-ревью кода» детерминированной: порядок фаз зашит в код, Codex-шаг физически не пропустить.

## Когда применять (ПОРОГ)

Применять, если код попадает под хотя бы одно:
- меняет **прод-поведение** / деплоится клиенту / трогает **инфраструктуру** (хуки, LaunchAgent/cron, демоны, API-интеграции);
- **security-чувствительное** (auth, деньги, токены, автономное исполнение, SSRF/path-traversal);
- объём **> ~50 строк** или архитектурное изменение/рефакторинг;
- named workflow (`.claude/workflows/*.js`) — это тоже код.

НЕ применять (overkill → пропуск): опечатка/однострочник, конфиг-правка, маркетинг-работа (PPC/контент/КП — не код), тривиальный glue <~50 строк без прод-эффекта.

Правило: `codex-dev-lifecycle.md` (enforcement: правило → workflow → хук-кандидат).

## Что делает

Фазы (детерминированный порядок, цикл рефакторинга ≤2):

1. **Implement** — агент реализует/правит код по задаче.
2. **Codex-review** — `codex:codex-rescue` adversarial-ревью изменённых файлов → severity-находки (P0/P1/P2/P3) + вердикт APPROVED/REVISE.
3. **Refactor** — если есть блокеры (P0 всегда; P1 при пороге по умолчанию) → агент чинит по плану Codex → Codex re-verify. Цикл ≤2, потом эскалация в return.
4. **Verify** — агент прогоняет синтаксис/тесты/qa-гейт проекта + сверяет «ожидание == результат».

Возврат: `{status, findings, history, verify, commitsReady}`. `commitsReady:true` только после Codex-APPROVED + verify-гейта (коммитит человек — git не делается автоматически).

Деградация: если Codex недоступен (403/socket) — workflow эскалирует (ревью обязателен, заменить ревьюера на codex CLI / round_table / main, НЕ пропускать).

## Как вызвать

```
Workflow({ name: 'code-finisher', args: {
  task: '<что реализовать/исправить>',
  files: ['путь/к/файлу.py'],   // опц. — изменённые/целевые файлы
  threshold: 'P1',               // опц. — до какого severity чинить (P0 всегда блокер)
  maxCycles: 2,                  // опц. — потолок рефакторингов (макс 2)
  builderAgent: 'python-pro'     // опц. — тип агента-сборщика по agent-roster
}})
```

Связано: `codex-dev-lifecycle.md`, `finisher-loop.md`, `determinism-first-and-verify.md`, `enforcement-primitives.md`, `consilium-matrix.md` (codex-rescue).
