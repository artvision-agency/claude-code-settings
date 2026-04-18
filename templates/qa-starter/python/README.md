# QA Starter — Python

Тесты + линт + типы + security + CI + pre-commit. Coverage gate 80%.

## Быстрый старт (новый проект)

```bash
cp -r ~/.claude/templates/qa-starter/python/. ./ && cat pyproject.toml.fragment >> pyproject.toml && rm pyproject.toml.fragment && make install && make hooks && make all
```

## Применение к существующему проекту

1. Скопируй файлы вручную:
   ```bash
   cp -r ~/.claude/templates/qa-starter/python/tests ./
   cp ~/.claude/templates/qa-starter/python/requirements-dev.txt ./
   cp ~/.claude/templates/qa-starter/python/Makefile ./
   cp ~/.claude/templates/qa-starter/python/.pre-commit-config.yaml ./
   mkdir -p .github/workflows
   cp ~/.claude/templates/qa-starter/python/.github/workflows/test.yml .github/workflows/
   ```
2. Смерджи `pyproject.toml.fragment` в свой `pyproject.toml` (или скопируй как есть, если нет).
3. `make install && make hooks && make all`.

## Структура

```
python/
├── tests/
│   ├── conftest.py                    # pytest fixtures skeleton
│   ├── test_example.py                # unit test (parametrized, raises)
│   └── test_integration_example.py    # integration с моками
├── requirements-dev.txt               # pytest, ruff, mypy, bandit
├── pyproject.toml.fragment            # секции pytest/ruff/coverage/bandit/mypy
├── .github/workflows/test.yml         # CI: ruff, mypy, bandit, pytest --cov
├── .pre-commit-config.yaml            # ruff + mypy + bandit локально
├── Makefile                           # test, lint, typecheck, security, all
└── README.md
```

## Команды

| Команда | Что делает |
|---------|-----------|
| `make test` | pytest без coverage gate |
| `make test-cov` | pytest с coverage gate 80% |
| `make lint` | ruff check + format --check |
| `make lint-fix` | ruff check --fix + format |
| `make typecheck` | mypy strict |
| `make security` | bandit по src |
| `make all` | lint + typecheck + security + test-cov |
| `make hooks` | установить pre-commit hooks |
| `make clean` | удалить кеши и репорты |

## Что в CI

1. `ruff check` + `ruff format --check` — линт и форматирование.
2. `mypy` — статическая типизация (strict).
3. `bandit` — security-скан.
4. `pytest --cov` — тесты + coverage ≥80% (gate fail если меньше).
5. Артефакты: HTML coverage, JUnit XML (badge-friendly).

## Markers

- `@pytest.mark.slow` — тесты >1s
- `@pytest.mark.integration` — требует внешних сервисов (skip по умолчанию, запуск через `--run-integration`)
- `@pytest.mark.e2e` — полные E2E

## Проверка что всё работает

```bash
make install
make all   # должно пройти на примерах
```

Если CI зелёный — template применён правильно.
