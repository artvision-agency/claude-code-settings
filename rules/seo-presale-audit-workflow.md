# SEO presale-аудит — канонический workflow авто-действий

> **Установлено:** 2026-06-04 (Антон, сессия DS-Lab). Distill из полного прогона DS-Lab — чтобы будущие SEO-аудиты шли автоматически по порядку, без сегодняшних граблей.
> **Корень проблем сессии (self-corrections #23/#24):** хендролл вместо скилла · структура из головы вместо seo-audit-spec.md · тёмная тема вместо системы клиента · «Pending» без проверки что данные реально недоступны.
> **Связано:** `templates/seo-audit-spec.md` (структура), `scripts/seo/run-seo-pipeline.sh`, `/seo-master`, `/seo-cluster`, `analyzed-project-design-system.md`, `dental-clinic-blueprint.md` (медицина), `/presale-kp` (генератор).

## ЖЁСТКИЙ порядок (выполнять строго сверху вниз)

### Шаг 0 — ЗАГРУЗИТЬ КАНОН (первым, всегда)
- `Read templates/seo-audit-spec.md` — структура 7 секций + TOC (§1 Профиль · §2 Конкуренты · §3 Позиции · §3a Top Pages · §4 Технический · §5 Потенциал+Тариф · §6 План 1 мес). Для медицины — `dental-clinic-blueprint.md` §XII (14 блоков).
- Извлечь **дизайн-систему клиента** с его сайта: `curl <site> + styles.css | grep '#hex' + font-family + hero-img`. НЕ дефолтить тёмную тему (правило `analyzed-project-design-system.md`).

### Шаг 1 — DATA-AVAILABILITY precheck (чтобы не врать «Pending» и не гадать)
Проверить ДО сборки, что реально доступно:
- **Topvisor позиции:** `get/positions_2/projects {show_searchers:1}` → если `searchers=НЕТ` → позиции НИКОГДА не снимались (новый клиент) → §3 честно «не настроено». Если searchers есть → `get/positions_2/history` (чтение БЕСПЛАТНО) → взять данные. Платный `checker/go` — только с ОК Антона.
- **SEMrush:** Playwright-сессия жива? RU-покрытие ниши тонкое → часто пусто, не блокер.
- **Токены:** keys.so (Яндекс top-pages), DataForSEO (`/seo-cluster` SERP-overlap), PSI (Lighthouse). Нет → §3a/кластер-валидация = «Pending», Lighthouse → локально (есть lhci+Chrome).
- **Доступ к Метрике/Вебмастеру клиента:** presale = нет → top-страницы трафика «Pending».
- Зафиксировать карту «собрано / Pending(почему)» — она ляжет в §3/§3a/секцию статуса.

### Шаг 2 — CRAWL (авторитет техданных)
`scripts/seo/run-seo-pipeline.sh <slug> https://<domain>` (touch sentinel + SF crawl + hybrid). Читать `sf-out/`: internal_all.csv (статусы), response_codes 4xx, page_titles_duplicate, canonicals_all (сколько пустых). НЕ грепом — csv-парс.

### Шаг 3 — СЕМАНТИКА (competitor-derived, не маски)
1. Текущее ядро из Topvisor.
2. Wordstat-расширение (Direct API v4 CreateNewWordstatReport, batch≤10, GeoID; параметр загрузки в Topvisor `add/keywords_2/keywords` → `to_id` не `group_id`) → **отсев shows=0**.
3. **gap от структуры конкурентов:** curl их sitemap.xml + /uslugi/ → service-кластеры → чего нет у клиента → Wordstat-валидация gap-ключей.
4. Кластер→посадочная карта (intent-based; SERP-overlap валидация = `/seo-cluster`+DataForSEO если токен есть).

### Шаг 4 — CWV
Lighthouse локально: `lighthouse https://<d>/ --only-categories=performance --form-factor=mobile --chrome-flags=--headless=new` → LCP/CLS/Perf. (PSI-токена обычно нет — локально работает.)

### Шаг 5 — КОНКУРЕНТЫ
WebSearch топ + **WebFetch каждого сайта** (не сниппеты): тип бизнеса (лаборатория vs клиника-заказчик!), услуги, прайс, B2B-блок, digital/срок-УТП. Чужие claim («ТОП-N РФ») = маркетинг, помечать.

### Шаг 6 — СБОРКА + ДЕПЛОЙ
- HTML **строго по seo-audit-spec.md** (TOC+§1-§6), в **дизайн-системе клиента** (hero-фото+overlay, иконки-метрики, SVG-секции, воздух — не плоские таблицы).
- §5 Тариф: 3 пакета (медицина 105/135/175К, иначе 95/145/195К — `feedback_pricing_by_revenue`).
- §6 План 1 мес: 4 направления (техфикс → семантика→посадочные → контент → аналитика).
- Деплой review-URL `artvision.pro/_priv-<slug>-<date>/` (--ack-anton для outbound-gate, SEO_MASTER_FORCE если pipeline уже прогнан) → curl HTTP 200.
- **Скриншот-верификация** (Chrome headless → Read png) — смотреть глазами, не вслепую.
- Deploy-URL Антону **первой строкой** (правило ВСЕГДА deploy-links).

## Антипаттерны (ровно сегодняшние грабли)
- ❌ Собирать структуру из головы вместо открытия seo-audit-spec.md (Шаг 0)
- ❌ Тёмная тема вместо системы клиента (Шаг 0 extract)
- ❌ «Pending позиции» без проверки searchers/history (Шаг 1)
- ❌ Семантика масками из головы вместо gap от конкурентов (Шаг 3)
- ❌ Конкуренты по сниппетам без захода на сайт (Шаг 5)
- ❌ Деплой без скриншот-проверки глазами (Шаг 6)
- ❌ file:// вместо live deploy-URL первой строкой

## TODO — превратить в Skill (чистая сессия, через skill-generator)
1. `/seo-presale-audit <slug> <domain>` — обёртка над Шагами 0-6 (главный кандидат).
2. `/topvisor-data-check <project_id>` — Шаг 1 precheck (searchers/history/платность).
3. `/competitor-semantics <domain> <competitors>` — Шаг 3.3 (structure→gap→Wordstat).
4. Кандидат-хук `stop-audit-structure-check.sh` — деплой `clients/*/seo/*.html` без маркеров §1-§6 → warn (self-corrections #24).
