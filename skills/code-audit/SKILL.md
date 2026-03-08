---
name: code-audit
description: >-
  Параллельный аудит кодовой базы 4 агентами: security, code quality, architecture balance, platform/deployment.
  Синтезирует результаты в HTML-отчёт с CSS-only графиками. Стоимость ~$0.40, время ~2.5 мин.
  Триггеры: code audit, аудит кода, аудит репо, проверь код, security audit, ревью кода,
  проверка безопасности, quality audit.
argument-hint: "[repo-path-or-url] [focus-areas]"
user-invocable: true
allowed-tools: Read Write Edit Bash Glob Grep Agent WebSearch
---

## WORKFLOW

### Step 0: Preparation
- If URL given → clone repo to temp dir
- If local path → use directly
- Create backup branch: `git checkout -b backup-pre-audit-$(date +%Y%m%d)`
- Fork to artvision-agency if external repo (safety net)
- Count files: `find . -name "*.py" -o -name "*.js" -o -name "*.ts" | wc -l`

### Step 1: Launch 4 Parallel Agents (SINGLE message, all at once)

| Agent | subagent_type | Focus |
|-------|--------------|-------|
| Security | security-auditor | XSS, injection, auth, secrets, dependencies |
| Code Quality | code-reviewer | patterns, complexity, DRY, naming, tests |
| Architecture | architect-reviewer | balance frontend/backend, separation, scalability |
| Platform | seo-specialist or devops-engineer | deployment, CI/CD, platform-specific issues |

Each agent prompt:
```
ANALYZE ONLY. Do not modify files.
Repository: [path]
Focus: [aspect]
Report format:
## [Category]
### CRITICAL (must fix)
- [file:line] Description
### HIGH (should fix)
- [file:line] Description
### MEDIUM (nice to have)
- [file:line] Description
### LOW
- [file:line] Description
```

### Step 2: Synthesize Results
- Collect all 4 agent outputs
- Deduplicate (agents may report same issues)
- Create consolidated finding list sorted by severity
- Count: CRITICAL, HIGH, MEDIUM, LOW per category

### Step 3: Generate HTML Report
Self-contained HTML with:
- Dark theme (bg: #1a1a2e, text: #e0e0e0)
- CSS-only charts (NO Chart.js/D3):
  - Horizontal bars: `.hbar` with `width:%` inline style
  - Vertical bars: `.vbar-chart` with `height:%`, flex-end
  - Donut: `conic-gradient()` on border-radius:50%
- Badge system: CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=green
- Sections: Executive Summary, Security, Quality, Architecture, Platform
- TOP-5 findings with fix instructions
- Roadmap: Week 1 (critical), Week 2 (high), Week 3-4 (medium)

Save to: `[repo]/docs/audit-report-[date].html` or specified output path.

### Step 4: Summary
Print to user:
- Total findings by severity
- TOP-3 critical issues
- Estimated fix time
- Link to HTML report

## Lessons Learned
- Git conflicts are #1 problem — split files between fixers (if fix phase added)
- Agents can't communicate — all coordination through orchestrator
- Always `git checkout master` before committing (not backup branch)
- CSS-only charts: hbar with width:%, vbar with height:% flex-end, donut with conic-gradient()
