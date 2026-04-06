---
name: verification-loop
description: "A comprehensive verification system for Claude Code sessions."
origin: ECC
---

# Verification Loop Skill

A comprehensive verification system for Claude Code sessions.

## When to Use

Invoke this skill:
- After completing a feature or significant code change
- Before creating a PR
- When you want to ensure quality gates pass
- After refactoring

## Verification Phases

### Phase 1: Build / Syntax Verification

**Определи стек по файлам в директории:**

```bash
# Auto-detect: Python или JS/TS?
if ls *.py 2>/dev/null | head -1 >/dev/null; then
  echo "Python project"
  # Синтаксис ВСЕХ .py файлов
  find . -name "*.py" -not -path "*/node_modules/*" -not -path "*/__pycache__/*" | \
    xargs -I{} python3 -m py_compile {} 2>&1 | head -20
elif [ -f "package.json" ]; then
  echo "Node.js project"
  npm run build 2>&1 | tail -20
fi
```

If build/syntax fails, STOP and fix before continuing.

### Phase 2: Type Check
```bash
# TypeScript
[ -f "tsconfig.json" ] && npx tsc --noEmit 2>&1 | head -30

# Python (если установлен pyright/mypy)
command -v pyright >/dev/null && pyright . 2>&1 | head -30
command -v mypy >/dev/null && mypy . --ignore-missing-imports 2>&1 | head -30
```

### Phase 3: Lint Check
```bash
# JavaScript/TypeScript
[ -f "package.json" ] && npm run lint 2>&1 | head -30

# Python
command -v ruff >/dev/null && ruff check . 2>&1 | head -30
# Fallback: базовые проверки
grep -rn "import pdb\|breakpoint()\|print(" --include="*.py" . 2>/dev/null | grep -v "test_\|#" | head -10
```

### Phase 4: Test Suite
```bash
# Python: найти и запустить тесты
if [ -d "tests" ] || find . -name "test_*.py" -not -path "*/node_modules/*" | head -1 | grep -q .; then
  python3 -m pytest tests/ -v --tb=short 2>&1 | tail -30
fi

# JS/TS
[ -f "package.json" ] && grep -q '"test"' package.json && npm test 2>&1 | tail -30
```

Report:
- Total tests: X
- Passed: X
- Failed: X
- Coverage: X% (if available)

### Phase 5: Security Scan
```bash
# Secrets (Python + JS)
grep -rn "sk-\|api_key\|password\s*=\|token\s*=\|SECRET" \
  --include="*.py" --include="*.js" --include="*.ts" --include="*.env" \
  . 2>/dev/null | grep -v "test_\|\.example\|#.*TODO\|node_modules" | head -10

# Python: hardcoded credentials
grep -rn "BOT_TOKEN\s*=\s*['\"]" --include="*.py" . 2>/dev/null | head -5

# Debug leftovers
grep -rn "console\.log\|print(\|debugger\|pdb\.set_trace\|breakpoint()" \
  --include="*.py" --include="*.js" --include="*.ts" \
  . 2>/dev/null | grep -v "test_\|node_modules\|logging" | head -10

# HTML: external CDN (автономность)
grep -rn "cdn\.\|googleapis\|unpkg\|jsdelivr" --include="*.html" . 2>/dev/null | head -5
```

### Phase 6: Diff Review
```bash
# Show what changed
git diff --stat
git diff HEAD~1 --name-only 2>/dev/null || git diff --name-only
```

Review each changed file for:
- Unintended changes
- Missing error handling
- Potential edge cases
- **Python**: забытый `await`, shadowing imports (п.7 self-corrections)
- **Bots**: FSM state transitions, handler без декоратора
- **HTML**: внешние зависимости, viewport, lang

## Output Format

After running all phases, produce a verification report:

```
VERIFICATION REPORT
==================

Build:     [PASS/FAIL]
Types:     [PASS/FAIL] (X errors)
Lint:      [PASS/FAIL] (X warnings)
Tests:     [PASS/FAIL] (X/Y passed, Z% coverage)
Security:  [PASS/FAIL] (X issues)
Diff:      [X files changed]

Overall:   [READY/NOT READY] for PR

Issues to Fix:
1. ...
2. ...
```

## Continuous Mode

For long sessions, run verification every 15 minutes or after major changes:

```markdown
Set a mental checkpoint:
- After completing each function
- After finishing a component
- Before moving to next task

Run: /verify
```

## Связь с другими скиллами

| Скилл | Когда | Отношение |
|-------|-------|-----------|
| `superpowers:verification-before-completion` | Перед "готово" | Логический чеклист ("всё учёл?") → потом этот скилл (техническая проверка) |
| `/code-review` | После 5+ файлов | Ревью логики кода → потом этот скилл (build/lint/test) |
| `/code-audit` | Крупный рефактор | Глубокий аудит 4 агентами → потом этот скилл (финальная верификация) |

**Порядок:** code-review → verification-loop → superpowers:verification-before-completion

## Integration with Hooks

Автотриггер: `post-edit-skill-trigger.sh` при 15+ изменениях в сессии.
Хуки `post-edit-lint.sh` и `post-html-seo-check.sh` ловят проблемы ПО ХОДУ.
Этот скилл — комплексная проверка ПЕРЕД финализацией.
