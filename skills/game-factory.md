# Game Factory — Скилл для быстрого создания и публикации браузерных игр

Накопленный опыт проекта Card Duel: архитектура, мультиплатформенность, деплой, типичные ошибки.

---

## 1. Архитектура проекта

### Стек
- **Frontend:** Vue 3 + TypeScript + Vite
- **Backend (опционально):** Node.js + WebSocket (для PvP)
- **Монорепо:** pnpm workspaces (`packages/server`, `packages/shared`, корень = клиент)
- **Дизайн:** CSS custom properties, mobile-first, 4px grid

### Слои (Hexagonal / DDD)
```
src/
├── engine/          # Domain — чистая игровая логика (без Vue, без платформ)
│   ├── deck.ts      # Управление колодой
│   ├── combo.ts     # Детекция комбинаций
│   ├── damage.ts    # Расчёт урона
│   └── sound.ts     # Звук (mute/unmute)
├── platform/        # Infrastructure — SDK обёртки
│   ├── index.ts     # Platform detection (VITE_PLATFORM)
│   ├── yandex.ts    # Yandex Games SDK v2
│   ├── vk.ts        # VK Bridge
│   ├── ads.ts       # Единый интерфейс рекламы
│   ├── cloud-saves.ts  # Единый интерфейс облачных сохранений
│   └── leaderboards.ts # Лидерборды
├── network/         # Infrastructure — сервер, auth, WS
│   ├── use-auth.ts  # Auth composable (все платформы)
│   ├── use-multiplayer.ts  # WS клиент
│   └── ws-client.ts # WebSocket с reconnect
├── stores/          # Application — оркестрация
│   ├── game.ts      # Главный store
│   └── composables/ # useGameStats, useSessionLog, useCooldowns
├── components/      # Presentation — Vue компоненты
├── views/           # Экраны (Menu, Game, End, Profile, Leaderboard)
├── assets/          # CSS, шрифты
└── i18n/            # Локализация (ru, en, tr, etc.)
```

### Ключевой принцип
**Engine не знает о Vue и платформах.** Это позволяет:
- Тестировать логику без UI
- Переиспользовать движок в другом фреймворке
- Запускать на сервере (для PvP верификации)

---

## 2. Мультиплатформенность

### Platform Detection
```typescript
// src/platform/index.ts
const PLATFORM = import.meta.env.VITE_PLATFORM || ''
export const isYandex = PLATFORM === 'yandex'
export const isVK = PLATFORM === 'vk'
export const isTelegram = PLATFORM === 'telegram'
// ...
export const isPlatform = isYandex || isVK || isTelegram || ...
```

### Сборка под платформу
```bash
VITE_PLATFORM=yandex npx vite build --outDir dist-yandex
```

### Поддерживаемые платформы и их особенности

| Платформа | SDK | Auth | Cloud Saves | Лидерборды | Реклама | Особенности |
|-----------|-----|------|-------------|------------|---------|-------------|
| **Yandex** | SDK v2 | player.signature (HMAC) | player.setData() | ysdk.leaderboards | Fullscreen + Rewarded | Rate limit 1 req/sec на лидерборды |
| **VK** | VK Bridge | launch params | VKWebAppStorageSet | Нет встроенных | VKWebAppShowNativeAds | Max 3 interstitial/5 min |
| **Telegram** | WebApp SDK | initData HMAC | CloudStorage | Нет встроенных | AdsGram (отдельный SDK) | Async callback API |
| **CrazyGames** | SDK v3 | getUserToken() | Нет | Нет | showMidgame/showRewarded | Sitelock обязателен |
| **Poki** | Poki SDK | Нет | Нет | Нет | commercialBreak/rewardedBreak | Строгие требования к качеству |
| **Facebook** | Instant Games | getSignedPlayerInfoAsync | setDataAsync | Нет | getInterstitialAdAsync | Предзагрузка рекламы |
| **OK.ru** | FAPI | hash params | Нет | Нет | showAd | Старый API, callback-based |
| **GameDistribution** | GD SDK | Нет | Нет | Нет | showAd events | Event-based architecture |
| **itch.io** | Нет | Нет | Нет | Нет | Нет | Нулевой порог, без модерации, для фидбека |

### Приоритет публикации (рекомендуемый)
1. **Yandex** — большая RU-аудитория, хороший eCPM
2. **CrazyGames** — англоязычный трафик, revenue share от рекламы, порог $100
3. **Poki** — большой трафик, но строгие требования, работают по приглашениям (1-2 недели)
4. **itch.io** — мгновенная публикация, обычный web-билд, для фидбека и портфолио
5. **VK** — если нужна RU-аудитория сверх Яндекса
6. **Telegram** — растущая платформа

### i18n и платформы
- **Engine** (`packages/shared`): только id-ключи (`pair`, `bronze`, `freeze-1s`)
- **UI** (Vue): переводит через `t('combo.' + name)`, `t('ranks.' + id)`
- **Дефолт языка**: международные (CrazyGames, Poki, itch.io) → `en`, русские (Yandex, VK, OK) → `ru`
- **Переключатель языка**: скрывать только на Яндексе (SDK требование), на остальных — показывать
- **Лидерборды**: показывать кнопку только на платформах с поддержкой

### Единые интерфейсы

**Реклама** (`src/platform/ads.ts`):
```typescript
export async function showInterstitial(): Promise<boolean>
export async function showRewarded(): Promise<boolean>
```
Внутри — роутинг по `isPlatform`:
```typescript
if (isYandex) return showYandexInterstitial()
if (isVK) return showVKInterstitial()
// ...
```

**Облачные сохранения** (`src/platform/cloud-saves.ts`):
```typescript
export async function saveToCloud(data: Record<string, unknown>): Promise<void>
export async function loadFromCloud(): Promise<Record<string, unknown> | null>
```

**Лидерборды** (`src/platform/leaderboards.ts`):
```typescript
export async function submitScore(board: BoardName, score: number): Promise<void>
export async function submitAllScores(stats: {...}): Promise<void>
```

---

## 3. Аутентификация

### Паттерн: SDK → HTTP → WS fallback
```
1. SDK даёт токен/подпись (player.signature, launch params, initData)
2. Клиент POST /api/auth/{platform} → сервер верифицирует → httpOnly cookie
3. WS подключение — cookie авто-аутентифицирует
4. Fallback: если HTTP не работает (WebView) → WS-based auth
```

### Без сервера (isPlatform && !VITE_WS_URL)
Если PvP/сервер не нужен — **пропускать auth и WS полностью:**
```typescript
const hasServer = !isPlatform || !!import.meta.env.VITE_WS_URL
if (!hasServer) return // skip auth, WS, save-log
```

### Безопасность серверной верификации
- **ВСЕГДА `timingSafeEqual`** для HMAC/подписей (не `===` / `!==`)
- Валидация длины токена (max 8192)
- Валидация playerId (тип + длина + формат)
- Проверка пустых сегментов токена
- httpOnly cookies (защита от XSS)

---

## 4. Деплой и публикация

### Чеклист перед публикацией на платформу

#### Общий
- [ ] `overflow: hidden` на html/body (платформы запрещают page scroll)
- [ ] Touch targets минимум 44x44px (WCAG 2.5.5)
- [ ] `aria-label` на иконочных кнопках
- [ ] Нет WS/HTTP запросов к хосту платформы (относительные URL запрещены)
- [ ] Нет `console.log` спама (только logger с уровнями)
- [ ] Локализация минимум ru + en
- [ ] Responsive: мобильный + десктоп

#### Yandex Games
- [ ] SDK скрипт: `<script src="https://yandex.ru/games/sdk/v2"></script>`
- [ ] `ysdk.features.LoadingAPI.ready()` после загрузки
- [ ] `ysdk.on('game_api_pause', ...)` — мьютить звук, ставить на паузу
- [ ] Лидерборды: имена только `[a-zA-Z0-9]`, без подчёркиваний
- [ ] Rate limit: `setScore` не чаще 1 раз/сек → последовательная отправка с delay
- [ ] Размер ZIP < 200MB (рекомендуется < 5MB)
- [ ] Борды создать в консоли ДО отправки

#### VK Games
- [ ] VK Bridge `send('VKWebAppInit')`
- [ ] Рекламу показывать не чаще 3 раз / 5 минут
- [ ] `VKWebAppStorageSet` — max 10 ключей

#### Telegram
- [ ] `Telegram.WebApp.ready()`
- [ ] BackButton навигация
- [ ] CloudStorage — async callback API (не Promise!)
- [ ] AdsGram — отдельный SDK для рекламы

#### CrazyGames
- [ ] Sitelock: проверка домена
- [ ] `window.CrazyGames.SDK.game.sdkGameLoadingStart/Stop()`
- [ ] Нет localStorage для прогресса (используй их API)

### Команды сборки
```bash
# Яндекс
VITE_PLATFORM=yandex npx vite build --outDir dist-yandex
# Упаковка
python3 -c "import zipfile,os;z=zipfile.ZipFile('game-yandex.zip','w',zipfile.ZIP_DEFLATED);[z.write(os.path.join(r,f),os.path.relpath(os.path.join(r,f),'dist-yandex')) for r,d,files in os.walk('dist-yandex') for f in files];z.close()"

# VK
VITE_PLATFORM=vk npx vite build --outDir dist-vk

# Telegram
VITE_PLATFORM=telegram npx vite build --outDir dist-telegram
```

### Имя ZIP-файла
**Всегда одно и то же**: `{project}-{platform}.zip` (например `card-duel-yandex.zip`). Не менять между билдами.

---

## 5. Типичные ошибки (Lessons Learned)

### CRITICAL
| Ошибка | Урок |
|--------|------|
| `sign !== expected` для HMAC | Всегда `timingSafeEqual` для криптографии |
| WS подключается к хосту платформы | На платформах без VPS — отключать WS и HTTP auth |
| `fetch('/api/...')` на платформе | Относительные URL идут на хост платформы, не на твой сервер |

### HIGH
| Ошибка | Урок |
|--------|------|
| `Promise.all` для лидербордов | Yandex rate limit 1/sec — отправлять последовательно |
| `bestDmg` обновлялся ПОСЛЕ `saveStats()` | Обновлять все данные ДО вызова save/submit |
| Touch targets 32px | Минимум 44px, даже на маленьких экранах |
| `:key="e.rank"` дублируется при ties | Использовать uniqueID или составной ключ |
| Лидерборд names с `_` | Yandex: только `[a-zA-Z0-9]` |
| Хардкод русских строк в shared engine | Combo/rank/effect names в engine — ТОЛЬКО id-ключи, перевод в UI через i18n |
| `v-if="!isPlatform"` для языка | Скрывать переключатель только на Яндексе (`isYandex`), остальные платформы — показывать |

### MEDIUM
| Ошибка | Урок |
|--------|------|
| `console.log` вместо `logger.*` | Единый логгер с уровнями |
| Переменная `t` затеняет `useI18n().t` | Не использовать `t` как имя переменной |
| `#54d474` хардкод вместо CSS var | Всегда CSS custom properties |
| `onEvent` deprecated в SDK v2 | Следить за версиями SDK, читать changelog |
| Cleanup subscriptions при HMR | Сохранять unsubscribe от `ysdk.on()` |
| Fallback locale `ru` для CrazyGames | Международные платформы — fallback `en`, русскоязычные — `ru` |
| Лидерборд виден без данных | Скрывать кнопку лидерборда на платформах без поддержки |
| CrazyGames sitelock блокирует preview | SDK + sitelock не дают preview по IP — использовать dev-сервер |
| CD индикатор только на Draw/Combo | Добавлять cd-fill на ВСЕ action-кнопки (включая Attack) |

### Из патчей проекта
| Патч | Урок |
|------|------|
| Shared method side effects | Если метод shared — трассировать ВСЕ вызывающие места |
| Field rename completeness | После переименования — grep ВЕСЬ проект |
| WebSocket navigation | Навигация ТОЛЬКО после подтверждения сервера |
| structuredClone migration | После bulk replace — grep на оставшиеся occurrences |
| PvP desync | Расчёты урона должны быть симметричны клиент-сервер |
| i18n в shared engine | Engine возвращает id-ключи (`pair`, `bronze`), UI переводит через `t('combo.' + name)` |

---

## 6. CSS Design System

### Токены
```css
/* Цвета */
--gold-400: #c9a84c;     /* Основной акцент */
--n-100: #e8e6e1;        /* Текст */
--n-400: #888;           /* Вторичный текст */
--bg: #0e0e16;           /* Фон */
--bg-el: rgba(255,255,255,0.03); /* Элемент */

/* Спейсинг (4px grid) */
--sp-1: 4px; --sp-2: 8px; --sp-3: 12px; --sp-4: 16px;

/* Типографика */
--text-xs: 11px; --text-sm: 13px; --text-base: 15px;
--text-lg: 17px; --text-xl: 20px; --text-2xl: 24px;

/* Шрифты */
--font-display: 'Cinzel', serif;
--font-body: 'IBM Plex Mono', monospace;

/* Радиусы */
--r-md: 8px; --r-lg: 12px; --r-xl: 16px;
```

### Responsive breakpoints
```css
@media (max-width: 480px)  { /* Мобильный */ }
@media (min-width: 600px)  { /* Малый планшет */ }
@media (min-width: 768px)  { /* Планшет */ }
@media (min-width: 1024px) and (min-height: 900px)  { /* Десктоп */ }
@media (min-width: 1440px) and (min-height: 1200px) { /* Большой десктоп */ }
```

### Правила
- `height: 100%; overflow: hidden` на контейнере экрана (платформы запрещают scroll)
- `overflow-y: auto` только на внутренних scrollable элементах
- `min-height: 44px` на всех интерактивных элементах
- `@media (hover: hover)` для hover-эффектов (не на тач-устройствах)

---

## 7. Порты (не менять!)

| Порт | Назначение |
|------|------------|
| 3001 | Docker prod + WS сервер |
| 4177 | Vite dev (HMR) |
| 4178 | Яндекс preview |

---

## 8. Git & Workflow

### Коммиты
```
feat: add new game mechanic
fix: player collision detection
refactor: extract game loop logic
```

### Запрещено
- `git reset` (любой)
- `git push --force` (без явного разрешения)
- `git commit --amend` после push

### Перед коммитом
- vue-tsc --noEmit (type check)
- vitest run (тесты)
- Проверить что нет секретов в коде

---

## 9. Быстрый старт новой игры

### Шаги
1. **Клонировать шаблон** или создать Vite + Vue 3 + TS проект
2. **Скопировать `src/platform/`** — готовые обёртки для всех платформ
3. **Настроить `vite.config.ts`** — инъекция SDK скриптов по VITE_PLATFORM
4. **Разработать engine/** — чистая логика без зависимостей
5. **Обернуть в stores/** — Vue reactivity поверх engine
6. **Создать экраны** — Menu, Game, End, Profile, Leaderboard, Settings
7. **Добавить i18n** — минимум ru + en
8. **Тестировать** — vitest для engine, vue-tsc для типов
9. **Собрать билды** — по одному ZIP на платформу
10. **Отправить на модерацию** — чеклист выше

### Порядок публикации (рекомендуемый)
1. **Yandex Games** — большая русская аудитория, простая модерация
2. **VK Games** — похожая аудитория, интеграция близка к Yandex
3. **CrazyGames** — англоязычный рынок, хороший трафик
4. **Poki** — строгие требования, но большой трафик
5. **Telegram** — растущая платформа
6. **Facebook/OK.ru** — по необходимости
