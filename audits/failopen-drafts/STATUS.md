# Fail-open guardrail фиксы — ЧЕРНОВИКИ (НЕ применены на live)

> Источник: workflow `failopen-guardrail-fix-drafts` (wf_951af02d-b39), 30.05.2026.
> Задача #3. Принцип: fail-CLOSED (сбой парса/зависимости/сети = блок), без ослабления.
> **СТАТУС: черновики готовы к ревью. НА LIVE НЕ ПРИМЕНЕНЫ** (blast-radius + неполный independent verify + контекст исчерпан).

## Готовность черновиков

| Хук | Черновик | Тест | Self-тест | fail-CLOSED | Готов к ревью |
|-----|:--------:|:----:|----------|:-----------:|:-------------:|
| `pre-finance-deploy.sh` | ✅ | ✅ | 7/7 PASS | ✅ | ✅ ДА (полный verdict) |
| `pre-outbound-gate.sh` | ✅ | ✅ | 12/12 PASS | ✅ | ✅ ДА (полный verdict) |
| `stop-deploy-url-check.sh` | ✅ | ✅ | 9/9 PASS | ✅ | ✅ ДА (полный verdict) |
| `pre-strip-script-guard.sh` | ✅ | ✅ | агент упал на StructuredOutput | ? | 🟡 черновик+тест есть, прогнать тест вручную |
| `pre-cleanup-tokens-check.sh` | ✅ | ❌ | агент упал | ? | 🟡 черновик есть, теста нет → дописать |
| `pre-scp-kp-strict-factcheck.sh` | ✅ | ❌ | агент упал | ? | 🟡 черновик есть, теста нет → дописать |
| `pre-deploy-coords-verify.py` | ❌ | ❌ | НЕ сдрафтился | — | 🔴 redraft с нуля |

## Что сделали 3 «зелёных» черновика (полный verdict)

- **pre-finance-deploy**: отсутствие/нечитаемость factcheck-numeric.py (L5) и factcheck-finance-domain.py (L6) → exit 0 (банк-документ без проверки) заменено на exit 2 block. + латентный баг: `python3 ... | tail -3` брал exit-код у tail (всегда 0) → заменено на PIPESTATUS[0]. Bypass FINANCE_DEPLOY_SKIP=1 сохранён. ⚠️ Остаточный риск: Edit/Write-ветка деплоя финанс-документов в хуке не реализована (обход через прямой Edit) — отдельная задача.
- **pre-outbound-gate**: парс CMD `python3 2>/dev/null` при сбое → CMD пуст → exit 0 пропускал scp/email/telegram на чужой хост. Фикс: set -uo pipefail + парс-ошибка/нет python3/битый JSON → exit 2. Сохранено различие: валидная пустая команда → exit 0, сбой парса → exit 2. bypass --ack-anton сохранён.
- **stop-deploy-url-check**: `python3 2>/dev/null` сбой → SESSION_ID пуст → exit 0 молча пропускал enforcement. Фикс: fail_closed() с видимым warn + exit 2 при невозможности проверить. ⚠️ Риск: если харнес зовёт Stop без session_id/до создания .jsonl → ложный блок (нужен DEPLOY_URL_OK=1) — понаблюдать на первом прогоне.

## Применение на live (в чистом контексте, per-hook)

1. Прочитать diff черновик vs live (`diff ~/.claude/hooks/<name> hookfix-<name>`).
2. Прогнать тест: `bash hooktest-<name>.sh` → должен PASS.
3. Independent review (агент-скептик или вручную): fail-CLOSED? не ослабляет? happy-path жив?
4. `cp` черновик → live + `bash -n`.
5. Зарегистрирован ли в settings.json? (self-corrections #18 — иначе тихо не работает).
6. Commit per-hook.

НЕ применять пачкой. P0 первыми: pre-strip-script-guard (data-loss), pre-cleanup-tokens (OAuth-wipe) — но у них нет полного verdict, нужен прогон теста.
