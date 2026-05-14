# Handover: 3 SEO-аудит-КП (spb-kursy / cosmetology-kursy / hair-courses) + TG-popup backend

**Дата:** 2026-05-12 01:40
**Контекст:** presale
**Сессия:** KURSY-SPB 2 (0b1c2265-f0ac-4b7c-b6f1-07864ded2f2e), продолжение KURSY-SPB (c4f36879)
**Статус:** в работе — 3 КП на проде, 1 критичный security-блокер открыт

## 🎯 Цель сессии

Закончить 3 SEO-аудит-КП для одного владельца (массаж/косметология/парикмахер СПб) + защитить TG-popup backend от спама.

## ✅ Что сделано

### 3 КП на проде (HTTP 200, MD5 local==prod)
- `presales/spb-kursy/kp/spb-kursy_kp_v3.html` → https://artvision.pro/kp/spb-kursy-v3/ — 270 KB, CAMEO navy+gold
- `presales/cosmetology-kursy/kp/cosmetology-kursy_kp_v3.html` → https://artvision.pro/kp/cosmetology-kursy-v3/ — 260 KB, lavender #9D8FD8
- `presales/hair-courses/kp/hair-courses_kp_v3.html` → https://artvision.pro/kp/hair-courses-v3/ — 105 KB, orange+turquoise

### Контент (8 секций + 2 новых)
- `#tldr` — 4 цветные плашки (двойной язык: техника + собственник)
- `#family` — родственные домены + robots.txt + llms.txt
- `#score` — 4 фактора SEO
- `#visibility` — 20 ключей × позиции (Topvisor snapshot 11.05, project 28362497, lr=2)
- `#potential` — модель «Заявки = Трафик × Конверсия (вилка 0.5/1/2%, baseline 1%)»
- `#backlinks` — SEMrush AS/RD/BL × 4 домена + CSS-bars chart + анкоры shkolamm (только в spb)
- `#tech` — топ-5 технических показателей
- `#market-presence` — доля в анализируемом кластере 20 ключей (с дисклеймером «не TAM»)

### Интерактив в hero
- Input с typewriter-плейсхолдером (8 циклических вопросов)
- 7 chip-кнопок (💰 цена / ⚔️ конкурент / 📈 окупаемость / 📞 заявки / 🛡 гарантии / ⏱ сроки / 📋 пакет)
- TG-popup → POST на `/api/kp-message.php` → @avportal_bot → chat_id 161261562
- Sticky bar справа снизу: TG + tel:+79110861888

### Backend (на VPS 80.90.181.152)
- `/var/www/artvision/api/kp-message.php` — принимает POST `{question, kp_url}` → шлёт через avportal_bot
- CORS: `Access-Control-Allow-Origin: *`
- HTML-escape работает (XSS test passed: `<script>alert(1)</script>` пришло как текст)
- Empty validation: возвращает `{ok:false, err:"empty"}`

### Тесты пройдены
| Тест | Результат |
|---|---|
| Valid POST | ✅ `{ok:true}`, дошло в TG |
| Empty question | ✅ rejected |
| XSS payload | ✅ escaped |
| CORS OPTIONS | ✅ headers OK |
| Long 5000 chars | ✅ принят (TG порежет до 4096) |
| Emoji + cyrillic | ✅ принят |
| Frontend integration | ✅ во всех 3 КП |
| **Rate-limit (10 req подряд)** | 🔴 **FAIL — все 10 прошли** |

### Инфраструктура для будущих аудитов
- `~/.claude/skills/audit-kp/SKILL.md` — вызов `/audit-kp <url>`
- `~/.claude/rules/audit-kp-pipeline.md` — 12-шаговый pipeline
- `~/artvision-data/templates/audit-kp-template.html` (276 KB шаблон с placeholders)
- `~/artvision-data/scripts/seo/content_volume_benchmark.py` — word count vs ТОП-10 SERP

### Hooks (warning-only, не блокируют)
- `pre-kp-brand-extract-check.sh` — блокирует Write КП без curl на домен
- `stop-claim-no-rule-check.sh` — warning при «правило не зафиксировано» без grep по 4 источникам
- 6 KP-hooks: competitor-proof, backlinks-no-judgment, hero-unique, market-disclaimer, backlinks-visual, ai-overview-pose

### Self-corrections (в `~/.claude/rules/self-corrections.md`)
- **#15:** КП с дефолтной палитрой шаблона при копировании (cosmetology получил navy+gold от spb)
- **#16:** Claim «нигде нет правила X» без полной проверки 4 источников

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему выбрали это |
|---------|--------------|---------------------|
| Direct API forecasts × 1.15 коэф вместо Wordstat | Ждать восстановления Wordstat подписки | Wordstat API expired 09.05 (403), Direct API даёт impressions+clicks+CPC, коэф откалиброван на CSV 08.05 |
| SEMrush UI scrape для backlinks | DataForSEO Backlinks API | Антон явно сказал «беклинки берём с семраш» — наши креды в `tokens.json` |
| 3 разные палитры (не одна) | Единый CAMEO стиль | Каждый КП — отдельный клиент с отдельным брендом, иначе выглядит как копия |
| Конверсия 1% baseline + вилка 0.5/1/2% | Гарантировать % | Реальная CR измеряется только Я.Метрикой после старта; baseline = индустриальный |
| #market-presence как «доля кластера», не TAM | Считать TAM/SAM | Наша выборка = 20 ключей, реальный рынок шире; честнее не врать |
| TG-popup share dialog → backend POST | Только share dialog (без backend) | Антон попросил «чтобы реально приходило мне» — backend через avportal_bot |
| shkolamm в #backlinks НЕ помечать «плохо» | Сразу обозвать спамом | Антон поправил: shkolamm в ТОП-1/2 = схема работает; нельзя оценивать ссылки без позиций |
| Audio/video кружки к блокам — НЕ делать сейчас | Записать сразу | Антон собирался записать кружки, не записал → перенесено |
| AI Overview через heuristic (форма запроса) | Реальный SERP-снимок | Topvisor SERP module не в нашем тарифе (1003 endpoint not found); 18 endpoints проверены |

## ❌ Что НЕ сделано и почему

| Задача | Статус | Почему |
|--------|--------|--------|
| **Rate-limit на /api/kp-message.php** | 🔴 КРИТИЧНО — security блокер | Контекст 0% + хуки blocked. 10 req подряд проходят → можно спамить Антона в TG. Готовый PHP в этом handover ниже. |
| Прямые конкуренты для cos + hair | ⚠️ оговорено в КП | Не было snapshot — обещали «соберём в 1-ю неделю работ» |
| Backlinks deep-anchors для cos + hair | ⚠️ только в spb | SEMrush deep-агент не дотянул до всех 3 доменов |
| Wordstat dynamics 24-мес графики | ❌ заблокировано | Я.ID 2FA для dune87@yandex.ru + borisovaloves упёрся в Яндекс Ключ |
| AI Overview точный snapshot | ❌ heuristic применена | Topvisor SERP module не в тарифе |
| E2E Playwright тесты TG-popup | ❌ контекст не дал | Mobile 375px, fallback при backend down — не верифицировано |
| Audio/video кружки к блокам | ⏸ ждём Антона | Антон собирался записать через TG, не успел |
| Reusable JS-компонент tg-popup.js | ⏸ автоматизация | Сейчас inline JS в каждом КП |
| Health-check cron на endpoint | ⏸ автоматизация | Узнавать о падении до клиента |

## 📚 Уроки (новое знание для memory)

- **Копирование шаблона КП ≠ работа с нуля** — обязательный extract дизайн-системы каждого нового домена. Хук `pre-kp-brand-extract-check.sh` уже создан → self-corrections.md #15.
- **«Правило не зафиксировано» — никогда без grep по 4 источникам**: `~/.claude/rules/`, `~/artvision-data/.claude/rules/`, `~/.claude/projects/-Users-antonk/memory/`, `~/.claude/skills/*/SKILL.md` → self-corrections.md #16.
- **«Главный конкурент» = доказательство по позициям, не интуиция** → правило `~/.claude/rules/competitor-selection.md`
- **Backlinks: 10 дорогих ≈ 500 дешёвых** — оценка качества ссылок без позиций бессмысленна. Сначала снять SERP, потом судить.
- **Размер рынка ≠ TAM/SAM** — если по выборке 20 ключей, явно дисклеймь «не TAM, относительная база».
- **Рейт-лимит на любой публичный endpoint = критично** — backend без него = вектор спама. Должен быть в шаблоне для всех будущих API. → создать `feedback_public_api_needs_ratelimit.md`
- **Anthropic API нестабильно (12.05)** — 4 фоновых агента упали ECONNRESET за сессию. Если несколько подряд — пауза 30 мин.
- **Python `len(string)` ≠ `wc -c` для UTF-8** — для сравнения local vs prod использовать MD5, не размеры в байтах.

## 🔜 Следующие шаги (приоритет)

### 1. 🔴 HIGH — rate-limit на /api/kp-message.php

**Готовый PHP-код:**
```php
<?php
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
header("Content-Type: application/json");
if ($_SERVER["REQUEST_METHOD"] === "OPTIONS") exit;

$ip = preg_replace("/[^0-9a-f.:]/i", "",
    explode(",", $_SERVER["HTTP_X_FORWARDED_FOR"] ?? $_SERVER["REMOTE_ADDR"])[0]);

// Rate-limit: 5 req / 60 sec
$lock = "/tmp/kp-rate-" . md5($ip) . ".log";
$now = time();
$hits = file_exists($lock)
  ? array_filter(explode("\n", file_get_contents($lock)), fn($t) => (int)$t > $now - 60)
  : [];
if (count($hits) >= 5) {
    http_response_code(429);
    echo json_encode(["ok" => false, "err" => "rate_limit", "retry_after" => 60]);
    exit;
}
$hits[] = $now;
file_put_contents($lock, implode("\n", $hits));

// Daily cap: 50 req/IP/day
$daily = "/tmp/kp-daily-" . md5($ip) . "-" . date("Ymd") . ".cnt";
$count = file_exists($daily) ? (int)file_get_contents($daily) : 0;
if ($count >= 50) {
    http_response_code(429);
    echo json_encode(["ok" => false, "err" => "daily_limit"]);
    exit;
}
file_put_contents($daily, $count + 1);

$input = json_decode(file_get_contents("php://input"), true);
$q = trim($input["question"] ?? "");
$url = trim($input["kp_url"] ?? "");
if ($q === "") { echo json_encode(["ok" => false, "err" => "empty"]); exit; }
if (mb_strlen($q) > 2000) $q = mb_substr($q, 0, 2000) . "…";

$qSafe = htmlspecialchars($q, ENT_QUOTES, "UTF-8");
$urlSafe = htmlspecialchars($url, ENT_QUOTES, "UTF-8");

$token = "ВЗЯТЬ_ИЗ_СУЩЕСТВУЮЩЕГО_ФАЙЛА";  // см. шаги ниже
$chatId = "161261562";
$text = "💬 <b>Вопрос с КП</b>\n\n{$qSafe}\n\n📄 {$urlSafe}\n🌐 IP: {$ip}";

$ch = curl_init("https://api.telegram.org/bot{$token}/sendMessage");
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POSTFIELDS => json_encode(["chat_id" => $chatId, "text" => $text, "parse_mode" => "HTML"]),
    CURLOPT_HTTPHEADER => ["Content-Type: application/json"],
    CURLOPT_TIMEOUT => 5,
]);
curl_exec($ch);
$code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);
echo json_encode(["ok" => $code === 200]);
```

**Деплой:**
```bash
ssh root@80.90.181.152
cp /var/www/artvision/api/kp-message.php /var/www/artvision/api/kp-message.php.bak
# Извлечь существующий токен (НЕ затирать):
grep -oE "70[0-9]+:[A-Za-z0-9_-]+" /var/www/artvision/api/kp-message.php | head -1
# Открыть редактор, вставить код выше, подставить $token
nano /var/www/artvision/api/kp-message.php
```

**Тест после деплоя:**
```bash
for i in 1 2 3 4 5 6 7; do
  curl -sX POST https://artvision.pro/api/kp-message.php \
    -H "Content-Type: application/json" \
    -d '{"question":"rt'$i'","kp_url":"x"}' -w " [HTTP %{http_code}]\n"
done
# Ожидание: req 1-5 = HTTP 200, req 6-7 = HTTP 429
```

### 2. MEDIUM — собрать прямых конкурентов для cos + hair
Topvisor проект уже есть (28362497). Добавить 3 ключа cos и 3 hair → snapshot → если кто-то встречается ≥3 ключа в ТОП-10 = главный конкурент. Применить в #backlinks их КП. Алгоритм описан в `~/.claude/rules/competitor-selection.md`.

### 3. MEDIUM — вынести rate-limit helper
`/var/www/artvision/api/_lib/rate_limit.php` → подключать через `include` в новых endpoints.

### 4. LOW — reusable JS tg-popup.js
`https://artvision.pro/js/tg-popup.js?bot=avportal&chat=161261562` — заменить inline JS в 3 КП на одну `<script>` строку.

### 5. LOW — health-check cron
Curl каждые 5 мин на `/api/kp-message.php` (OPTIONS) → если не 200 → TG alert в @avportal_bot 161261562.

### 6. LOW — E2E Playwright TG-popup тесты
Mobile 375px viewport + fallback на TG share dialog при backend down.

## 🗺️ Карта файлов

```
/Users/antonk/artvision-data/
├── presales/
│   ├── spb-kursy/kp/spb-kursy_kp_v3.html              ← prod
│   ├── cosmetology-kursy/kp/cosmetology-kursy_kp_v3.html ← prod
│   └── hair-courses/kp/hair-courses_kp_v3.html        ← prod
├── clients/spb-kursy/seo/2026-05-11/
│   ├── topvisor-positions.json                        ← позиции 20 ключей
│   ├── direct-forecast-{commercial,informational}.json ← Wordstat-прокси
│   ├── backlinks/semrush-*.json                       ← 4 домена SEMrush
│   └── (CSV 7 точных частот в /tmp/wordstat-spb-30.csv)
├── templates/audit-kp-template.html                    ← 276 KB шаблон
└── scripts/seo/content_volume_benchmark.py             ← word count vs ТОП-10

VPS 80.90.181.152:
└── /var/www/artvision/api/kp-message.php               ← BACKEND, нужен rate-limit

~/.claude/
├── rules/audit-kp-pipeline.md                          ← 12-шаговый pipeline
├── rules/competitor-selection.md                       ← новое правило
├── rules/self-corrections.md                           ← #15, #16 добавлены
├── skills/audit-kp/SKILL.md                            ← /audit-kp <url>
├── handovers/HANDOVER-2026-05-12-0140-presale-kursy.md ← этот файл
└── hooks/pre-kp-*, stop-claim-no-rule-check.sh         ← защитные хуки

Связанная сессия (не блокер для kursy):
~/artvision-data-orchestrator-week1/  ← worktree, бранч feat/orchestrator-week1
```

## ⚠️ Гачи

- **Token VPS:** `grep -oE "70[0-9]+:[A-Za-z0-9_-]+"` в существующем `kp-message.php` — НЕ затирать при правке rate-limit
- **CDN/cache:** Browser кешит CSS — после deploy дай Антону Cmd+Shift+R
- **Хуки в сессии 0% контекста** блокируют почти все Bash/Edit — лучше начать новую сессию для критичных правок
- **Anthropic API нестабильно (12.05)** — 4 фоновых агента упали ECONNRESET. Не запускать рои подряд, пауза между.
- **`scp # --ack-anton`** — bash comment, иначе попадает в имя файла на VPS (был такой косяк сегодня)
- **Python `len(string)` ≠ `wc -c`** для UTF-8 — для сравнения local vs prod использовать MD5
- **shkolamm = конкурент только spb-kursy**, для cos/hair прямые конкуренты не собраны (оговорено в КП «соберём в 1-ю неделю работ»)
- **Audio/video кружки** — Антон собирался записать сам, не успел; вернуться при follow-up
- **Wordstat exact** — у нас 7/20 точных из CSV 08.05 + 13 прокси × 1.15 коэф; 13 пропущенных нужны Я.ID логин
- **Антон ловит галлюцинации** — каждое число с источником (Direct API / Topvisor / SEMrush / Wordstat CSV дата). Без — strict-factchecker завернёт.

## 🔗 Связанные ресурсы

- Backend на VPS: `ssh root@80.90.181.152` → `/var/www/artvision/api/kp-message.php`
- TG бот: @avportal_bot, chat_id 161261562 (Антон)
- Topvisor проект: id=28362497 (Я.СПб lr=2)
- SEMrush: креды в `~/artvision-data/tokens.json` → `semrush` (kulikov.v.art@gmail.com)
- Wordstat workaround reference: `~/.claude/projects/-Users-antonk/memory/reference_artvision_api_access_status_2026-05-11.md`
- Связанная сессия: ORCHESTRATOR (805da82f) — Tasks 3-5 закрыты, hook subagent-driven не закоммичен в `~/claude-code-settings/`
- Pending TaskList: #1 Tests TG-popup KP backend + frontend, #2 FIX rate-limiting

## 📋 Промпт для новой сессии

```
Подними handover ~/.claude/handovers/HANDOVER-2026-05-12-0140-presale-kursy.md
и сделай шаги 1-5 из «Следующие шаги».

Критично сейчас — шаг 1 (rate-limit). Готовый PHP в handover, деплой через SSH на root@80.90.181.152.
После деплоя — тест 7 curl POST подряд → 6-й должен вернуть 429.

Затем: шаг 2 (конкуренты cos+hair через Topvisor), шаг 3 (helper),
шаги 4-5 — автоматизации, не блокеры.

3 финальных URL КП:
- https://artvision.pro/kp/spb-kursy-v3/
- https://artvision.pro/kp/cosmetology-kursy-v3/
- https://artvision.pro/kp/hair-courses-v3/
```
