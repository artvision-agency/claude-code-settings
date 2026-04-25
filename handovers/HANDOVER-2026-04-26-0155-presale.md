# Handover: Позиции circon-clinic.ru по 117 ключам Творим (Yandex СПб)

**Дата:** 2026-04-26 01:55
**Контекст:** presale (новый потенциальный клиент Циркон)
**Сессия:** ab0ab5bd-5b0e-4984-a8d0-31aa121df9d8
**Статус:** ⚠️ заблокировано — нужно действие Антона в UI

## 🎯 Цель сессии

Снять позиции circon-clinic.ru в Yandex/СПб по 117 ключам семантики проекта Творим (Topvisor pid=15535661) и сохранить выгрузку.

## ✅ Что сделано

- Topvisor pid=15535661 (Творим) — выгружены **все 117 ключей** с group_id, 7 непустых групп: Несгруппированное 27 / Виниры 4 / Имплантация 57 / Реставрация 4 / Ортодонтия 9 / Протезирование 13 / Хирургия 3 (Детская и Терапия — пустые в исходнике).
- Topvisor — создан **новый проект `circon-clinic.ru` pid=28117034**, добавлен регион Yandex/СПб desktop, импортированы все 117 ключей в 7 групп 1:1 как у Творим.
- Topvisor pid=15535661 — добавлен **competitor circon-clinic.ru id=28116977** (на всякий, выключен on=0).
- `~/.claude_temp_scripts/tv_circon_poll.py` — готовый poller, опрашивает history каждые 90 сек, на выходе сохраняет CSV+MD в `clients/circon-clinic/seo/`.
- Yandex Cloud Search API — проверен, ключ валиден (`api_key_id=aje1qfsiohtakmbdud0a`, folder=`b1g3skikcv7e3aehpu26`), но HTTP 403 — нужна роль.
- Side-артефакты (адаптированные кластеры 175 кл) удалены по решению Антона.
- Recap `sync/recaps/ab0ab5bd-...md` обновлён до PARTIAL.

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---|---|---|
| Создать новый Topvisor проект под Циркон | Подсадить ключи в проект Творим | Творим pid 15535661 архивный (`existsDates` пуст с 2024-10-21), сбор не идёт |
| Не использовать `add/positions_2/tasks` | Разовая проверка без проекта | API возвращает 1003 «undefined method» — метод не в подписке |
| Yandex Cloud Search API как fallback | xmlriver / Playwright | Ключ уже в `tokens.json`, бесплатный лимит, миграция XML → Cloud Search официальная |
| Отказался от своих кластеров (175 кл) | Расширенная семантика под Циркон | Антон уточнил: нужны **только** 117 ключей Творим как есть |

## ❌ Что НЕ сделано и почему

- **Сбор позиций** — заблокировано:
  - Topvisor проект 28117034 имеет `on=0`, API метод `edit/projects_2/projects/on` принимает только `on=0` (вылючить); `on=1` отвергается → включить можно **только в UI** (биллинговая операция)
  - Yandex Cloud Search API → 403 Permission denied, service-аккаунту не назначена роль `search-api.executor`

## 📚 Уроки (для memory)

- **Topvisor API не позволяет включить проект на сбор позиций.** `edit/projects_2/projects/on` принимает только `on=0`. Включение = только UI/тариф. → `feedback_topvisor_api_limits.md`
- **Yandex Cloud Search API = новый дом Yandex XML.** Старый `yandex.ru/dev/xml/` редиректит на `aistudio.yandex.ru/docs/ru/search-api/`. Доступ через ключи `yandex.cloud` в tokens.json — не SpeechKit only, как казалось. → `reference_yandex_search_api.md`
- **«Собери то же самое» ≠ «адаптируй».** Антон под «то же самое» подразумевает «ровно те же данные», не «структурно похожее». Спрашивать перед интерпретацией. → `feedback_literal_interpretation.md`
- **Готовые скрипты ПЕРЕД своим кодом.** В `scripts/topvisor_*.py` и `.claude_temp_scripts/topvisor_mitralab*.py` уже были рабочие паттерны для разовой проверки. Я писал с нуля — antipattern. → `feedback_check_existing_scripts_first.md`

## 🔜 Следующие шаги

1. **HIGH (Антон):** Один из двух путей разблокировки —
   - **A. Topvisor:** https://topvisor.com/projects/28117034 → включить тариф «Сбор позиций» на проект (или прицепить к существующему пакету)
   - **B. Yandex Cloud:** https://console.cloud.yandex.ru → каталог `b1g3skikcv7e3aehpu26` → Сервисные аккаунты → найти аккаунт с api_key_id `aje1qfsiohtakmbdud0a` → назначить роль `search-api.executor` на каталог
2. **HIGH (Claude после разблокировки):**
   - Если путь A → `nohup python3 ~/.claude_temp_scripts/tv_circon_poll.py > /tmp/tv_poll.log 2>&1 &` → ждать 10-15 мин → проверить `clients/circon-clinic/seo/positions-2026-04-26.{csv,md}`
   - Если путь B → дописать скрипт `tv_circon_yandex_search.py` под Cloud Search API (async, 117 запросов, batch ~100 в день free), сохранить в тот же путь
3. MEDIUM: удалить competitor circon-clinic.ru id=28116977 из проекта Творим (если путь B пошёл, Topvisor проект 28117034 уже не нужен — снести)
4. LOW: обновить knowledge/seo/rules.md с уроком про Topvisor API limits

## 🗺️ Карта файлов

```
~/artvision-data/
├── sync/recaps/ab0ab5bd-...md            ← recap PARTIAL
└── clients/circon-clinic/                 ← УДАЛЕНА (side-артефакты убрали, после разблокировки создаётся poller-скриптом)

~/.claude_temp_scripts/
└── tv_circon_poll.py                      ← готовый poller, ждёт включения проекта

~/artvision-data/tokens.json
├── topvisor.user_id + api_key             ← рабочие
└── yandex.cloud.{folder_id, api_key_id, api_key}  ← валидные, нет роли search-api.executor
```

## ⚠️ Гачи

- **`git add -A` опасен:** в моменте sync захватил `engagement_probe.py` (Scout) и `gantt-data.json` (cron) которые НЕ из этой сессии. Проверять stage перед commit. (В этот раз auto-commit hook их забрал в свой коммит — обошлось.)
- **Topvisor проект Творим (15535661) сейчас имеет лишнего конкурента** circon-clinic.ru id=28116977 (выключен). Не критично, но при чистке убрать.
- **circon-clinic — НОВЫЙ потенциальный клиент**, в реестре `clients-registry.md` его пока нет. После съёма — добавить или нет (зависит от планов Антона).
- **Контекст 88%** при создании этого handover — следующая сессия должна стартовать с чистого `/clear`, читать этот файл первым.

## 🔗 Связанные ресурсы

- Topvisor проекты: pid=15535661 (Творим, архивный), pid=28117034 (Циркон, on=0), pid=28063349 (Mitralab — рабочий пример)
- Topvisor API docs: https://topvisor.com/api/v2-services/
- Yandex Search API docs: https://aistudio.yandex.ru/docs/ru/search-api/quickstart/
- Tasks: #4 (in_progress), #5 (completed)
- Последний коммит сессии: `cb6d2176f` (auto-commit подобрал sessions/jsonl)
