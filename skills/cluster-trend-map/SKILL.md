---
name: cluster-trend-map
description: Карта спроса + динамика по кластерам для клиента/региона (Wordstat). Оркеструет clusters→Wordstat(частоты 3 режима + помесячная динамика 2018+)→treemap+окна Динамика/Годы+деньги+покрытие→deploy→verify. Переиспользуемо per клиент+регион. Триггеры — 'cluster-trend', 'карта спроса', 'кластер тренды', 'динамика спроса', 'растущие кластеры', 'treemap спроса', 'cluster trend map', 'спрос по направлениям', 'годы wordstat', 'wordstat динамика'.
---

# cluster-trend-map — карта спроса и динамики по кластерам (per клиент/регион)

> Капстоун пайплайна USmile cluster-trend. Цель: ОДНОЙ командой собрать полную картину спроса
> (размер + деньги + покрытие + ДИНАМИКА 2018+ + растущие под-кластеры) для любого клиента и региона.
> Принцип: растущие под-кластеры → быстрый трафик → поведенческие → ранжирование
> (`~/.claude/rules/seo-rising-subclusters-fast-traffic.md`).
> Числа — ДЕТЕРМИНИРОВАННО из API (`numbers-deterministic-meaning-llm`), не «на глаз».

## Когда вызывать
- «карта спроса / динамика / растущие кластеры / treemap спроса» по клиенту.
- Новый SEO/PPC-клиент: понять где спрос, где деньги, что растёт, что не покрыто.

## Вход
- `<client>` — slug (есть `clients/<client>/`).
- `<region>` — GeoID Wordstat (СПб=2, Москва=1, РФ=225). По умолчанию из `clients/<client>/config.yaml`.
- Кластеры: `clients/<client>/ppc/semantics/arsenkin-clusters-SOURCE-OF-TRUTH.csv` (Arsenkin SERP-кластеризация; Услуга=направление, Фраза=фраза). Если нет — сперва собрать (Arsenkin, см. `tfidf-clustering`).

## Доступы (tokens.json)
- Частоты (v4 Direct): `yandex.direct` 3 аккаунта (round-robin, дневной лимит 1000/аккаунт — error 56).
- **Динамика (Search API)**: `yandex.cloud` (api_key + folder_id). Endpoint/правила/лимиты — `knowledge/services/yandex-wordstat/official-kb.md` (⛔ rate-limit 100 запросов/ЧАС → throttle+resume).

## Пайплайн (детерминированные шаги — «всегда работает»)
Все скрипты в `clients/<client>/ppc/manual_strategy/` (USmile — эталон, обобщать per клиент).

| # | Шаг | Скрипт | Заметка |
|---|-----|--------|---------|
| 1 | Кластеры → representative-фразы | (из arsenkin-CSV) → `treemap-phrases.txt` | БЕЗ капа [:10] — ВСЕ кластеры/направление (иначе «дыра покрытия») |
| 2 | Частоты 3 режима (broad/phrase/exact) | `collect_cluster_wordstat_spb.py --mode {broad\|phrase\|exact}` | round-robin 3 аккаунта (лимит 1000/день); брать фразовую/точную (широкая = сумма вложенных) |
| 3 | **Динамика помесячно 2018+** | `collect_dynamics_v1.py` (resumable+throttle) + runner `collect_all_dynamics.sh` | Search API, 100/час → добор батчами/cron; incremental-save; resume пропускает собранное |
| 4a | Treemap (размер/деньги/покрытие/пробелы/инфо) | `render_treemap_html.py` | дедуп по base_theme; деньги = ср.цена×спрос; пробелы = спрос есть, страницы нет |
| 4b | Окна Динамика + Годы 2018+ | `render_dynamics_html.py` → `cluster-dynamics.html` | год-фильтр ГЛОБАЛЬНЫЙ (графики окна 1 + таблицы); спарклайны; рейтинг растущих |
| 5 | Deploy | scp → `/var/www/artvision/_priv-<client>-cluster-trend/` | curl 200; URL первой строкой (always-html-deploy-links) |
| 6 | Verify | factcheck чисел vs CSV/JSON + визуал-QA 375/1440 (ui-visual-validator) + охват-баннер | НЕ выдавать частичный сбор за полный (дыра покрытия) |

## Правила качества (DoD — перед «готово»)
- ОХВАТ показан явно (собрано N из M фраз) — частичный сбор НЕ выдавать за полный.
- Частоты: фразовая/точная (не широкая); дедуп base_theme (без двойного счёта).
- Динамика: ряды из Search API as-is; rate-limit 100/час соблюдён (throttle/resume).
- Автономный HTML (0 внешних URL), mobile-first (min-width), охват-баннер.
- Визуал-QA глазами/валидатором на 375+1440 (не только структурно).
- Числа — source+дата; медфакты (если клиника) — `medical-facts-verification`.

## Эталон (USmile)
- Live: artvision.pro/_priv-usmile-cluster-trend/ (treemap) + /dynamics.html (динамика).
- Реестр ссылок: `clients/usmile/DEPLOY-LINKS.md`.
- Данные: `clients/usmile/ppc/data/market-trends/` (treemap-source.json, dynamics.json/csv, *-phrase.csv).

## Связано
`seo-rising-subclusters-fast-traffic`, `tfidf-clustering` (Arsenkin), `numbers-deterministic-meaning-llm`, `clinic-pricing-canonical` (деньги), `large-tool-output-to-file`, `determinism-first-and-verify`, `checks-by-validators-multimodel` (визуал-QA), `service-knowledge-base` (Wordstat KB).

## Статус обобщения
USmile = эталон (реализовано). Per-клиент обобщение: вынести GeoID/пути в параметры, перенести скрипты в шаблон. TODO — после стабилизации на 2-м клиенте.
