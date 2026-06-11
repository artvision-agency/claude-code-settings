# Mobile-first — ВСЕГДА, для ВСЕХ HTML (не только КП)

> **Установлено:** 2026-06-01 (Антон: «всегда mobile first»). Sync на 3 аккаунта через git (дубль в artvision-data/.claude/rules/).
> **Расширяет** `kp-brand.md` (там mobile-first только для КП) — теперь на ЛЮБОЙ HTML: КП, дашборды, review-страницы, гайды, отчёты, планы, лендинги, внутренние документы.
> **Связано:** `html-clients.md`, `kp-brand.md`, `feedback_kp_mobile_first_design.md`.

## Правило (HARD)

Любой HTML, который генерит Claude — проектируется **от мобильного (320/375/414) → расширение под desktop**. БЕЗ исключений.

## Чеклист (каждый HTML)

- `<meta name="viewport" content="width=device-width, initial-scale=1.0">` — обязательно
- CSS: **`@media (min-width: ...)`** для расширений вверх. **НЕ `@media (max-width: ...)`** (это desktop-first).
- Базовые стили (вне @media) = мобильная версия. Десктоп — добавляется в min-width брейкпоинтах.
- Таблицы: `overflow-x:auto` + min-width на таблице ИЛИ карточки на mobile (таблица не должна рвать вёрстку на 320).
- Touch targets ≥44×44px (все ссылки/кнопки, включая футер).
- Body font ≥16px на mobile.
- Hero/ключевой контент виден выше fold на 375 без скролла.
- Горизонтальный скролл на 320 = БАГ.

## Проверка перед «готово»

```bash
grep -oc 'min-width' file.html   # должно быть > 0
grep -oc 'max-width' file.html   # для брейкпоинтов — 0 (max-width допустим ТОЛЬКО для max-width картинок/контейнера, не для @media-логики)
```
Если @media построены на max-width → переписать на min-width.

## Антипаттерны

- ❌ Верстать на 1440 → потом «как-нибудь подожмётся» на mobile
- ❌ `@media (max-width: 768px)` как основа адаптива (desktop-first)
- ❌ Таблица фиксированной ширины без overflow-x на mobile
- ❌ Считать «есть viewport meta = mobile-first» (это не одно и то же — нужен min-width-подход)

## Прецедент

- **2026-06-01:** Антон «всегда mobile first». `standup-FINAL.html` вышел смешанным (2 min + 2 max-width @media). Правило поднято из КП-частного в глобальное для всех HTML.
