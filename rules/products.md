# Продуктовая разработка

## Активные продукты

| Продукт | Папка | Стек | Ответственный |
|---------|-------|------|---------------|
| Card Duel | `products/cardwell/` | Vue 3, TypeScript, WebSocket | Стас = код, Антон = монетизация |
| AIvision (Artvision Radar) | `products/aivision/` | Python, API | Антон |
| Direct-Radar (Artvision Scout) | `products/direct-radar/` | Python, YAML configs | Антон |

## Правила

1. Каждый продукт имеет свой CLAUDE.md в корне папки — читать ПЕРВЫМ
2. Код через git → commit → push → deploy. НЕ на VPS напрямую
3. Тесты: `~/.claude/scripts/run-tests.sh` обёртка. Перед merge — тесты зелёные
4. Продуктовые задачи → `artvision-data/products/TODO.md`
5. Монетизация: ARPDAU, LTV, CAC — считать перед запуском фичи

## Деплой продуктов

- Card Duel: VPS 147.45.232.226, Yandex Games, Telegram Mini App
- AIvision: ai.artvision.pro
- Direct-Radar: CLI, конфиги в test-configs/

## Публичные названия (в маркетинге)

Внутреннее → публичное: PBN → Artvision LinkForge, AIvision → Artvision Radar, SEO Pipeline → Artvision Flow, Direct-Radar → Artvision Scout. Никаких AI/Bot/Neural.
