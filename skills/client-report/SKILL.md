---
name: client-report
description: Собрать месячный отчёт клиенту (Директ + SEO + оффлайн) из готовых скриптов в один документ по эталону usmile-otchet — дашборд-сверху + TOC, визуальный гейт, factcheck, деплой. Триггеры — 'отчёт клиенту', 'месячный отчёт', 'собери отчёт <клиент>', 'client report', 'report <client>', 'отчёт по контексту клиенту', 'отчёт за месяц'.
---

# /client-report — месячный отчёт клиенту (капстоун-оркестратор)

Связывает 6 готовых скриптов в один воспроизводимый отчёт. Эталон: `clients/usmile/reports/usmile-otchet-FINAL-2026-06-26.html` (live artvision.pro/usmile-otchet/).

## Когда применять
«Собери отчёт <клиент>», «месячный отчёт», «отчёт клиенту за месяц». Нужен логин кабинета Я.Директ клиента (tokens.json → yandex.direct.<login>).

## Пайплайн (по шагам)

### 1. Данные → черновик-блоки (детерминированно)
```bash
python3 ~/artvision-data/scripts/ppc/client-report.py \
  --client <slug> --login <direct-login> --from <YYYY-MM-DD> --to <YYYY-MM-DD>
# → clients/<slug>/reports/draft-<to>.md (3 блока: Директ без НДС + SEO + оффлайн)
```
Расход показать на экране только после пароля (finance-gate) → добавить `--show-cost`.

### 2. Сборка в HTML по эталону
- Взять/обновить страницу отчёта клиента (эталон usmile-otchet: hero → **дашборд-итоги** → **TOC по направлениям** → разделы → методология).
- `report-fill.py --html <src> --data <data.json>` вставляет дашборд-сверху + заполняет блоки по якорям.
- Структура строго ОБЩЕЕ→ЧАСТНОЕ (правило document-structure-general-to-specific): TOC сверху, дашборд с выводами+графиками, детали ниже.

### 3. Визуальный гейт (ОБЯЗАТЕЛЕН перед «готово»)
```bash
python3 ~/artvision-data/scripts/ppc/frontend-hardcheck.py --url <live-url>
```
- Текстовый factcheck СЛЕП к фронтенду (self-corrections #35) — без hardcheck не говорить «готово».
- PASS обязателен: overflow 375 = 0, картинки 200, бары не пустые, vision-validate ок.

### 4. Factcheck
```bash
python3 ~/.claude/scripts/factcheck-v2.py <file> --base-url <url> --standard
```
CRITICAL=0 → ок.

### 5. Деплой + ссылка
```bash
FACTCHECK_SKIP=1 ~/.claude/scripts/safe-deploy-html.sh <local> /var/www/artvision/<path>/index.html
```
Ответ Антону — **deploy-URL ПЕРВОЙ строкой** (feedback_deploy_url_first).

### 6. Человек-гейт
Показать Антону → CONFIRM → отправку клиенту делает Антон/Андрей (НЕ Claude напрямую).

## 🔴 ЗАШИТЫЕ ПРАВИЛА (не нарушать)
- **Расход Директа = БЕЗ НДС** (`--no-vat` в ppc-report; совпадает с Метрикой, которую видит клиент). НЕ с-НДС (self-corrections #36).
- **Суммы счёта (305к/245к/...) в клиентский отчёт НЕ вставлять** (finance-gate; счёт — отдельно).
- **Дашборд-сверху + TOC по направлениям** (общее→частное).
- **Mobile-first**, автономный HTML (base64, без CDN).
- **«Готово» только после frontend-hardcheck PASS** (визуал, не текст-чек).
- **Числа из API с источником**, нет данных → «настр.» (не выдумывать).
- **Вопрос про счёт/оплату** → `contract-terms.py` (договор-источник), не «из головы» (self-corrections #37).

## Скрипты (все готовы)
| Скрипт | Роль |
|---|---|
| `client-report.py` | оркестратор: запускает 3 ниже → черновик-блоки |
| `ppc-report.py --no-vat` | Директ (без НДС для клиента) |
| `seo-report.py` | SEO (Вебмастер+Метрика) |
| `offline-report.py` | оффлайн+посевы |
| `report-fill.py` | дашборд+TOC+вставка блоков |
| `frontend-hardcheck.py` | визуальный гейт |
| `contract-terms.py` | условия оплаты/счёт из договора |

## Связано
`docs/client-report-system-spec-2026-06-26.md` · правила document-structure-general-to-specific, single-table-progress-report, finance-password-gate · self-corrections #35-37 · хук pre-deploy-frontend-hardcheck · cron ppc-report-usmile.
