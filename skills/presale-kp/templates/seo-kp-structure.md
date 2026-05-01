# Структура развёрнутого SEO-КП (15 разделов)

> Источник: na-sklad.ru, 2026-05-01. Для коммерческих SEO-проектов с большим аудитом.
> Простые лендинги — использовать Вариант A (10 секций) из SKILL.md.

## Скелет HTML

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow">
  <title>{{client_domain}} × Artvision — SEO/GEO-аудит и план роста</title>
  <style>
    /* Цвета: PRIMARY=#2c3e88, DANGER=#c92533, WARN=#d97706, GREEN=#15803d */
    /* (вставить mobile-responsive.css) */
  </style>
</head>
<body>
  <div class="kp-document">

    <!-- 1. HERO + score-плашка -->
    <section class="hero" id="hero">
      <h1>{{client}} × Artvision — SEO/GEO-аудит и план роста</h1>
      <div class="hero-score">{{audit_score}} / 100</div>
      <div class="hero-metrics">{{4 KPI-плашки}}</div>
    </section>

    <!-- 2. TOC С ГРУППАМИ — см. grouped-toc.html -->

    <!-- 3. Раздел 1 — Три красных флага -->
    <section class="kp-page-dark" id="flags">…</section>

    <!-- 4. Раздел 2 — Сводный балл сайта (8 проверенных блоков) -->
    <section class="kp-page" id="audit">…</section>

    <!-- 5. Раздел 3 — Видимость в поиске (ТОП-10 по N запросам региона) -->
    <section class="kp-page" id="serp">…</section>

    <!-- 6. Раздел 4 — Технические находки (CRITICAL/HIGH/MEDIUM) -->
    <section class="kp-page" id="tech">…</section>

    <!-- 7. Раздел 5 — Цена в рынке (только для коммерческих ниш) -->
    <section class="kp-page" id="price">…</section>

    <!-- 8. Раздел 6 — Конкуренты для бенчмарка -->
    <section class="kp-page" id="competitors">…</section>

    <!-- 9. Раздел 7 — Маркетплейсы / отраслевая ниша (если применимо) -->
    <section class="kp-page" id="mp">…</section>

    <!-- 10. Раздел 8 — NAP и каталоги -->
    <section class="kp-page" id="nap">…</section>

    <!-- 11. Раздел 9 — Видимость в генеративном поиске + ЕГРЮЛ -->
    <section class="kp-page-dark" id="ai">…</section>

    <!-- 12. Раздел 9.5 — СВОДНЫЙ SEO-АУДИТ pulse-радар + графики + «Суть аудита» -->
    <section class="kp-page" id="audit-full">
      {{traffic.png}}
      {{pulse-radar.png + 4 модуля}}
      {{sitemap-diff.png}}
      {{table разрывов}}
      {{backlinks.png}}
      {{audit-summary-box.html}}  <!-- ОБЯЗАТЕЛЬНО -->
    </section>

    <!-- 13. Раздел 10 — Распределение работ 3/6/12 мес — horizons-3-6-12.html -->
    <section class="kp-page" id="plan">…</section>

    <!-- 14. Раздел 11 — Два формата сотрудничества (95К + 70К/мес) -->
    <section class="kp-page" id="tariffs">…</section>

    <!-- 15. KPI + следующий шаг -->
    <section class="kp-page" id="kpi">…</section>
    <section class="cta-block" id="next">…</section>

    <footer class="kp-footer">…</footer>
  </div>

  <!-- Вставить chat-widget.html (виджет с менеджером) -->
  <!-- Вставить mini-toc.html (sticky навигация ≥1024px) -->
</body>
</html>
```

## Группы TOC

```
АУДИТ И ДИАГНОСТИКА
  - Три красных флага
  - Сводный балл /100
  - Видимость в поиске
  - Технические находки
  - Цена в рынке
  - Конкуренты для бенчмарка
  - Маркетплейс-ниша
  - NAP и каталоги
  - Видимость в генеративном поиске + ЕГРЮЛ

СТРАТЕГИЯ SEO
  - Полный SEO-аудит: XX,X / 100
  - Распределение работ 3 / 6 / 12 месяцев

КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ
  - Форматы сотрудничества
  - Инструменты, которыми работаем
  - KPI на 3/6/12 месяцев
  - Следующий шаг
```

## Связь с партиалами

| Раздел | Партиал |
|--------|---------|
| TOC | `grouped-toc.html` |
| Глобальный CSS | `mobile-responsive.css` |
| Графики | `gen-charts.py` → 4 PNG в `img/` |
| Pulse-радар плашка | `pulse-radar-block.html` |
| Раздел 12 «Суть аудита» | `audit-summary-box.html` |
| Раздел 13 Горизонты | `horizons-3-6-12.html` |
| Виджет чата | `chat-widget.html` |
| Sticky TOC | `mini-toc.html` |
| Карта замен резких слов | `soften-language.json` |

## Цены

**С 2026-05-01 — 2 формата** (не 3 тарифа):
- 95 000 ₽ одноразово — «План и рекомендации»
- 70 000 ₽/мес — «Полное сопровождение» (план 95К включён)

Цена согласовывается с Антоном до отправки (правило `feedback_pricing_by_revenue.md`: 0,5–1,5% от годовой выручки клиента).
