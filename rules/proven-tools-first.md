# Принцип: проверенные инструменты — не велосипеды

> **Антон, 20.05.2026 02:35 MSK:** «мне надо чтобы мы пользовались именно полным проверенными инструментами»
> **Прецедент:** ночь Wave A audit — я писал кастомный `perf-monitor.sh` 280 строк, когда есть `@lhci/cli` (Google, ~5K stars, 2M npm downloads/мес) + `unlighthouse` (~3.5K stars).

## Правило

**Перед написанием кастомного решения** для типовой задачи — **обязательный 3-минутный research**:
1. WebSearch: `"<task>" github stars 2026`
2. WebSearch: `<task> production tool 2026`
3. Если есть GitHub repo **с >1K stars + recent commits** в нужной нише → **adopt вместо write**

## Признаки «велосипеда» (не делай)

- Bash-скрипт >100 строк для типовой задачи (мониторинг, тесты, бенчмарки, парсинг)
- Кастомный wrapper над public API когда есть mature CLI
- «Свой» config-формат вместо standard (YAML / TOML / JSON schema)
- Repeated regex parsing где есть jq / yq / xmlstarlet

## Признаки «проверенного tool»

- GitHub stars >1K (для CLI/utility) или >10K (для framework)
- Recent commits последние 6 месяцев
- npm/PyPI/cargo с installs >100K/мес
- Использование в production known companies (есть в README)
- Активный issue tracker (не abandoned)

## Готовый каталог (для частых задач)

| Задача | Велосипед | ✅ Проверенный |
|--------|-----------|-----------------|
| Lighthouse мониторинг | bash + PSI API curl | **`@lhci/cli`** (Google, ~5K stars) ИЛИ **`unlighthouse`** (~3.5K) |
| Site crawl | curl + python + bs4 | **Screaming Frog CLI** (наш `sf`) |
| Web vitals real users | Custom JS beacon | **`web-vitals`** библиотека (~6K stars) |
| Daily cron monitoring | Bash + cron | **`monit`**, **`uptime-kuma`** (~50K stars) |
| HTTP load test | bash + ab/curl | **`k6`** (Grafana, ~26K stars), **`vegeta`** (~22K stars) |
| Image optimization | bash + sips/convert | **`squoosh-cli`** (Google, ~21K stars) ИЛИ **`sharp-cli`** (~30K) |
| WordPress backup | tar + cron | **`UpdraftPlus`** (3M+ active installs) |
| HTML/CSS quality | custom validator | **`htmlhint`**, **`stylelint`**, **`axe-core`** |
| Markdown to PDF | Pandoc + bash | **`wkhtmltopdf`** ИЛИ **`puppeteer`** |
| API rate limit handling | Custom retry loop | **`p-retry`**, **`bottleneck`** (npm) |
| YAML/JSON config | Custom parser | **`yq`** (~13K stars), **`jq`** (~32K) |

## Что МОЖНО писать своё (legit cases)

- **Glue / pipeline скрипт** соединяющий 2-3 готовых tool (`lhci` + `jq` + `curl-tg`)
- **Domain-specific business logic** (нет общего инструмента — например, Artvision Flow аналитика)
- **Adapter** между нашим стеком и tool (yaml → lhci config)
- **Custom report генерация** на основе output готового tool

## Антипаттерн

❌ Пишу 280 строк bash-скрипта для PSI мониторинга когда `@lhci/cli` делает то же лучше
❌ Реализую custom Markdown parser когда есть `marked` / `markdown-it`
❌ Свой `wp-cli` wrapper когда официальный `wp-cli` работает
❌ Custom screenshot tool когда есть Playwright / Puppeteer

## Применение

Перед каждой новой инфраструктурной задачей задать себе вопросы:
1. Есть ли это в GitHub-каталоге выше?
2. Если нет — 3 минуты WebSearch?
3. Если кастом — обоснованно ли это "domain-specific" или просто «не искал»?

Если **кастом без research** — STOP, ищи. Прецедент 20.05.2026 — потеряно ~2 часа на perf-monitor.sh + skill /perf-bench velosipeed.

## Связанные

- `~/.claude/rules/tool-adoption-proof.md` — round_table перед adopt нового инструмента
- `~/.claude/rules/core.md` — autonomous workflow
- `clients/artvision-pro/audits/2026-05-19-frontend/LESSON-lighthouse-snap-chromium.md`
