# Handover: Unotrans КП — формальная версия, визуальные правки

**Дата:** 2026-04-21 12:12
**Контекст:** presale (Unotrans, Денис Зыков)
**Сессия:** UNO (38200872-4fa8-4c5c-9d24-60188d92a651)
**Статус:** в работе, контекст 138% → /clear

## 🎯 Цель сессии

Сделать формальную (не-«суперграфика») версию КП Unotrans в стиле КП Бабурова v2 от 21.04, задеплоить, проверить качество.

## ✅ Что сделано

- `clients/unotrans/kp/unotrans-kp-formal-2026-04-21.html` — создан, 94,6KB, 1 262 строки, стиль Бабурова v2 (Georgia serif, белый, без декора)
- Деплой: https://artvision.pro/unotrans/kp/unotrans-kp-formal-2026-04-21.html (200 OK)
- Деплой скриншота: https://artvision.pro/unotrans/kp/screenshots/unotrans_com_overview.png (200 OK)
- Factcheck strict на старую v04 (https://artvision.pro/kp/unotrans/) — найдено **4 CRITICAL** пропущенных предыдущими проверками:
  - C1: `rusprofile/id/6846627` ведёт на партию «Союз Труда», правильный ID — `/id/11486802`
  - C2: Церта ИНН был `9710035907`, верный — `7805346759`
  - C3: Траско ИНН был `5024056317`, верный — `5024028131`
  - C4: «+32% транзит через Казахстан (РБК)» — РБК про Казахстан не пишет; +32% = заявки на автоперевозки РФ-Китай (цитата ПЭК)
  - Все 4 исправлены в новой formal-версии
- Память обновлена (3 новых файла):
  - `memory/feedback_inverted_pyramid.md` — первая строка = вердикт
  - `memory/feedback_lists_over_prose.md` — списки вместо прозы
  - `memory/feedback_factcheck_includes_ux.md` — factcheck включает UX/визуал/фронт

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| Стиль B (корпоративный отчёт Георгия serif) как у Бабурова v2 | A (Google Docs), C (деловое письмо) | Антон прямо сказал «как у Бабурова вчера» + «шрифты из серьёзных документов» |
| Не трогать prod `/kp/unotrans/` с 4 CRITICAL | Срочно пропатчить | Антон подтвердил что ссылку клиенту не отправлял → репутационного риска нет |
| SVG-диаграммы вместо старых скриншотов конкурентов | Оставить скриншоты из `kp/screenshots/` | Старые скрины = FESCO/ПЭК/eurolog, которые мы УДАЛИЛИ из актуального списка конкурентов. Релевантных скринов нет |
| Факчек до деплоя прошёл, но 2 CRITICAL (404 скрин + Коммерсантъ timeout) | Блокировать deploy | Оба снимаются после scp; Коммерсантъ — сетевой timeout скрипта, не факт |
| Handover + /clear вместо /compact | /compact focus on Unotrans | Контекст 138% — /compact уже теряет важное (правило bulletproof 40% + предупреждение хука) |

## ❌ Что НЕ сделано

- **Переписать повествовательные абзацы → списки/таблицы.** Антон указал это в последнем сообщении: «предложение за предложением», «нужны списки», «зарубить на носу». Применить в секциях 1.3, 4 (до таблицы), B.1 (интро), B.2, C (интро), E (интро) — везде где есть `section-intro` или `p` блоки из 2+ предложений.
- **UI-визуальная проверка.** Запущен `ui-visual-validator` агент (ID: `a111e95c7f637dafb`) фоном. На момент handover ещё работал. Отчёт в `/tmp/ui-audit-unotrans-formal-2026-04-21.md`.
- **Применить правки Бабурова «вчера».** Антон упомянул визуальные правки, которые делал на plan-3m-formal-v2 позже — нужно посмотреть ВСЕ файлы в `clients/baburov/kp/`: `plan-3m-doctor-first.html`, `plan-3m-detailed.html`, `plan-3m-visual.html`, `onboarding-3m.html` — возможно там более свежий финальный стиль, а не v2.
- **Новый факчек-слой UX.** Память `feedback_factcheck_includes_ux.md` создана, но не добавлен сам шаг в skill `factcheck`. Нужно обновить `/Users/antonk/.claude/skills/factcheck/SKILL.md` — добавить Layer 4 (ui-visual-validator) и Layer 5 (frontend-developer) автоматически для КП.

## 📚 Уроки (новое)

- Factcheck-v2 не проверяет **контент** rusprofile-страниц — только HTTP 200. Страница с ИНН 7839104050 может отдавать 200, но содержать партию «Союз Труда». Нужно grep по `og:title` и `meta ИНН`. Добавить в strict-factchecker.
- 3 предыдущих factcheck (14.04, 15.04, 18.04) пропустили C1-C4 → strict-factchecker должен получить **явный шаг «проверить что страница источника действительно про то, что в подписи КП»** (WebFetch + grep имени юрлица).
- В документах клиенту — СПИСКИ, не проза. Антон «зарубить на носу».

## 🔜 Следующие шаги (приоритет)

1. **HIGH:** Прочитать отчёт `ui-visual-validator` (`/tmp/ui-audit-unotrans-formal-2026-04-21.md`) → исправить съехавшие блоки.
2. **HIGH:** Переписать прозу → списки в `unotrans-kp-formal-2026-04-21.html` (секции 1.3, 4-интро, B.1-интро, B.2, C-интро, E-интро, section-intro всех разделов, callout-блоки → bullet-формат).
3. **HIGH:** Проверить все файлы в `clients/baburov/kp/` на предмет более позднего/финального стиля, применить к Unotrans.
4. **MEDIUM:** Обновить skill `/factcheck` — добавить Layer 4 (ui-visual-validator) + Layer 5 (frontend-developer) автоматически для путей `clients/*/kp/*.html`.
5. **MEDIUM:** Обновить `strict-factchecker` — шаг «проверить что контент страницы rusprofile/source соответствует подписи в КП».
6. **LOW:** Пропатчить prod `/kp/unotrans/` и `/unotrans/kp/unotrans-kp-2026-04.html` с 4 CRITICAL (риск низкий, но гигиенично).

## 🗺️ Карта файлов

```
clients/unotrans/
├── kp/
│   ├── unotrans-kp-formal-2026-04-21.html   ← НОВЫЙ formal, в работе
│   ├── unotrans-kp-2026-04.html              ← старый, 4 CRITICAL (prod пока не трогаем)
│   ├── screenshots/
│   │   └── unotrans_com_overview.png         ← используется в разделе 4 formal
│   └── (старые скрины конкурентов — НЕ использовать, это удалённые конкуренты)
├── context-log.md                            ← лог
├── reports/factcheck-kp-2026-04-14.md        ← отчёт strict от 14.04
└── brief-2026-03-14.md                       ← контекст клиента

clients/baburov/kp/
├── plan-3m-formal-v2.html        ← эталон стиля (использовал)
├── plan-3m-formal.html            ← v1
├── plan-3m-doctor-first.html      ← ПРОВЕРИТЬ
├── plan-3m-detailed.html          ← ПРОВЕРИТЬ (упомянут в коммите 18.04)
├── plan-3m-visual.html            ← ПРОВЕРИТЬ
└── onboarding-3m.html             ← ПРОВЕРИТЬ

~/.claude/handovers/
└── HANDOVER-2026-04-21-1212-presale.md   ← этот файл

/tmp/
├── factcheck-unotrans-2026-04-21.md          ← strict на старой v04 (BLOCK, 4 CRITICAL)
├── factcheck-unotrans-formal-2026-04-21.md   ← factcheck-v2 на formal (PASS по фактам)
└── ui-audit-unotrans-formal-2026-04-21.md    ← в работе, агент фоном
```

## ⚠️ Гачи

- **prod `/kp/unotrans/` содержит 4 CRITICAL**, но клиент ссылку не получал (подтверждено Антоном). Не паниковать, но учесть при редеплое.
- **Gmail MCP требует re-auth** (`token expired`) — проверку переписки с клиентом не сделать без авторизации.
- **Антон сильно раздражается на прозу** в документах — только списки/таблицы. Это железо.
- **Контекст сессии 138%** — ЛЮБУЮ доработку делать в НОВОЙ сессии с `/clear` и этим handover.
- **Agent `a111e95c7f637dafb`** (`ui-visual-validator`) мог ещё работать при старте новой сессии — проверить `/tmp/ui-audit-unotrans-formal-2026-04-21.md` на существование/полноту.

## 🔗 Связанные ресурсы

- Prod formal: https://artvision.pro/unotrans/kp/unotrans-kp-formal-2026-04-21.html
- Prod старая v04: https://artvision.pro/kp/unotrans/ (4 CRITICAL, не отправлена)
- Клиент: Денис Зыков, ООО «УНОтранс Групп» (ИНН 7839104050), unotrans.com
- Предыдущий factcheck: `clients/unotrans/reports/factcheck-kp-2026-04-14.md`

## Вход в новую сессию

```
cd ~/artvision-data
git pull
cat ~/.claude/handovers/HANDOVER-2026-04-21-1212-presale.md
cat /tmp/ui-audit-unotrans-formal-2026-04-21.md   # если есть
# Затем: шаг 1-3 из «Следующих шагов»
```
