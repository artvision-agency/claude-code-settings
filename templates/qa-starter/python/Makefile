.PHONY: help install test test-cov lint typecheck security all clean hooks

help:
	@echo "Targets:"
	@echo "  install    — install dev dependencies"
	@echo "  test       — run pytest (no coverage gate)"
	@echo "  test-cov   — run pytest with coverage (fails <80%)"
	@echo "  lint       — ruff check + format check"
	@echo "  typecheck  — mypy"
	@echo "  security   — bandit"
	@echo "  all        — lint + typecheck + security + test-cov"
	@echo "  hooks      — install pre-commit hooks"
	@echo "  clean      — remove caches and reports"

install:
	python -m pip install --upgrade pip
	pip install -r requirements-dev.txt
	@if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
	@if [ -f pyproject.toml ]; then pip install -e . || true; fi

test:
	pytest --no-cov

test-cov:
	pytest

lint:
	ruff check .
	ruff format --check .

lint-fix:
	ruff check --fix .
	ruff format .

typecheck:
	mypy src tests 2>/dev/null || mypy .

security:
	bandit -r src -c pyproject.toml 2>/dev/null || bandit -r . -x ./tests,./.venv -c pyproject.toml

all: lint typecheck security test-cov

hooks:
	pre-commit install
	pre-commit install --hook-type commit-msg

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov coverage.xml reports .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
