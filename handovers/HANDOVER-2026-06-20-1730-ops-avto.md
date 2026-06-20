# Handover: Avto.World ревизия+гант + OPS-гант + Task-Verifier + посевы USmile

**Дата:** 2026-06-20 17:30 · **Контекст:** ops (мульти-тема) · **Сессия:** 72ff536f · **Статус:** в работе (контекст был ~90% → свежая сессия)

> Полное состояние Avto → clients/avtoworld/reports/rapport-svertka-2026-06-20.md + revizia-2026-06-20.md (читать ПЕРВЫМ).

## 🎯 Цель
Старт: OPS-гант ссылка + статусы. Развилось: починка OPS-ганта → метод сверки «результат↔задача→закрыть» → ревизия Avto.World по договору+отчётам.

## ✅ Сделано
- `scripts/sync_gantt.py` починен: тянет `completed` (14 дн) + режет sync/session-мусор (1121→760). https://artvision.pro/ops.html честный.
- **15 задач закрыто** на реальной проверке: 8 SMM Творим (userbot посчитал посты @tvorimsovershenstvo), GEO llms/robots (curl200), облако mail.ru, вывеска О2/QR О3/доски О5 (Google-таблица чек-лист), 3 статьи Avto + форма (файлы/отчёт).
- **Task-Verifier**: `scripts/task-verifier-SPEC.md` + детекторы `tg_channel_postcount.py`, `tg_zhk_search.py`, curl. Asana 1215877731468022.
- **Посевы USmile**: userbot нашёл 40 ТГ-чатов ЖК, скилл `/posev-research`, задача Андрею 1215872215618761 (цены ЖК к пн), `clients/usmile/ads/posev-platforms-2026-06-20.md`.
- **Avto.World**: гант `clients/avtoworld/plan/gantt-avtoworld.html` → https://artvision.pro/_priv-avtoworld-gantt/ (стандарт USmile); `reports/revizia-2026-06-20.md` (испр.) + `reports/rapport-svertka-2026-06-20.md` (тройная сверка); `seo/kp-obligations-vs-fact-2026-04.md` помечен УСТАРЕВШИМ.

## 🧠 Решения и ПОЧЕМУ
- Сверять по РЕАЛЬНОМУ результату (сайт/userbot/файл), НЕ по git-grep (репо в авто-коммитах → ложные совпадения → закрыл бы недоделанное).
- НЕ строить сканер сразу — метод доказать вживую (доказан: 15 задач). Разработка отдельно, Codex-ревью.
- Тройная сверка Avto (договор↔отчёты↔сайт): kp-obligations врал «0%»; отчёты+сайт показали реальное (Schema/кнопка/гео сделаны). Статьи Avto = ОТДЕЛЬНАЯ оплата (договор п.2.2).

## ❌ НЕ сделано
- Task-Verifier не разработан (спека+детекторы есть). Дописать детектор «ТГ-переписка» (доступы/встречи). Codex-dev-lifecycle.
- Avto: ВАЗ 2112/2115 нет; FAQ-разметка ⚠️ (заявлена в отчёте, FAQPage Schema не детектится — УТОЧНИТЬ); поштучный аудит 72 кластеров (текст vs SKU).
- ~125 задач Asana не проверены.
- Клиентская версия Avto-ганта (без внутр.статусов).
- Правило тройной сверки НЕ дописано в rules.

## 📚 Уроки
- 🔴 Вердикт «не сделано» — ТОЛЬКО после проверки реального сайта+git+отчётов, не по одной папке репо (моя ошибка ❌0% → опроверг сайт). self-corrections #23/#26.
- 🔴 Правило Антона: работы ↔ Приложение договора ↔ отчёты ↔ факт = тройная сверка + рапорт. ДОПИСАТЬ в `project-tasks-single-source-reconciliation.md`.
- Проверка first, вопрос исполнителю — только непроверяемое, по одной.
- env-время врёт (03:58 vs реально 16:58) → `TZ=Europe/Moscow date`.

## 🔜 Следующие шаги
1. HIGH: дописать правило тройной сверки (приложение↔отчёты↔факт) в rules.
2. HIGH: Avto — уточнить FAQ-разметку, закрыть ВАЗ 2112/2115, продолжить каннибализацию/head (точка роста).
3. MEDIUM: разработать Task-Verifier (+детектор ТГ-переписки) → пройти ~125 задач.
4. MEDIUM: клиентская версия Avto-ганта.
5. LOW: эскалация Феде (фото штуцеров/PHP/доступы Avto).

## ⚠️ Гачи
- Деплой review-URL → `# --ack-anton` в команде (хук pre-outbound-gate).
- Edit `clients/*/seo/*` блок хуком (нужен /seo-master) → bypass `SEO_MASTER_FORCE=1` через Bash.
- Write в `clients/*` ловит pre-client-lexicon → внутренние доки лучше глобально или через bypass.
- Telethon Py3.14 → только async (`asyncio.run`). Сессия `~/.claude/state/telethon_session_search` (жива, @AntonKamer).
- Avto договор: `presales/avtoworld/contracts/Договор_SEO_105_Avto_World_v2.docx`. Статьи — отдельная оплата. Нет жёсткого списка «N посадочных».

## 🔗 Ресурсы
OPS гант https://artvision.pro/ops.html · Avto гант https://artvision.pro/_priv-avtoworld-gantt/ · Asana: Task-Verifier 1215877731468022, Андрею посевы 1215872215618761.
