---
name: perf-bench
description: Production-grade performance benchmark сайтов. Не использует snap chromium Lighthouse (нестабильно — давал 65/33/32/0/0/0 в 6 раундах на одном URL). Использует PSI Google + WebPageTest + GTmetrix как primary, local Chrome Lighthouse как secondary. Сравнивает с baseline из ~/perf-history/, генерит HTML отчёт в clients/<name>/perf/. Mobile-first thresholds. Triggers — "перф", "perf check", "benchmark", "lighthouse <url>", "cwv <url>", "pagespeed <url>", "core web vitals", "как страница грузится", "проверь скорость".
triggers:
  - перф
  - perf check
  - perf-bench
  - benchmark
  - lighthouse
  - cwv
  - pagespeed
  - core web vitals
  - как страница грузится
  - проверь скорость
  - psi
  - webpagetest
---

# /perf-bench — Production Performance Benchmark

> Замена нестабильного snap chromium Lighthouse. Источник правды — PSI Google + WebPageTest CrUX. Voiceless mode для post-deploy, deep mode для аудитов.

## Когда применять

| Сценарий | Mode |
|---|---|
| Post-deploy smoke (за 30 сек убедиться что не уронили) | `quick` |
| Полный аудит страницы клиента / отчёт | `deep` |
| Регрессия — сравнение с baseline 7-30 дней назад | `compare` |
| Один URL много замеров (anti-snap-chromium) | `multi` (3× PSI, median) |

## Запуск

```
/perf-bench <URL> [--mode=quick|deep|compare|multi] [--client=<slug>] [--device=mobile|desktop|both]
```

Дефолт: `--mode=quick --device=mobile`.

## Pipeline — 5 шагов

### STEP 1 — Curl baseline (5 сек)

```bash
URL="$1"
HOST=$(echo "$URL" | awk -F/ '{print $3}')
mkdir -p ~/perf-history/"$HOST"

curl -sI -o /dev/null -w \
  'HTTP %{http_code} | size=%{size_download}B | ttfb=%{time_starttransfer}s | total=%{time_total}s | http_version=%{http_version} | scheme=%{scheme}\n' \
  --compressed \
  -H 'User-Agent: Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 Mobile' \
  "$URL"
```

Проверки:
- HTTP 200 (если 3xx/4xx/5xx → STOP, не имеет смысла мерить дальше)
- TTFB <600ms (>800ms = backend slow → отметить)
- http_version=2 или 3 (HTTP/1.1 = legacy, флаг amber)
- content-encoding=br/gzip (отсутствие = misconfig)

### STEP 2 — PSI Google API (mobile + desktop)

PSI = главный источник. CrUX field data = реальные пользователи Chrome за 28 дней.

```bash
PSI_KEY=$(python3 -c "import json; print(json.load(open('/Users/antonk/artvision-data/tokens.json')).get('google',{}).get('pagespeed_api_key',''))" 2>/dev/null)
# fallback: без ключа — 25 req/day public quota
KEY_PARAM=""
[ -n "$PSI_KEY" ] && KEY_PARAM="&key=$PSI_KEY"

for STRATEGY in mobile desktop; do
  curl -s "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=${URL}&strategy=${STRATEGY}&category=performance&category=accessibility&category=best-practices&category=seo${KEY_PARAM}" \
    -o ~/perf-history/"$HOST"/psi-"$STRATEGY"-$(date +%Y-%m-%d-%H%M).json
done
```

Извлекаемые метрики (Lighthouse audits в ответе PSI):
- `largest-contentful-paint` (LCP)
- `interaction-to-next-paint` (INP, заменил FID)
- `cumulative-layout-shift` (CLS)
- `total-blocking-time` (TBT)
- `first-contentful-paint` (FCP)
- `speed-index` (SI)
- `performance` score 0-100

Извлечь через `jq`:

```bash
jq -r '.lighthouseResult.audits |
  "LCP=\(.["largest-contentful-paint"].numericValue/1000)s | " +
  "INP=\(.["interaction-to-next-paint"].numericValue // "n/a")ms | " +
  "CLS=\(.["cumulative-layout-shift"].numericValue) | " +
  "TBT=\(.["total-blocking-time"].numericValue)ms | " +
  "FCP=\(.["first-contentful-paint"].numericValue/1000)s"' \
  ~/perf-history/"$HOST"/psi-mobile-*.json | tail -1
```

CrUX field data (реальные пользователи) — отдельный блок:

```bash
jq -r '.loadingExperience.metrics |
  "field_LCP=\(.LARGEST_CONTENTFUL_PAINT_MS.percentile)ms | " +
  "field_INP=\(.INTERACTION_TO_NEXT_PAINT.percentile // "n/a")ms | " +
  "field_CLS=\(.CUMULATIVE_LAYOUT_SHIFT_SCORE.percentile)"' \
  ~/perf-history/"$HOST"/psi-mobile-*.json | tail -1
```

### STEP 3 — WebPageTest (опционально, deep mode)

```bash
WPT_KEY=$(python3 -c "import json; print(json.load(open('/Users/antonk/artvision-data/tokens.json')).get('webpagetest',{}).get('api_key',''))" 2>/dev/null)

if [ -n "$WPT_KEY" ]; then
  WPT_ID=$(curl -s "https://www.webpagetest.org/runtest.php?url=${URL}&k=${WPT_KEY}&f=json&location=Dulles:Chrome.3G&runs=3&fvonly=1&mobile=1" | jq -r '.data.testId')
  echo "WPT submitted: $WPT_ID, poll https://www.webpagetest.org/result/$WPT_ID/"
  # polling: каждые 30 сек до .data.statusCode=200, max 5 мин
fi
```

3 locations рекомендация для deep mode: `Dulles:Chrome.3G`, `Frankfurt:Chrome.Cable`, `Mumbai:Chrome.4G` (захватывает географию клиентов).

### STEP 4 — Сравнение с baseline

```bash
HISTORY_DIR=~/perf-history/"$HOST"
LATEST=$(ls -t "$HISTORY_DIR"/psi-mobile-*.json | head -1)
PREVIOUS=$(ls -t "$HISTORY_DIR"/psi-mobile-*.json | sed -n '2p')  # вчерашний или предыдущий
WEEK_AGO=$(ls -t "$HISTORY_DIR"/psi-mobile-*.json | awk -v d="$(date -v-7d +%Y-%m-%d 2>/dev/null || date -d '7 days ago' +%Y-%m-%d)" '$0 ~ d' | head -1)

# regression check
diff_score() {
  local cur=$(jq '.lighthouseResult.categories.performance.score * 100' "$1")
  local old=$(jq '.lighthouseResult.categories.performance.score * 100' "$2")
  echo "$cur - $old" | bc
}
```

Если regression >5 points performance score → `quick` mode шлёт TG alert через `scripts/tg-send.sh`.

### STEP 5 — HTML отчёт

Путь: `clients/<slug>/perf/perf-bench-<YYYY-MM-DD>-<HHMM>.html` (или `~/perf-reports/<host>/...` если client не указан).

Шаблон ниже.

## CWV Thresholds (mobile-first)

| Метрика | Green | Amber | Red |
|---|:---:|:---:|:---:|
| LCP | <2.5s | 2.5-4s | >4s |
| INP | <200ms | 200-500ms | >500ms |
| CLS | <0.1 | 0.1-0.25 | >0.25 |
| TBT | <200ms | 200-600ms | >600ms |
| FCP | <1.8s | 1.8-3s | >3s |
| Performance score | ≥90 | 50-89 | <50 |
| TTFB (curl) | <600ms | 600-1500ms | >1500ms |

Desktop thresholds мягче (LCP green <1.5s, TBT <100ms) — для отчётов клиентам показывать ОБЕ колонки.

## Quick Mode (post-deploy, 30 сек)

```bash
perf_quick() {
  URL="$1"
  # 1. Curl smoke
  curl -sI -w 'HTTP %{http_code} | ttfb=%{time_starttransfer}s\n' -o /dev/null "$URL"
  # 2. PSI mobile only
  curl -s "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=${URL}&strategy=mobile&category=performance${KEY_PARAM}" |
    jq -r '"score=\(.lighthouseResult.categories.performance.score*100) LCP=\(.lighthouseResult.audits["largest-contentful-paint"].displayValue) CLS=\(.lighthouseResult.audits["cumulative-layout-shift"].displayValue)"'
  # 3. Regression check vs baseline
  # 4. TG alert если score упал >5 points
}
```

TG alert template:
```
PERF REGRESSION on <host>
Score: 87 → 71 (-16)
LCP: 2.1s → 3.8s
Deploy commit: <sha>
URL: <url>
```

## Deep Mode (audit, 3-5 мин)

```
1. Curl baseline (mobile UA + desktop UA)
2. PSI mobile + desktop (по 3 раза, median)
3. WebPageTest 3 locations × 3 runs (если ключ есть)
4. CrUX field data (28-day percentiles)
5. Сравнение с baseline 7 и 30 дней назад
6. Top issues — извлечь из PSI lighthouseResult.audits с score<0.9
7. HTML отчёт с trend графиком (CSS-only sparkline)
```

## Multi Mode (anti-snap-chromium, для надёжности на одном URL)

PSI запускается 3 раза с интервалом 30 сек → берётся медиана LCP/INP/CLS. Защита от cold cache / CDN warmup.

```bash
for i in 1 2 3; do
  curl -s "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=${URL}&strategy=mobile${KEY_PARAM}" \
    > /tmp/psi-run-$i.json
  sleep 30
done

# median LCP
for f in /tmp/psi-run-*.json; do
  jq -r '.lighthouseResult.audits["largest-contentful-paint"].numericValue' "$f"
done | sort -n | awk 'NR==2'  # median of 3
```

## HTML Report Template

```html
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Perf Bench — {{HOST}} — {{DATE}}</title>
<style>
:root { --green: #16a34a; --amber: #d97706; --red: #dc2626; --bg: #0a0a0a; --text: #f5f5f5; }
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--text); padding: 32px; max-width: 1100px; margin: 0 auto; }
h1 { font-size: 28px; margin-bottom: 8px; }
.meta { color: #9ca3af; font-size: 14px; margin-bottom: 32px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 32px; }
.card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 12px; padding: 20px; }
.card .label { font-size: 12px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em; }
.card .value { font-size: 28px; font-weight: 700; margin: 8px 0; }
.card .status { font-size: 11px; padding: 2px 8px; border-radius: 4px; display: inline-block; }
.status.green { background: rgba(22,163,74,0.2); color: var(--green); }
.status.amber { background: rgba(217,119,6,0.2); color: var(--amber); }
.status.red { background: rgba(220,38,38,0.2); color: var(--red); }
table { width: 100%; border-collapse: collapse; margin: 16px 0; }
th, td { padding: 12px; text-align: left; border-bottom: 1px solid #2a2a2a; }
th { background: #1a1a1a; font-size: 12px; text-transform: uppercase; color: #9ca3af; }
.sparkline { display: inline-flex; gap: 2px; align-items: flex-end; height: 24px; }
.sparkline span { width: 6px; background: var(--green); border-radius: 1px; }
.warn { background: #1a1208; border-left: 4px solid var(--amber); padding: 16px; margin: 24px 0; border-radius: 4px; }
</style>
</head>
<body>
<h1>Perf Bench — {{HOST}}</h1>
<div class="meta">{{DATE}} · mode={{MODE}} · URL: <a href="{{URL}}" style="color:#60a5fa">{{URL}}</a></div>

<div class="grid">
  <div class="card">
    <div class="label">Performance Score (mobile)</div>
    <div class="value">{{SCORE_MOBILE}}</div>
    <span class="status {{SCORE_STATUS}}">{{SCORE_STATUS_TEXT}}</span>
  </div>
  <div class="card">
    <div class="label">LCP</div>
    <div class="value">{{LCP}}s</div>
    <span class="status {{LCP_STATUS}}">{{LCP_STATUS_TEXT}}</span>
  </div>
  <div class="card">
    <div class="label">INP</div>
    <div class="value">{{INP}}ms</div>
    <span class="status {{INP_STATUS}}">{{INP_STATUS_TEXT}}</span>
  </div>
  <div class="card">
    <div class="label">CLS</div>
    <div class="value">{{CLS}}</div>
    <span class="status {{CLS_STATUS}}">{{CLS_STATUS_TEXT}}</span>
  </div>
  <div class="card">
    <div class="label">TBT</div>
    <div class="value">{{TBT}}ms</div>
    <span class="status {{TBT_STATUS}}">{{TBT_STATUS_TEXT}}</span>
  </div>
  <div class="card">
    <div class="label">TTFB (curl)</div>
    <div class="value">{{TTFB}}s</div>
    <span class="status {{TTFB_STATUS}}">{{TTFB_STATUS_TEXT}}</span>
  </div>
</div>

<h2>CrUX Field Data (28 days, real users)</h2>
<table>
  <thead><tr><th>Metric</th><th>p75 mobile</th><th>p75 desktop</th><th>Status</th></tr></thead>
  <tbody>{{CRUX_ROWS}}</tbody>
</table>

<h2>Top Issues</h2>
<table>
  <thead><tr><th>Audit</th><th>Impact</th><th>Score</th></tr></thead>
  <tbody>{{ISSUES_ROWS}}</tbody>
</table>

<h2>Trend (last 14 runs)</h2>
<div class="sparkline">{{SPARKLINE_BARS}}</div>

{{REGRESSION_WARN}}

<h2>Methodology</h2>
<ul>
  <li>Источник: PSI Google API (Lighthouse 11+ remote, headless Chrome on Google infra)</li>
  <li>НЕ используется snap chromium Lighthouse (давал нестабильные оценки 65/33/32/0/0/0 на одном URL — ловушка Ubuntu 24.04 server snap)</li>
  <li>Mobile thresholds — primary (Pixel 5, Slow 4G throttling)</li>
  <li>Median of 3 runs если --mode=multi</li>
  <li>CrUX field data — реальные пользователи Chrome за 28 дней (p75)</li>
</ul>
</body>
</html>
```

## Anti-Patterns — что НЕ делать

| Anti-pattern | Почему запрет | Что вместо |
|---|---|---|
| snap chromium Lighthouse на Ubuntu 24.04 server | 6 раундов дали 65/33/32/0/0/0 (LESSON-lighthouse-snap-chromium.md). Headless+devtools throttling+snap sandboxing = race conditions | PSI Google API (Google infra, стабильно) |
| Один замер = вердикт | CDN cold cache, network jitter, CPU contention | Минимум 3 замера, median (multi mode) |
| Lighthouse на VPS под нагрузкой | CPU contention с pm2/nginx workers → TBT/TTI = `?` | PSI на Google или local Mac с idle CPU |
| Доверять TBT/TTI с chromium throttling если CPU занят | Throttling работает поверх real CPU clock — под нагрузкой даёт мусор | CrUX field data (реальные пользователи) |
| Сравнение mobile vs desktop как «улучшение» | Разные throttling profiles, не сопоставимы | Только same-strategy: mobile↔mobile, desktop↔desktop |
| Lighthouse score как единственная метрика | Score = взвешенная композиция, маскирует регрессию одной метрики | Смотреть LCP+INP+CLS+TBT отдельно + score |

## Файлы

| Файл | Назначение |
|---|---|
| `~/perf-history/<host>/psi-<strategy>-<timestamp>.json` | Сырые PSI snapshots для baseline сравнения |
| `~/perf-history/<host>/wpt-<id>.json` | WebPageTest результаты |
| `clients/<slug>/perf/perf-bench-<date>.html` | Готовый отчёт для клиента |
| `~/.claude/skills/perf-bench/SKILL.md` | Этот файл |

## Связанные инструменты

- `scripts/perf-monitor.sh` (artvision-data, TBD) — обёртка над PSI для cron-monitoring активных клиентов
- `scripts/tg-send.sh` — алёрты в команду при regression
- `~/.claude/rules/quality.md` — gate для SEO/audit задач (Lighthouse + SF + Webmaster)
- `clients/artvision-pro/audits/2026-05-19-frontend/LESSON-lighthouse-snap-chromium.md` — исходный урок про нестабильность snap chromium

## TG alert (quick mode regression)

```bash
~/.claude/scripts/tg-send.sh team_alerts "[PERF REGRESSION] $HOST
Score: $OLD → $NEW ($DIFF)
LCP: $OLD_LCP → $NEW_LCP
URL: $URL
Report: $REPORT_URL
Commit: $(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo n/a)"
```

## Ключи (tokens.json)

- `google.pagespeed_api_key` — опционально, поднимает квоту с 25/day до 25000/day
- `webpagetest.api_key` — опционально, для deep mode

Если ключей нет — `quick` mode работает на public quota (25 req/day хватает для post-deploy smoke).

## Прецедент

19-20.05.2026 ночь — Artvision frontend audit. 6 раундов snap chromium Lighthouse на VPS дали performance score 65, 33, 32, 0, 0, 0 на одном URL без изменений сайта. Стало ясно что snap chromium = ненадёжный измерительный инструмент. PSI Google и WebPageTest на тех же URL давали стабильные ±3 points. Skill закрепляет этот вывод инструментально — больше никаких snap chromium runs.
