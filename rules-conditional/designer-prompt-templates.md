---
name: designer-prompt-templates
paths:
  - '**/design/**'
  - '**/*design*'
---

# Designer Prompt Templates — указатель на библиотеку one-shot промптов дизайнера

> **Установлено:** 2026-06-15 (Антон). Источник: видео DesignCourse (Gary Simon) «Claude Fable 5 UI/UX One-Shots — 5 Tests» (YouTube tSg3FAdWvzI) — извлечено через `/video-learn`.
> **Запрос:** «собрать промпты дизайнера для будущих разработок, как шаблон для любой ниши, с возможностью разработать свою версию на этом шаблоне».
> **Это короткий указатель (грузится каждую сессию).** Полная библиотека: `~/artvision-data/templates/design-prompts/designer-oneshot-prompts.md`.
> **Связано:** `capture-wins-as-skills.md` (захват находки), `analyzed-project-design-system.md` (дизайн-система клиента — НЕ дефолт-тёмная), `template-selection-map.md` (класс артефакта), `mobile-first-all-html.md`, `_compliance-checklist.md`, skill `/frontend-design`, `/figma-bulk-creative`, `/website-to-hyperframes`, `/design-extract`, `/site-clone-pipeline`, `figma-mcp-bulk-creative.md`.

## Когда применять
Любая генерация UI/интерфейса для разработки (лендинг, hero, дашборд, страница услуги, посадочная, редизайн) — для клиента или нашего продукта. ПЕРЕД тем как писать промпт «из головы» — открыть библиотеку и взять каркас.

## Правило (DEFAULT)
Качественный UI = **детальный one-shot промпт с 6 рычагами**, не короткое «сделай лендинг» (доказано на 5 тестах Gary Simon):
1. Планка качества словами («modern, awards-worthy, winning» — не «clean minimal»).
2. Референс как вход (скриншот/URL/видео → воссоздать ИЛИ «объективно лучше приложенного»).
3. Тех-стек и моушн явно (GSAP/three.js/CSS, subtle, выверенные timing/easing).
4. Ограничения управляют выходом (type-heavy / не уходить в white space / ФЗ-323 / B2B-сдержанность).
5. Верификация в промпте (Chrome DevTools, mobile-friendly 375).
6. Агент-усиление (spawn Figma MCP design agent для бренд-точности → `/figma-bulk-creative`).

## 5 архетипов (в библиотеке — готовые блоки)
- **A** — с нуля awards-worthy · **B** — воссоздать по скриншоту+URL (секция/эффект) · **C** — «объективно лучше приложенного» + Figma MCP · **D** — модернизировать сдержанно (контроль ограничениями) · **E** — воссоздать по видео-эталону.

## Форк под проект (своя версия)
1. Копировать в `clients/<slug>/design/prompts-<slug>.md`.
2. Извлечь дизайн-систему клиента (`curl <site>+styles.css | grep '#hex'+font-family`) → подставить (НЕ дефолт-тёмная).
3. Выбрать архетип A-E + нишевые ограничения + класс артефакта (`template-selection-map`).
4. Прогнать `/frontend-design` (или Figma MCP) → деплой review-URL → самопроверка скриншотом глазами (`post-deploy-selfcheck`).
5. Удачные правки — обратно в `prompts-<slug>.md` (растёт как контекст проекта).

## Антипаттерны
- ❌ Короткий промпт вместо детального one-shot с 6 рычагами.
- ❌ Дефолтная тёмная тема вместо дизайн-системы клиента.
- ❌ Generic-шаблон / «clean minimal» без направления.
- ❌ Воссоздание (B/E) с чужими фото/лого без замены на наши (этика+право).
- ❌ Пиксель-клон всего сайта текст-спекой вместо `site-clone-pipeline`.
- ❌ «Готово» без DevTools + mobile 375 + просмотра скриншота глазами; AI как финальный гейт (приёмка/AB — человек).

## Кандидат (TODO, свежая сессия через skill-generator)
Skill `/design-oneshot <архетип> <slug>` — интерактивная обёртка: выбрать архетип → извлечь дизайн-систему клиента → собрать заполненный промпт → передать в `/frontend-design`/Figma MCP. Пока — копировать каркас из библиотеки вручную.

## Sync
`~/.claude/rules/` → 3 аккаунта через git. Библиотека промптов — в `artvision-data` (git, видно всем). Применяется во всех нишах.
