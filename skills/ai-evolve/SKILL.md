---
name: ai-evolve
description: Self-improve Artvision skills and CLAUDE.md based on client patches, context logs, and codebase patterns. Analyzes what went wrong across all clients, finds patterns, and enhances skills/rules. Use when you want to make Claude smarter. Triggers: 'evolve', 'улучши скиллы', 'самообучение', 'auto-improve'.
argument-hint: [skill-name or "all"]
allowed-tools: Read Write Edit Glob Grep Bash(git *) Bash(python3 *context_logger*) AskUserQuestion
disable-model-invocation: true
---

# Evolve — Self-Improvement for Artvision

Analyze client patches, context decisions, and codebase to improve existing skills and CLAUDE.md rules.

## Core Idea

```
clients/*/patches/*.md (past mistakes per client)
  + context/decisions/*.jsonl (past decisions)
  + context/prompts/*.jsonl (successful prompts)
    ↓
analyze recurring problems, client-specific pitfalls, cross-client patterns
    ↓
enhance skills with project-specific rules, update CLAUDE.md
```

## Workflow

### Step 1: Collect Intelligence

**1.1: Read ALL client patches**

```
Glob: /Users/antonk/artvision-data/clients/*/patches/*.md
```

Read every patch. For each one, extract:
- **Client** — which client had the issue
- **Problem category** (design, seo, content, tech, process)
- **Root cause pattern** — what class of mistake
- **Prevention rule** — what should be done differently
- **Tags**

**1.2: Read context decisions (last 30 days)**

```bash
python3 /Users/antonk/artvision-data/scripts/context_logger.py --list --days 30
```

**1.3: Read successful prompts**

```
Glob: /Users/antonk/artvision-data/context/prompts/*.jsonl
```

**1.4: Aggregate patterns**

Group patches by tags and categories. Identify:
- **Recurring problems** — same tag appears 3+ times = systemic issue
- **Cross-client issues** — same mistake with different clients
- **Missing guards** — what checks could have prevented the bugs
- **Successful patterns** — prompts with quality >= 8

### Step 2: Determine What to Evolve

If `$ARGUMENTS` contains a specific skill name → evolve only that skill.
If `$ARGUMENTS` is "all" or empty → evolve all installed skills + CLAUDE.md rules.

Read each target:
```
Glob: ~/.claude/skills/*/SKILL.md
Read: /Users/antonk/artvision-data/CLAUDE.md
Read: ~/.claude/CLAUDE.md
```

### Step 3: Analyze Gaps

For each skill/rule, identify what's missing:

**3.1: Patch-driven gaps**
- Does a skill warn about the most common error categories? If not → add
- Does CLAUDE.md cover recurring patterns? If not → add rule
- Are there client-specific pitfalls that should be in client CLAUDE.md? → add

**3.2: Cross-client patterns**
- Same mistake in 2+ clients? → add to global CLAUDE.md
- Same mistake only in 1 client? → add to client patches (already there)

**3.3: Prompt patterns**
- Successful prompts (quality >= 8) not documented? → extract pattern, add to skill

### Step 4: Generate Improvements

For each gap, create a concrete improvement:

```markdown
## Improvement: [target (skill name or CLAUDE.md)]

### What
[Specific change to make]

### Why
[Which patches/patterns drove this change]

### Where
[Exact section to modify]

### Change
[The actual text to add/modify]
```

**Quality rules:**
- Each improvement MUST be traceable to a patch, decision, or prompt
- No generic advice — only evidence-based enhancements
- Minimal and focused — add, don't replace
- Preserve existing structure

### Step 5: Present & Apply

**5.1: Present improvements to user**

```
## Skill Evolution Report

Based on:
- X patches across Y clients analyzed
- Z recurring patterns found
- W successful prompts cataloged

### Proposed Improvements

#### CLAUDE.md (global)
1. **Add rule about X** — 3 patches across 2 clients
   → Add to ЧАСТЫЕ ОШИБКИ section

#### /page-create skill
1. **Add check for Y** — 2 patches in ANT Partners
   → Add to checklist

Apply these improvements?
- [ ] Yes, apply all
- [ ] Let me pick
- [ ] No, just save report
```

**5.2: Apply approved improvements** using Edit tool.

**5.3: Save evolution log**

```bash
python3 /Users/antonk/artvision-data/scripts/context_logger.py \
  --log "Evolve: [summary of improvements]" \
  --category process --tags "evolve,self-improve"
```

### Step 6: Commit & Sync

```bash
cd /Users/antonk/artvision-data && git add -A && git commit -m "refactor: evolve — [summary]

Co-Authored-By: Claude <noreply@anthropic.com>" && git push
```

Also sync to repo:
```bash
cp ~/.claude/skills/[modified-skill]/SKILL.md /Users/antonk/artvision-data/.claude/skills/[skill]/SKILL.md
```

## Important Rules

1. **Traceable** — every improvement links to a patch or decision
2. **Minimal** — add rules, don't rewrite skills
3. **Reversible** — user approves before changes
4. **Cumulative** — each evolution builds on previous
5. **No hallucination** — only evidence-backed suggestions
6. **Cross-client** — look for patterns across ALL clients, not just one

## DO NOT:
- Rewrite entire skills
- Remove existing rules
- Add generic advice ("write clean code")
- Apply changes without user approval
- Create new skills (suggest /skill-generator instead)
