---
name: swarm
description: "Multi-agent Swarm orchestration. Launches parallel test/fix/verify agents with handoff between phases. Usage: /swarm [target] [task]. Coordinates agents, collects results, manages phases."
argument-hint: "[target-path] [task-description]"
---

# /swarm — Multi-Agent Swarm Orchestration

## What this does

Orchestrates multiple parallel agents through phases:
1. **Test/Analyze** — multiple agents examine the target in parallel
2. **Synthesize** — collect findings, create fix plan
3. **Fix/Execute** — agents apply fixes in parallel (non-overlapping files)
4. **Verify** — single agent confirms all fixes applied correctly

## Architecture

```
PHASE 1: PARALLEL ANALYSIS
┌─────────────┬─────────────┬─────────────┐
│  Agent A    │  Agent B    │  Agent C    │
│  (aspect 1) │  (aspect 2) │  (aspect 3) │
└──────┬──────┴──────┬──────┴──────┬──────┘
       │             │             │
       ▼             ▼             ▼
   Results A     Results B     Results C

SYNTHESIS: Claude collects all results, creates fix plan
           Groups fixes by FILE to avoid conflicts

PHASE 2: PARALLEL FIXES (non-overlapping files!)
┌─────────────┬─────────────┐
│  Fixer A    │  Fixer B    │
│  Files 1-15 │  Files 16-30│
└──────┬──────┴──────┬──────┘
       │             │
       ▼             ▼

PHASE 3: VERIFICATION
┌─────────────┐
│  Verifier   │
│  All files  │
└─────────────┘
```

## CRITICAL RULES

### Rule 1: NO FILE OVERLAP between fixers
Each fixer agent gets its OWN set of files. NEVER assign the same file to two agents.
This prevents git conflicts and race conditions.

### Rule 2: Disable auto-sync during fixes
Before launching fixers, ensure auto-sync hooks won't commit mid-fix.

### Rule 3: Sequential phases
DO NOT launch Phase 2 until ALL Phase 1 agents complete.
DO NOT launch Phase 3 until ALL Phase 2 agents complete.

### Rule 4: One commit per phase
After all fixers complete, make ONE commit with all changes.
Do not let individual agents commit separately.

## Execution Steps

### Step 0: Parse target and task

From user input, determine:
- **Target path**: directory with files to process
- **Task type**: test, fix, audit, transform, etc.
- **File list**: glob the target to get all files

### Step 1: Plan the analysis agents

Based on the task, determine 3-6 analysis aspects. Common patterns:

**For HTML pages:**
| Agent | Aspect | subagent_type |
|-------|--------|---------------|
| Structure | HTML validity, semantic markup, meta tags | frontend-developer |
| CSS | Styles, responsiveness, consistency | frontend-developer |
| Accessibility | WCAG, ARIA, contrast, keyboard nav | accessibility-tester |
| SEO | Schema.org, Open Graph, canonical, robots | seo-analyzer |
| Security | XSS, CSP, external deps, HTTPS | security-auditor |
| Content | Duplicates, empty blocks, broken links | code-reviewer |

**For code:**
| Agent | Aspect | subagent_type |
|-------|--------|---------------|
| Quality | Code review, patterns, complexity | code-reviewer |
| Security | Vulnerabilities, injection, auth | security-auditor |
| Tests | Coverage, edge cases, assertions | test-automator |
| Performance | Bottlenecks, memory, complexity | performance-engineer |

### Step 2: Launch Phase 1 (parallel)

Launch ALL analysis agents in a SINGLE message (parallel execution):

```
Task(subagent_type="frontend-developer", prompt="ANALYZE ONLY. Do not fix.
Report findings as structured list. Target: [path]. Focus: [aspect]...")

Task(subagent_type="code-reviewer", prompt="ANALYZE ONLY. Do not fix.
Report findings as structured list. Target: [path]. Focus: [aspect]...")
```

Use `run_in_background: true` for each, then poll with TaskOutput.

### Step 3: Collect and synthesize results

After ALL Phase 1 agents complete:
1. Read each agent's output
2. Deduplicate findings (agents may report same issues)
3. Prioritize: critical > important > nice-to-have
4. Group findings BY FILE (for non-overlapping assignment)

### Step 4: Create fix plan

Build a fix plan with file assignments:

```
Fixer A (files 1-15):
- Fix 1: [description] in files [list]
- Fix 2: [description] in files [list]

Fixer B (files 16-30):
- Fix 3: [description] in files [list]
- Fix 4: [description] in files [list]
```

Show the plan to the user. Wait for approval if there are risky changes.

### Step 5: Launch Phase 2 (parallel fixers)

Launch fixer agents with explicit instructions:

```
Task(subagent_type="frontend-developer", prompt="
FIX the following issues. Only modify YOUR assigned files.
DO NOT git commit — the orchestrator will commit after all fixers complete.

YOUR FILES (only touch these!):
[file list]

FIXES TO APPLY:
[fix instructions with before/after examples]

VERIFY after fixing:
[grep commands to confirm fixes]
")
```

### Step 6: Commit all changes

After ALL fixers complete:
```bash
git add [all modified files]
git commit -m "fix: [description of all fixes]"
git push
```

### Step 7: Launch Phase 3 (verification)

```
Task(subagent_type="code-reviewer", prompt="
VERIFY that ALL the following fixes were applied correctly across ALL files.
Report any remaining issues.

Expected state:
[list of grep checks that should pass]
[list of grep checks that should return 0 matches]
")
```

### Step 8: Report

Show final summary:
- Issues found (Phase 1)
- Fixes applied (Phase 2)
- Verification result (Phase 3)
- Files modified
- Commit hash

## Examples

```
/swarm clients/ant-partners/templates/output_v7/ "test all HTML pages for bugs"
/swarm src/ "audit code quality and fix issues"
/swarm clients/geely-a2auto/content/ "check all blog posts for SEO issues"
```

## Lessons Learned (2026-02-08)

1. **Git conflicts are the #1 problem** — ALWAYS split files between fixers
2. **Auto-sync hooks interfere** — they commit changes before fixers finish
3. **Agents can't communicate** — all coordination goes through the orchestrator
4. **Python scripts are best for bulk edits** — Write tool for 1 file, Python for 30+
5. **Background agents lose bash permissions** — prefer Read/Write/Edit over Bash in agents
