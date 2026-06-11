# SEMrush — операции (консолидированный ops-гайд)

> Свод операций SEMrush + грабли. Скрипты: `scripts/semrush_top_pages.py`, `semrush_backlink_gap.py`, `semrush_doctra_toolgrade.py`.
> **Связано:** `/seo-master` ШАГ 6 (анализ конкурентов), `seo-presale-audit-workflow.md` Шаг 5.

## Доступ
`tokens.json → semrush {email, password, note}` — **НЕ API-ключ, а Playwright-сессия** (логин email+пароль через браузер). Скрипты «session-first»: пробуют активную сессию, иначе логинятся.

## Операции
| Операция | Скрипт | Применение |
|----------|--------|------------|
| Топ-страницы конкурента | `python3 scripts/semrush_top_pages.py --domain X.ru --limit 50` | §3a Top Pages (Google), ключи-драйверы конкурентов |
| Backlink gap | `python3 scripts/semrush_backlink_gap.py --domain site.ru --competitors "c1.ru,c2.ru"` | доноры конкурентов которых нет у нас → линкбилдинг |
| Organic keywords | (через top_pages/domain organic) | ранжирующие ключи конкурента → семантика |

## Грабли (почему часто пусто)
1. **Playwright-сессия хрупкая** — падает на timeout/redetect. Перед прогоном — `pkill -f "Google Chrome"`, проверить сессию жива.
2. **RU-покрытие тонкое** — для узких RU-ниш (зуботех, локальные услуги) SEMrush часто отдаёт пусто/мало. Это НЕ блокер — помечать «coverage тонкий» и переходить к fallback.
3. **Fallback когда SEMrush пуст (нет keys.so для Яндекса):** curl sitemap.xml конкурентов + /uslugi/ → их service-структура → реальные кластеры что таргетируют (метод DS-Lab, работает без токенов). См. `seo-presale-audit-workflow.md` Шаг 3.3.
4. **Для Яндекса SEMrush слаб** — он Google-ориентирован. RU-позиции/ключи → Topvisor/Wordstat/keys.so, не SEMrush.

## Когда что
- Google top-pages/backlinks конкурентов → SEMrush (если сессия жива).
- Яндекс (основное для RU) → Wordstat (частотность) + Topvisor (позиции) + структура конкурентов (curl).
- keys.so (Яндекс organic конкурентов) — токена пока НЕТ (купить → закроет §3a по Яндексу).
