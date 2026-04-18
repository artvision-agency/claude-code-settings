# QA Starter — TypeScript / Node.js

Vitest + ESLint + TS strict + CI + pre-commit. Coverage gate 80%.

## Быстрый старт (новый проект)

```bash
cp -r ~/.claude/templates/qa-starter/typescript/. ./ && npm init -y >/dev/null && node -e "const a=require('./package.json'),b=require('./package.json.fragment');Object.assign(a.scripts=a.scripts||{},b.scripts);Object.assign(a.devDependencies=a.devDependencies||{},b.devDependencies);require('fs').writeFileSync('package.json',JSON.stringify(a,null,2));" && rm package.json.fragment && make install && make hooks && make all
```

## Применение к существующему проекту

1. Скопируй файлы:
   ```bash
   cp -r ~/.claude/templates/qa-starter/typescript/tests ./
   cp ~/.claude/templates/qa-starter/typescript/vitest.config.ts ./
   cp ~/.claude/templates/qa-starter/typescript/tsconfig.json ./  # или смерджи опции
   cp ~/.claude/templates/qa-starter/typescript/.eslintrc.cjs ./
   cp ~/.claude/templates/qa-starter/typescript/Makefile ./
   cp ~/.claude/templates/qa-starter/typescript/.pre-commit-config.yaml ./
   mkdir -p .github/workflows
   cp ~/.claude/templates/qa-starter/typescript/.github/workflows/test.yml .github/workflows/
   ```
2. Смерджи `package.json.fragment` в свой `package.json` (scripts + devDependencies).
3. `make install && make hooks && make all`.

## Структура

```
typescript/
├── tests/
│   ├── setup.ts              # globals, hooks, mocks
│   ├── example.test.ts       # unit (parametrized)
│   └── integration.test.ts   # DI-based mocking
├── vitest.config.ts          # coverage 80%, JUnit XML
├── tsconfig.json             # strict + noUncheckedIndexedAccess
├── .eslintrc.cjs             # @typescript-eslint recommended + type-checking
├── package.json.fragment     # scripts + devDeps
├── .github/workflows/test.yml
├── .pre-commit-config.yaml
├── Makefile
└── README.md
```

## Команды

| npm | make |
|-----|------|
| `npm test` | `make test` |
| `npm run test:cov` | `make test-cov` |
| `npm run lint` | `make lint` |
| `npm run lint:fix` | `make lint-fix` |
| `npm run typecheck` | `make typecheck` |
| `npm run all` | `make all` |

## CI (GitHub Actions)

Матрица Node 20 / 22. Шаги: typecheck → lint → test-cov. Coverage gate 80% (lines/functions/statements), 75% (branches). Артефакты: HTML coverage, JUnit XML.

## Проверка

```bash
make install
make all   # должно пройти на примерах
```
