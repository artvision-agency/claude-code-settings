.PHONY: help install test test-cov test-e2e test-a11y test-visual test-visual-update lint typecheck all clean

help:
	@echo "Targets:"
	@echo "  install             — npm install + playwright install"
	@echo "  test                — vitest (unit)"
	@echo "  test-cov            — vitest with coverage gate"
	@echo "  test-e2e            — playwright e2e (desktop)"
	@echo "  test-a11y           — playwright a11y (axe-core)"
	@echo "  test-visual         — playwright visual regression"
	@echo "  test-visual-update  — regenerate visual snapshots"
	@echo "  lint                — eslint"
	@echo "  typecheck           — tsc --noEmit"
	@echo "  all                 — typecheck + lint + test-cov + test-e2e"

install:
	npm ci 2>/dev/null || npm install
	npx playwright install --with-deps

test:
	npm test

test-cov:
	npm run test:cov

test-e2e:
	npm run test:e2e

test-a11y:
	npm run test:a11y

test-visual:
	npm run test:visual

test-visual-update:
	npm run test:visual:update

lint:
	npm run lint

typecheck:
	npm run typecheck

all: typecheck lint test-cov test-e2e

clean:
	rm -rf coverage playwright-report test-results reports node_modules/.cache
