---
name: pbn-domains
description: "PBN domain system: find expired domains, check history, buy at auction, build PBN networks for clients. Revenue upsell 30-80K/client/month. Triggers: 'pbn', 'дроп домен', 'expired', 'домен аукцион', 'сетка', 'pbn сетка', 'линкбилдинг домены'"
argument-hint: "[action: search|check|buy|propose-client|niche-eval|telderi]"
---

# /pbn-domains — PBN Domain System

## REVENUE IMPACT

| Услуга | Чек клиенту | Себестоимость | Маржа |
|--------|-------------|---------------|-------|
| Подбор дроп-доменов (10 шт) | 15-30K | 3-5K (домены) | 80%+ |
| Развёртывание PBN (5 сайтов) | 50-100K разово | 10-20K | 70%+ |
| Обслуживание PBN/мес | 30-80K/мес | 5-15K | 70%+ |
| Линкбилдинг с PBN/мес | 20-50K/мес | 0 (свои сайты) | 90%+ |

**Потенциал:** +30-80K/мес с КАЖДОГО SEO-клиента = +150-400K/мес на 5 клиентах.

## WORKFLOW

```
SEARCH → CHECK → BUY → DEPLOY → SELL
  │         │       │       │       │
  expired   archive auction hosting upsell
  reg.ru    whois   reg.ru  VPS     КП
  webnames  ahrefs  expired WP      клиенту
```

## STEP 1: Search — Поиск дроп-доменов

### Источники

| Площадка | URL | Что даёт | Цена |
|----------|-----|----------|------|
| **expired.ru** | expired.ru | Аукцион .ru/.рф, перехват | от 249₽ |
| **Reg.ru аукцион** | reg.ru/domain/new/rereg | Освобождающиеся .ru/.рф/.su | от 300₽ |
| **Webnames** | webnames.ru/domains/deleted | Удалённые домены | рег. цена |
| **ExpiredDomains.net** | expireddomains.net | Международные TLD | бесплатно |
| **Dynadot** | dynadot.com/market/auction | Международные аукционы | от $1 |
| **xpire.ru** | xpire.ru | Поиск дропов с фильтрами, бэклинки, DR | Аккаунт Антона |
| **Telderi** | telderi.ru | Аукцион готовых сайтов и доменов | от 100₽ |

### Telderi — анализ ниш
```
1. WebSearch: "site:telderi.ru [ниша]" — что продают
2. Оценить: трафик, цена, бэклинки, возраст
3. Если трафик из Google коммерческий → покупать дроп
4. Если трафик информационный → делать страницу на artvision.pro
```

### xpire.ru — поиск дропов
У Антона есть аккаунт. Использовать для:
- Фильтры по DR, бэклинкам, возрасту, тематике
- Мониторинг освобождающихся доменов по ключевым словам
- Экспорт кандидатов в CSV для дальнейшей проверки

### Критерии поиска (для SEO)

```python
CRITERIA = {
    "min_age": 3,           # лет
    "min_backlinks": 10,    # referring domains
    "max_spam_score": 30,   # Moz Spam Score
    "min_da": 15,           # Domain Authority (Moz) или DR (Ahrefs)
    "no_history": [         # НЕ должно быть в истории
        "casino", "porn", "pharma", "spam",
        "redirect", "parking", "chinese"
    ],
    "tld": [".ru", ".рф", ".com", ".net"],
    "max_price": 5000,      # руб за домен
}
```

### Автоматизация поиска

**Playwright → expired.ru:**
```
1. Открыть expired.ru
2. Фильтры: зона .ru, возраст >3 года, ТИЦ >0
3. Парсить таблицу: домен, возраст, ТИЦ, free-date, цена
4. Сохранить в CSV
```

**Playwright → reg.ru/domain/new/rereg:**
```
1. Открыть аукцион
2. Фильтры: .ru, цена до 5000₽
3. Парсить: домен, текущая ставка, дата освобождения
```

## STEP 2: Check — Проверка домена

Для каждого кандидата — 5 проверок:

### 2.1 Wayback Machine (история)

```python
# API: бесплатно, без ключа
import requests

def check_wayback(domain):
    # Получить все снапшоты
    url = f"https://web.archive.org/cdx/search/cdx?url={domain}&output=json&fl=timestamp,statuscode&limit=50"
    resp = requests.get(url)
    snapshots = resp.json()

    # Первый и последний снапшот
    first = snapshots[1][0]  # YYYYMMDDHHMMSS
    last = snapshots[-1][0]

    # Проверить контент последнего снапшота
    preview_url = f"https://web.archive.org/web/{last}/{domain}"
    return {
        "first_seen": first[:4],
        "last_seen": last[:4],
        "total_snapshots": len(snapshots) - 1,
        "preview": preview_url
    }
```

**Красные флаги в истории:**
- Редиректы на спам-сайты
- Китайский/арабский контент (парковка)
- Казино/фарма/порно
- Пустая страница >2 лет (parking)
- Резкая смена тематики

### 2.2 Бэклинк-профиль

Проверить через:
- **Ahrefs** (если есть доступ) — DR, referring domains, anchors
- **Serpstat** — бесплатный лимит
- **Majestic** — TF/CF
- **Moz** — DA/PA/Spam Score

### 2.3 Индексация

```bash
# Проверить наличие в индексе Яндекс/Google
site:domain.ru
```

Если домен ещё в индексе — БОНУС (быстрее подхватится).

### 2.4 Whois история

Проверить сколько раз менял владельца. Частая смена = подозрительно.

### 2.5 Тематическое соответствие

Домен должен быть релевантен тематике клиента:
- Юристы (ANT) → правовые, юридические домены
- Стоматология (Творим) → медицинские, здоровье
- Строительство (Otido) → строительные, ремонтные

### Итоговый скоринг

```
SCORE = (age * 2) + (backlinks * 3) + (da * 2) - (spam * 5)

GREEN (>50): покупать
YELLOW (30-50): проверить вручную
RED (<30): пропустить
```

## STEP 3: Buy — Покупка

### На expired.ru
```
Playwright:
1. Авторизоваться
2. Найти домен → "Сделать ставку"
3. Поставить сумму (обычно 249-2000₽)
4. Скриншот → подтверждение Антона (🔴 CONFIRM — платная операция)
5. После "го" → подтвердить ставку
```

### На reg.ru
```
Playwright:
1. Авторизоваться
2. Аукцион → найти домен
3. Поставить ставку
4. Скриншот → подтверждение (🔴 CONFIRM)
5. Подтвердить
```

### Бюджет

| Количество | Домены | Хостинг/год | Контент | Итого |
|------------|--------|-------------|---------|-------|
| 5 доменов | 1.5-10K | 3-6K | 5-15K | ~15-30K |
| 10 доменов | 3-20K | 6-12K | 10-30K | ~20-60K |
| 20 доменов | 6-40K | 12-24K | 20-60K | ~40-120K |

## STEP 3.5: Restore — Восстановление сайта из Wayback Machine

### Зачем
Купленный дроп-домен имеет бэклинки → но они ведут на 404. Восстановив оригинальный контент — бэклинки снова передают вес. Это КЛЮЧЕВОЕ преимущество дропов перед новыми доменами.

### Инструменты

| Инструмент | Команда | Что делает |
|------------|---------|-----------|
| **wayback-machine-downloader** | `gem install wayback_machine_downloader` | Полное зеркало сайта одной командой |
| **waybackpy** | `pip install waybackpy` | Python API — список URL, снапшоты, CDX |
| **CDX API** | `curl "web.archive.org/cdx/search/cdx?url=domain.ru/*"` | Все URL + даты |

### Процесс восстановления

```bash
# 1. Скачать полный архив сайта
wayback_machine_downloader https://domain.ru -d ./restored-domain

# 2. Если wayback_machine_downloader недоступен — Python:
python3 <<'PYEOF'
import requests, os, time
from urllib.parse import urlparse

domain = "domain.ru"
# Получить все URL из CDX
cdx = requests.get(
    f"https://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&fl=timestamp,original&collapse=urlkey&limit=500"
).json()

os.makedirs("restored", exist_ok=True)
for ts, url in cdx[1:]:  # skip header
    wb_url = f"https://web.archive.org/web/{ts}id_/{url}"
    path = urlparse(url).path.strip("/") or "index.html"
    try:
        resp = requests.get(wb_url, timeout=10)
        filepath = f"restored/{path}"
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(resp.content)
        time.sleep(0.5)  # не DDoS-ить архив
    except Exception as e:
        print(f"Skip {url}: {e}")
PYEOF

# 3. Очистить от мусора Wayback
# - Удалить toolbar Wayback Machine из HTML
# - Заменить web.archive.org ссылки на оригинальные
# - Удалить старые счётчики (GA, Метрика, LiveInternet)
# - Починить битые картинки (base64 или заменить)

# 4. Залить на хостинг
scp -r restored/ user@vps:/var/www/domain.ru/
```

### Что чистить после восстановления
- `<!-- BEGIN WAYBACK TOOLBAR INSERT -->` блоки
- `web.archive.org/web/` в URL ссылок и картинок
- Старые `<script>` счётчиков (GA UA-*, Метрика старая)
- Невалидный HTML (doctype, charset)
- Битые внешние ресурсы (CDN, шрифты)

### Автоматизация через Claude
```
/pbn-domains restore domain.ru
→ 1. CDX API: получить список всех страниц
→ 2. Скачать последние версии каждой
→ 3. Очистить от Wayback мусора
→ 4. Сгенерировать недостающий контент через /content-writer
→ 5. Залить на VPS
→ 6. Проверить что бэклинки ведут на живые страницы
```

## STEP 4: Deploy — Развёртывание PBN

### Правила безопасного PBN
1. **Разные хостинги** — не все домены на одном VPS
2. **Разные IP** — минимум разные подсети (/24)
3. **Разный CMS** — WordPress, Hugo, Ghost, статика
4. **Уникальный контент** — не копипаст, не спин
5. **Разные Whois** — privacy protection
6. **Разные GA/Метрика** — или вообще без них
7. **Естественный вид** — не только ссылки на клиента

### Структура каждого PBN-сайта
```
domain.ru/
├── 5-10 статей (уникальные, по тематике)
├── Главная (информационная)
├── О сайте / Контакты
├── 1-2 ссылки на клиента (в контенте, естественно)
└── 3-5 ссылок на авторитетные источники (Wikipedia, gov.ru)
```

### Автоматизация (Claude)
- Генерация контента через /content-writer (без упоминания AI!)
- Установка WordPress через WP-CLI на VPS
- Настройка темы, SSL, robots.txt
- Размещение статей через WP REST API (/wp-rest-api)

## STEP 5: Sell — Продажа клиенту

### Позиционирование (НЕ "PBN"!)

**ТАБУ:** НЕ говорить клиенту "PBN", "сетка сателлитов", "дроп-домены"

**Как продаём:**
- "Тематическая сеть партнёрских ресурсов"
- "Контентные площадки для естественного линкбилдинга"
- "Стратегия укрепления ссылочного профиля"
- "Авторитетные тематические ресурсы"

### Пакеты для клиентов

| Пакет | Доменов | Ссылок/мес | Разово | Ежемесячно |
|-------|---------|------------|--------|------------|
| Starter | 3 | 3-5 | 30K | 15K/мес |
| Growth | 5 | 8-12 | 50K | 30K/мес |
| Authority | 10 | 15-25 | 80K | 50K/мес |
| Enterprise | 20 | 30-50 | 150K | 80K/мес |

### КП интеграция

При запуске /presale-kp для SEO-клиента — АВТОМАТИЧЕСКИ предлагать пакет PBN как upsell:
```
Дополнительно рекомендуем:
📈 Стратегия укрепления ссылочного профиля
• 5 тематических партнёрских ресурсов
• 8-12 естественных ссылок в месяц
• Рост DR/DA на 5-10 пунктов за 3 месяца
• 50,000 ₽ разово + 30,000 ₽/мес
```

## STEP 6: Monitoring — Мониторинг PBN

Регулярные проверки:
- Домены не деиндексированы
- SSL не протух
- Контент на месте
- Ссылки живые
- Нет ручных фильтров

## AUTOMATION COMMANDS

```
/pbn-domains search "юридическая тематика" 10
→ Ищет 10 дроп-доменов по юр. тематике

/pbn-domains check domain.ru
→ Полная проверка домена (Wayback + бэклинки + спам)

/pbn-domains buy domain.ru
→ Playwright → аукцион → покупка (🔴 CONFIRM)

/pbn-domains propose-client ant-partners
→ Генерирует предложение PBN для клиента ANT Partners

/pbn-domains status
→ Статус всех PBN доменов (индексация, ссылки, здоровье)
```

## DATA FILES

| Файл | Содержимое |
|------|-----------|
| `artvision-data/pbn/domains.json` | Купленные домены, статусы |
| `artvision-data/pbn/candidates.json` | Кандидаты на покупку |
| `artvision-data/pbn/clients.json` | Какому клиенту какие домены |
| `artvision-data/pbn/monitoring.json` | Результаты мониторинга |

## RULES

1. **Покупка домена = 🔴 CONFIRM** — всегда подтверждение + показать стоимость
2. **Контент на PBN** — ТОЛЬКО уникальный, генерить через /content-writer
3. **Никогда** не упоминать "PBN" или "сателлиты" в документах клиенту
4. **Разнообразие** — разные хостинги, IP, CMS, Whois
5. **Одна ссылка на клиента** на один PBN-сайт (не 10 ссылок)
6. **Мониторинг** — еженедельно проверять индексацию и здоровье
7. **ROI** — отслеживать рост DR/DA клиента после запуска PBN
