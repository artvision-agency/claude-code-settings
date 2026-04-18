.PHONY: install test test-unit test-integration test-schema test-regression test-stealth golden-update

install:
	pip install -r requirements-dev.txt
	playwright install chromium

test: test-unit test-schema test-regression

test-unit:
	pytest tests/unit -v

test-integration:
	pytest tests/integration -v -m integration

test-schema:
	pytest tests/schema -v -m schema

test-regression:
	pytest tests/regression -v -m regression

test-stealth:
	pytest tests/stealth -v -m stealth --headed

golden-update:
	PYTEST_GOLDEN_UPDATE=1 pytest tests/regression -v
