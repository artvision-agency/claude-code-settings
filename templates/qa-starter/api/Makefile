.PHONY: help install test-contract test-load-k6 test-load-locust test-auth all clean

BASE_URL ?= http://localhost:8000

help:
	@echo "Targets:"
	@echo "  install           — deps: schemathesis, locust, httpx"
	@echo "  test-contract     — schemathesis fuzz against openapi.yaml"
	@echo "  test-load-k6      — k6 load test (needs k6 installed)"
	@echo "  test-load-locust  — locust headless load test"
	@echo "  test-auth         — JWT / OAuth flow tests"
	@echo "  all               — contract + auth (load is manual)"

install:
	pip install schemathesis locust httpx pytest pyyaml

test-contract:
	BASE_URL=$(BASE_URL) pytest tests/contract -v --run-integration

test-load-k6:
	BASE_URL=$(BASE_URL) k6 run tests/load/k6_script.js

test-load-locust:
	mkdir -p reports
	locust -f tests/load/locustfile.py --host $(BASE_URL) \
		--headless -u 50 -r 10 -t 30s --html reports/locust.html

test-auth:
	API_BASE_URL=$(BASE_URL) pytest tests/auth -v --run-integration

all: test-contract test-auth

clean:
	rm -rf reports .pytest_cache
