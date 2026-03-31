---
name: tdd
description: Use when implementing any feature or bugfix — enforces RED-GREEN-REFACTOR cycle. Write tests FIRST, watch them fail, then write minimal code to pass.
---

# Test-Driven Development

## The Iron Law

```
NO CODE WITHOUT A FAILING TEST FIRST
```

## Cycle: RED → GREEN → REFACTOR

### RED — Write a failing test
1. Write test for the desired behavior
2. Run it — it MUST fail
3. If it passes — test is wrong or feature already exists

### GREEN — Write minimal code
1. Write the simplest code to make the test pass
2. No extra features, no "while I'm here"
3. Run tests — all must pass

### REFACTOR — Clean up
1. Remove duplication
2. Improve naming
3. Run tests — all must still pass

## Red Flags — STOP and Start Over

- Writing code before test
- "I'll test after"
- "Too simple to test"
- "I already manually tested it"
- "Tests after achieve the same purpose"

**All of these mean: Delete code. Start over with TDD.**

## What To Test

- Domain logic (always)
- Use cases (always)
- Edge cases: None, empty, boundary values
- Error paths

## What NOT To Test

- Framework internals (aiogram, SQLAlchemy)
- Third-party APIs (mock them)
- Trivial getters/setters

## Python Patterns

```python
# Test first
def test_price_below_market():
    analyzer = PriceAnalyzer()
    stats = MarketStats(median=500, p25=400, p75=600, count=10)
    result = analyzer.analyze(200, stats)
    assert result.label == "suspicious_low"

# Then implement
class PriceAnalyzer:
    def analyze(self, price, stats):
        ...
```

## Integration With DDD

- **Domain tests**: pure unit, no DB, no mocks needed
- **Use case tests**: mock ports (repositories)
- **Adapter tests**: SQLite in-memory for DB adapters
# test change
