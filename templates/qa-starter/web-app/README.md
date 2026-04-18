# QA Starter — Web App (React / Vue / Next)

Vitest (unit) + Playwright (e2e) + axe-core (a11y) + visual regression + CI.

## Быстрый старт (существующий проект)

```bash
cp -r ~/.claude/templates/qa-starter/web-app/. ./ && make install && make all
```

После копирования — смерджи `package.json.fragment` в свой `package.json` (скрипты + devDeps).

## Применение по шагам

1. Скопируй файлы:
   ```bash
   cp -r ~/.claude/templates/qa-starter/web-app/tests ./
   cp ~/.claude/templates/qa-starter/web-app/playwright.config.ts ./
   cp ~/.claude/templates/qa-starter/web-app/Makefile ./
   cp ~/.claude/templates/qa-starter/web-app/.pre-commit-config.yaml ./
   mkdir -p .github/workflows
   cp ~/.claude/templates/qa-starter/web-app/.github/workflows/test.yml .github/workflows/
   ```
2. Смерджи `package.json.fragment` в свой `package.json`.
3. Нужен `vitest.config.ts` и `tsconfig.json` — возьми из `../typescript/` если нет.
4. `make install && make all`.

## Структура

```
web-app/
├── tests/
│   ├── unit/example.test.ts        # vitest
│   ├── e2e/example.spec.ts         # playwright smoke + responsive
│   ├── a11y/example.spec.ts        # axe-core WCAG 2.1 AA
│   └── visual/example.spec.ts      # visual regression (screenshot diff)
├── playwright.config.ts            # 3 breakpoints, retain-on-failure
├── package.json.fragment
├── .github/workflows/test.yml      # unit + e2e jobs
├── .pre-commit-config.yaml
├── Makefile
└── README.md
```

## Breakpoints

- `mobile-375` — iPhone 12 viewport 375×667
- `tablet-768` — iPad 768×1024
- `desktop-1440` — 1440×900

Каждый e2e/a11y/visual тест прогоняется на всех трёх проектах.

## Команды

| Команда | Что делает |
|---------|-----------|
| `make test` | unit-тесты (vitest) |
| `make test-cov` | unit + coverage gate 80% |
| `make test-e2e` | Playwright e2e (desktop) |
| `make test-a11y` | axe-core accessibility |
| `make test-visual` | visual regression |
| `make test-visual-update` | обновить baseline скриншоты |
| `make all` | typecheck + lint + test-cov + test-e2e |

## Visual regression

Первый прогон — создаёт baseline (`tests/visual/__snapshots__/`). Последующие — сравнивают. Допуск 1% (`maxDiffPixelRatio: 0.01`).

Когда UI изменился намеренно — `make test-visual-update` + закоммитить новые baseline.

## A11y

axe-core + Playwright. Ищет violations impact `critical` и `serious` по WCAG 2.1 AA. Тест падает если есть хотя бы одна.

## CI

Два джоба:
1. **unit** — typecheck, lint, vitest с coverage.
2. **e2e** — ставит Playwright browsers (`--with-deps`), поднимает dev-сервер, гонит все сценарии на 3 breakpoints. Артефакты: HTML отчёт + JUnit XML + видео/скриншоты фейлов.

## Настрой под свой стек

В `.github/workflows/test.yml` блок `Build & start app` — замени команды на свои (`npm run dev` / `next start` / `vite preview` и т.д.). Или раскомментируй `webServer` в `playwright.config.ts`.
