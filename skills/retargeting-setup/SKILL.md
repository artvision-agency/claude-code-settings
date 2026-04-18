---
name: retargeting-setup
description: "Настройка, аудит и оптимизация ретаргетинга через Яндекс Метрику и Яндекс Директ. Триггеры: ретаргетинг, ремаркетинг, сегменты Метрики, РСЯ чистка, исключения площадок, look-alike, отказники, negative audiences, чистая аудитория, audience optimizer, retargeting."
---

# Retargeting Setup & Audience Optimizer

Ты senior performance-маркетолог с доступом к API Яндекс Метрики и Директа.
Задача: настроить ретаргетинг для клиента Artvision — чистые сегменты, исключение мусора, условия ретаргетинга, мониторинг.

## Требования

### Доступы (проверить tokens.json ПЕРВЫМ)

| Что | Ключ в tokens.json | Проверка |
|-----|-------------------|----------|
| OAuth Метрики | `yandex.metrika.token` | `curl -s -H "Authorization: OAuth TOKEN" "https://api-metrika.yandex.net/management/v1/counters"` |
| ID счётчика | `clients/[name]/config.yaml` | Числовой ID |
| OAuth Директа | `yandex.direct.[account].token` | GET campaigns |
| Login Директа | `yandex.direct.[account].login` | Для агентских аккаунтов |

**Нет доступа → Asana задача "Получить доступ к Метрике/Директу клиента [name]".**

---

## Фаза 1: Аудит (день 1)

### 1.1 Текущие сегменты Метрики
```bash
curl -s -H "Authorization: OAuth $METRIKA_TOKEN" \
  "https://api-metrika.yandex.net/management/v1/counter/$COUNTER_ID/apisegment/segments" \
  | python3 -m json.tool
```

### 1.2 Условия ретаргетинга в Директе
```bash
curl -s -X POST -H "Authorization: Bearer $DIRECT_TOKEN" -H "Client-Login: $LOGIN" \
  -d '{"method":"get","params":{"SelectionCriteria":{},"FieldNames":["Id","Name","Rules"]}}' \
  "https://api.direct.yandex.com/json/v5/retargetinglists"
```

### 1.3 Цели Метрики
```bash
curl -s -H "Authorization: OAuth $METRIKA_TOKEN" \
  "https://api-metrika.yandex.net/management/v1/counter/$COUNTER_ID/goals" | python3 -m json.tool
```

### 1.4 Площадки РСЯ с bounce >80%
```bash
curl -s -H "Authorization: OAuth $METRIKA_TOKEN" \
  "https://api-metrika.yandex.net/stat/v1/data?ids=$COUNTER_ID&metrics=ym:ad:visits,ym:ad:bounceRate&dimensions=ym:ad:directPlatform&date1=90daysAgo&date2=today&sort=-ym:ad:visits&limit=50"
```

### 1.5 Записать аудит
`clients/[name]/retargeting/audit-YYYY-MM-DD.md`

---

## Фаза 2: Создание сегментов (день 2)

### Обязательные сегменты

| Сегмент | Expression (API) | Назначение |
|---------|-----------------|------------|
| Все посетители (30/90/180/540д) | `ym:s:isNewUser=='Yes' OR ym:s:isNewUser=='No'` | Базовая аудитория |
| Конвертировавшиеся | `ym:s:goal{GOAL_ID}IsReached=='Yes'` | ИСКЛЮЧЕНИЕ |
| Отказники | `ym:s:pageViews==1` | ИСКЛЮЧЕНИЕ |
| Нерелевантный реферал | `ym:s:referer=@'trash-site.ru'` | ИСКЛЮЧЕНИЕ |

### API создания
```bash
curl -s -X POST -H "Authorization: OAuth $METRIKA_TOKEN" -H "Content-Type: application/json" \
  -d '{"segment":{"name":"Retarget: Отказники (исключ.)","expression":"ym:s:pageViews==1"}}' \
  "https://api-metrika.yandex.net/management/v1/counter/$COUNTER_ID/apisegment/segments"
```

**Лимит:** 500 API-сегментов на счётчик. API-сегменты НЕ видны в веб-интерфейсе.

### Автоматизация
Скрипт: `scripts/retargeting/create_metrika_segments.py`
- `--counter-id 12345 --goal-id 87654` — полное создание
- `--audit-only` — только аудит
- `--dry-run` — показать что будет создано

---

## Фаза 3: Директ (день 3-4)

### 3.1 Условие "Чистая аудитория"

```json
{
  "method": "add",
  "params": {
    "RetargetingLists": [{
      "Name": "Чистая аудитория (без конверсий и отказов)",
      "Rules": [
        {"Operator": "ALL", "Goals": [{"GoalId": SEGMENT_ALL, "GoalType": "SEGMENT", "MembershipLifeSpan": 30}]},
        {"Operator": "NONE", "Goals": [{"GoalId": GOAL_CONVERTED, "GoalType": "GOAL", "MembershipLifeSpan": 540}]},
        {"Operator": "NONE", "Goals": [{"GoalId": SEGMENT_BOUNCE, "GoalType": "SEGMENT", "MembershipLifeSpan": 30}]}
      ]
    }]
  }
}
```

**Логика:** ALL/ANY = включение, NONE = исключение. Группы связаны AND.
**Лимиты:** 2000 условий на аккаунт, 50 правил в условии, 250 целей в правиле.

### 3.2 Корректировка -100% для negative

```json
{"method": "add", "params": {"BidModifiers": [{"CampaignId": CAMP_ID,
  "RetargetingAdjustments": [{"RetargetingConditionId": COND_ID, "BidModifier": 0}]}]}}
```

`BidModifier: 0` = -100% (полное исключение), `50` = -50%, `1300` = +1200%.

### 3.3 Рекомендуемые ставки

| Сегмент | Корректировка | CPC ожидаемый |
|---------|--------------|---------------|
| Калькулятор-юзеры 0-7д | +100-200% | 10-20 руб |
| Посетители 0-7д | +50% | 8-15 руб |
| Посетители 7-30д | Базовая | 5-10 руб |
| Посетители 30-90д | -20% | 4-8 руб |
| LAL точность 5 | -30% | 3-7 руб |
| Отказники | -100% | Исключены |
| Конвертировавшиеся | -100% | Исключены |

### 3.4 Временные окна (от N до M дней)

Набор 1: сегмент M дней (ANY) + Набор 2: сегмент N дней (NONE) = аудитория N-M дней.

---

## Фаза 4: Мониторинг (еженедельно)

### KPI

| Метрика | Цель | Алерт |
|---------|------|-------|
| CPC | 2-10 руб | >15 руб |
| CTR | >0.3% | <0.1% |
| Отказы | <20% | >30% |
| CR | >1% | <0.3% |
| Частота показов | 3-5/нед | >10 |

### Еженедельные действия

- [ ] Проверить площадки, исключить мусорные (bounce >60%)
- [ ] Обновить negative-сегменты (новые отказники)
- [ ] Проверить CPC по группам
- [ ] Обновить креативы (каждые 1-3 мес)

### Чистка площадок

Критерии блокировки: bounce >60% (при >20 кликов), CTR >5% (фрод), 0 конверсий при расходе >2xCPA.
Лимит: 1000 запрещённых доменов на кампанию.

---

## Чеклист (полный)

### Фаза 1: Аудит
- [ ] tokens.json → доступы Метрика + Директ
- [ ] Список сегментов Метрики
- [ ] Условия ретаргетинга Директа
- [ ] Цели Метрики (конверсионные)
- [ ] Топ-50 площадок РСЯ → кандидаты на исключение
- [ ] Аудит в `clients/[name]/retargeting/audit-*.md`

### Фаза 2: Сегменты
- [ ] "Все посетители" (30/90/180/540д)
- [ ] "Конвертировавшиеся" (исключение)
- [ ] "Отказники" (исключение)
- [ ] "Нерелевантный реферал" (исключение)
- [ ] Сохранить segment_id

### Фаза 3: Директ
- [ ] RetargetingList "Чистая аудитория"
- [ ] Look-alike в Яндекс Аудиториях
- [ ] Привязать к РСЯ-кампаниям
- [ ] Настроить ставки + корректировки
- [ ] Креативы (3-5 вариантов по теплоте)

### Фаза 4: Мониторинг
- [ ] Еженедельный отчёт (cron)
- [ ] Чек через 7 дней
- [ ] Обновить negative-сегменты
- [ ] Метрики в ежемесячный отчёт клиенту

---

## Связанные скиллы

- `paid-ads` — общая стратегия платной рекламы
- `analytics-tracking` — настройка целей
- `cro` — оптимизация конверсии лендингов
- `seo-master` — SEO для EMD-сети (источник бесплатного трафика)

## Частые ошибки

| Ошибка | Решение |
|--------|---------|
| Ретаргетинг на ВСЕХ без исключений | Всегда исключать converted + bounce |
| Одно окно 30 дней | 4 окна с разными ставками |
| Нет чистки площадок | Еженедельно! 50%+ бюджета уходит в мусор |
| Одинаковые креативы | Разные по теплоте аудитории |
| Нет frequency cap | Макс 3-5 показов/неделю |
