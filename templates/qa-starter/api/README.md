# QA Starter — REST API (backend-agnostic)

Contract (schemathesis) + Load (k6 / locust) + Auth flow. Работает с FastAPI, Flask, Django, Express, любым REST.

## Быстрый старт

```bash
cp -r ~/.claude/templates/qa-starter/api/. ./ && make install
# Подними свой API на :8000, затем:
make all
```

Чаще применяется поверх `python/` template.

## Структура

```
api/
├── tests/
│   ├── contract/
│   │   ├── openapi.yaml                 # замени на свой OpenAPI spec
│   │   └── test_contract.py             # schemathesis fuzz
│   ├── load/
│   │   ├── k6_script.js                 # k6 сценарий + SLO thresholds
│   │   └── locustfile.py                # locust альтернатива
│   └── auth/
│       └── test_auth_flow.py            # JWT + OAuth skeleton
├── .github/workflows/test.yml
├── Makefile
└── README.md
```

## Contract-тесты (schemathesis)

1. Замени `tests/contract/openapi.yaml` на настоящую спеку (можно из `/openapi.json` FastAPI).
2. Подними API на `$BASE_URL`.
3. `make test-contract`.

Schemathesis генерит валидные запросы по схеме и проверяет что ответы ей соответствуют. Находит: пропавшие поля, неправильные типы, необъявленные статус-коды, отсутствующий Content-Type.

## Load-тесты

### k6 (рекомендуется)

```bash
# Install: https://k6.io/docs/get-started/installation/  (brew install k6)
K6_VUS=50 K6_DURATION=1m BASE_URL=http://localhost:8000 k6 run tests/load/k6_script.js
```

SLO в `options.thresholds`:
- `http_req_duration p95 < 500ms`
- `http_req_duration p99 < 1000ms`
- `http_req_failed < 1%`

k6 вернёт non-zero exit если thresholds сломались.

### Locust (если k6 нельзя)

```bash
# UI: http://localhost:8089
locust -f tests/load/locustfile.py --host http://localhost:8000
# Headless:
make test-load-locust
```

## Auth flow

`tests/auth/test_auth_flow.py` — скелеты для:
- password-grant login → валидный JWT
- refresh token rotation
- 401 на invalid creds
- 401 на protected endpoint без токена
- 200 на protected endpoint с токеном
- client_credentials grant

Помечены `@pytest.mark.integration` — запуск через `--run-integration`.

## CI

Три job'а:
1. **contract** — schemathesis fuzz.
2. **load-k6** — smoke 10 VU × 15s (если упадёт — сигнал о регрессии p95).
3. **auth** — JWT/OAuth сценарии с секретами из GitHub.

В каждом шаге `TODO: start your API here` — замени на команду запуска своего сервера (`uvicorn app.main:app &`, `npm run start &` и т.д.).

## Интеграция с python/ template

Если проект Python:
```bash
cp -r ~/.claude/templates/qa-starter/python/. ./
cp -r ~/.claude/templates/qa-starter/api/. ./
# Merge pyproject fragment, установи api-deps:
pip install schemathesis locust httpx
```

Тогда `make all` из python/ прогонит unit + coverage, а `make -f api/Makefile all` — contract + auth.
