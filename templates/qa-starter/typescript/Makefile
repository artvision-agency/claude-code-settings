.PHONY: help install test test-cov lint typecheck all clean hooks

help:
	@echo "Targets:"
	@echo "  install    — npm install"
	@echo "  test       — vitest run"
	@echo "  test-cov   — vitest run --coverage (fails <80%)"
	@echo "  lint       — eslint"
	@echo "  typecheck  — tsc --noEmit"
	@echo "  all        — typecheck + lint + test-cov"
	@echo "  hooks      — install pre-commit hooks"
	@echo "  clean      — remove build/coverage artifacts"

install:
	npm ci 2>/dev/null || npm install

test:
	npm test

test-cov:
	npm run test:cov

lint:
	npm run lint

lint-fix:
	npm run lint:fix

typecheck:
	npm run typecheck

all: typecheck lint test-cov

hooks:
	pre-commit install

clean:
	rm -rf dist coverage reports node_modules/.cache .eslintcache
