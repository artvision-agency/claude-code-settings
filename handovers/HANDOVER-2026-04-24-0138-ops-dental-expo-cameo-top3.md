---
session_id: 2ca2534e-current
context: ops
date: 2026-04-24 01:38
status: завершено (топ-3), 7 экспонентов → следующая сессия
---

# Handover: Дентал-Салон CAMEO КП топ-3 (Acteon / GC Russia / Рокада Мед)

**Дата:** 2026-04-24 01:38
**Контекст:** ops (artvision-data)
**Ветка:** feat/ops-crm-v1 (pushed be9715458)
**Дедлайн показа:** 24.04.2026 PM (конец выставки) — готово

## 🎯 Цель сессии

Подготовить 3 КП для очного показа Антоном на Дентал-Салоне 24.04 топ-3 экспонентам (Acteon, GC Russia, Рокада Мед) — по паттерну CAMEO+ (Acteon как эталон).

## ✅ Что сделано

| Экспонент | Файл | URL | Палитра | Строк |
|-----------|------|-----|---------|-------|
| Acteon | `clients/dentalexpo/presale/kp/acteon_kp.html` | https://artvision.pro/dental-expo/kp/acteon_kp.html | cyan #00B0DB + charcoal | 376 |
| GC Russia | `clients/dentalexpo/presale/kp/gcrussia_kp.html` | https://artvision.pro/dental-expo/kp/gcrussia_kp.html | teal #139C83 + graphite | 400 |
| Рокада Мед | `clients/dentalexpo/presale/kp/rocadamed_kp.html` | https://artvision.pro/dental-expo/kp/rocadamed_kp.html | red #E21710 + navy #0F2847 | 405 |

Все: HTTP 200 OK, factcheck 0 CRITICAL, адаптив 3 viewport.

Git: `feat/ops-crm-v1` → `be9715458` pushed в origin.

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| Acteon как pattern для остальных | Делать каждый с нуля | Antоn одобрил стиль Acteon — унифицированная структура, быстрая генерация через subagent |
| Палитру извлекать Playwright'ом с сайта клиента | Брать fallback из brandbook | Реальный брендинг клиента = уважение, сразу узнаваемо на презентации |
| Subagent'ы параллельно (GC + Рокада) | Последовательно | Независимые, exctract сайтов разные домены — время x2 быстрее |
| Без цен, тиры без сумм | Показать базовую ставку | Presale-показ, цена обсуждается после заинтересованности. Антон: "цены не в КП" |
| Блок «Чем собирали данные» с 6 продуктами Artvision (Flow/Scout/Radar/LinkForge/Watch/Lens) | Просто «методология» | Показать инструментарий → доверие к данным + upsell-намёк |
| НЕ добавлять scroll-reveal анимации | IntersectionObserver fade-in | Антон одобрил стиль Acteon без анимаций |
| 11 секций по структуре Acteon | Короче/длиннее | Pattern проверен — не ломать |

## ❌ Что НЕ сделано

- **7 экспонентов** (Юнидент / Ревилайн / МегаДжен / Кагаяки / Крафтвэй / СТЛ / ТС Дентал) — findings не собраны (в этой сессии данные только на топ-3). Нужна новая сессия после /clear.
- **«Прилога» для Dental-Expo** — Антон упомянул, но неясно что именно (event-landing-2026-04-22-v3.html? другое?). Уточнить у Антона.
- **Анимации CAMEO** (scroll-reveal) — отложено, стиль одобрен без них.

## 📚 Уроки

- **Subagent + Playwright extract палитры** — рабочий паттерн для генерации КП по pattern'у. Сэкономил ~10 мин на каждый КП.
- **Pattern-based генерация**: если есть эталон (Acteon) → subagent'у достаточно "build like {path} for {client}" + URL клиента → качество сохраняется.
- **Контекст 223%** — сессия не вытянула весь объём (10 экспонентов), надо было /clear после топ-3 сразу. Урок: планировать handover на 50% заранее.

## 🔜 Следующие шаги

1. **HIGH** — следующая сессия: собрать findings + КП для 7 экспонентов. Subagent по тому же pattern'у. Ориентировочно 2 subagent'а × 4 раунда (14-экспонент-пар).
2. **MEDIUM** — уточнить у Антона что такое «прилога» Dental-Expo.
3. **LOW** — если Антон после показа скажет "нужны анимации" → добавить IntersectionObserver scroll-reveal в все 10 КП единым патчем.
4. **SIDE** — снять блокер `[blocked-by: CAMEO HTML топ-3]` в TODO.md.

## 🗺️ Карта файлов

```
~/artvision-data/clients/dentalexpo/
├── presale/kp/
│   ├── acteon_kp.html          ← ЭТАЛОН PATTERN'А, 376 строк
│   ├── gcrussia_kp.html        ← new, 400 строк
│   └── rocadamed_kp.html       ← new, 405 строк
└── (findings для 7 остальных ещё нет)

artvision.pro/dental-expo/kp/    ← VPS deployed, все 200 OK
```

## ⚠️ Гачи

- **Acteon = source of truth** для pattern'а. Subagent'ам давать именно этот файл как reference, не GC и не Рокаду (могут быть локальные отклонения).
- **Factcheck ДО scp** — хук `pre-scp-factcheck.sh` блокирует если CRITICAL. Все 3 прошли чисто, но новые экспоненты могут не пройти без реальных URL.
- **Без цен!** В КП нет сумм — это решение, не забывание. Если в следующих появятся — вернуть.
- **Палитру проверять глазами** после Playwright extract — иногда берёт accent из рекламного баннера, не основной брендинг.
- **Контекст** — /clear перед стартом следующей сессии. Пытаться сжимать эту = задавить handover.

## 🔗 Связанные ресурсы

- TODO.md: задача `Дентал-Салон: очный показ топ-3 CAMEO` (high, due 2026-04-24) — блокер CAMEO HTML снят, задача "готова к показу"
- Git commit: `be9715458` в `feat/ops-crm-v1`
- Предыдущие handovers: 11 pending в `~/.claude/handovers/.pending/` (не relevant к этой работе, отдельная тема)
