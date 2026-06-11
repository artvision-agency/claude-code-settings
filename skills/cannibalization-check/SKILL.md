---
name: cannibalization-check
description: >
  Проверка каннибализации запросов через Яндекс.Вебмастер (query-analytics) — один запрос
  ранжируется на 2+ URL одного домена. Read-only, без GSC, не тратит баланс. Работает по любому
  хосту в нашем Вебмастер-аккаунте (28 клиентов). Дополняет SERP-overlap кластеризацию (/seo-cluster,
  tfidf-clustering): ловит ВТОРОЙ тип каннибализации (over-fragmentation). Триггеры — каннибализация,
  cannibalization, один запрос две страницы, дубли в выдаче, конкурируют страницы, проверь каннибализацию,
  query cannibalization, two pages one query.
user-invokable: true
argument-hint: "<slug или host_id> (напр. avtoworld | https:www.avto.world:443)"
metadata:
  author: Artvision
  category: seo
  created: 2026-06-04
---

# Cannibalization Check (Яндекс.Вебмастер)

Находит каннибализацию запросов **без GSC**, через Яндекс.Вебмастер API v4 `query-analytics/list`.
Прецедент: avto.world 04.06.2026 — найдено 14 запросов на 2+ URL (SKU-дубли, URL-encoding).

## Два типа каннибализации (проверять ОБА для полного аудита)
| Тип | Симптом | Чем ловит этот скилл / чем добить |
|---|---|---|
| **Over-fragmentation** | 1 запрос → N карточек/страниц | ✅ ЭТОТ скилл (Вебмастер query-analytics) |
| **Under-segmentation** | N интентов → 1 страница (generic) | SERP-overlap: `/seo-cluster` + `tfidf-clustering.md` (на generic Вебмастер не покажет — там один URL) |

## Шаги

1. **Определить host_id.** Если дан slug — взять домен из `clients/<slug>/config.yaml`. Запустить движок без аргумента → список хостов аккаунта, выбрать нужный (формат `https:www.avto.world:443`).
   ```bash
   python3 ~/artvision-data/scripts/yandex_cannibalization.py            # список хостов
   python3 ~/artvision-data/scripts/yandex_cannibalization.py <host_id>  # анализ
   ```
   Метод: `text_indicator:URL` → для каждого URL топ-запрос → инверсия query→[URLs] → флаг 2+ URL. Read-only, баланс не тратит.

2. **Классифицировать находки:**
   - **URL-encoding дубль** (`(tx)` vs `%28tx%29`, trailing-slash, `vaz-2107/` vs `vaz-2107.html`, `?page=N`) → canonical/301-редирект.
   - **Категория vs SKU** (запрос-категория размазан по N карточкам, категория проигрывает позицией) → усилить/создать категорийную посадочную.
   - **Близкие SKU** (бухты 10/25/50м под один запрос) → выбрать главную + canonical/перелинковка.

3. **Каждая находка → задача** (правило `audit-findings-to-tasks.md`): canonical / 301 / категория / перелинковка. Severity по показам.

4. **Артефакт:** дописать в `clients/<slug>/seo/cannibalization-*.md` (таблица запрос|URLs|показы|поз|вердикт|fix) + (опц.) deploy review-URL по `always-html-deploy-links.md`.

## Ограничения (честно)
- Вебмастер query-analytics возвращает по URL его ТОП-1 запрос → ловит явную over-fragmentation. Слабую (запрос #2 на одной странице, #1 на другой) — не видит.
- Доминируют брендовые навигационные запросы (`…бренд`) — это нормально для Вебмастера.
- Under-segmentation (generic-запрос → одна категория с разными интентами) этот метод НЕ ловит — для него SERP-overlap (`/seo-cluster`).

## Связано
- Движок: `~/artvision-data/scripts/yandex_cannibalization.py`
- Правила: `tfidf-clustering.md` (hard/soft SERP-overlap), `audit-findings-to-tasks.md`, `yandex-api.md`, `always-html-deploy-links.md`
- Скиллы: `/seo-cluster` (SERP-overlap кластеризация), `/seo-master` (URL-гигиена техаудита), `/topvisor-data-check`
- Прецедент: `clients/avtoworld/seo/cannibalization-cluster-review-2026-06-04.md`
