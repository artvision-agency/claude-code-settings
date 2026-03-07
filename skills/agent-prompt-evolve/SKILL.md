---
name: agent-prompt-evolve
description: >-
  Self-improvement of agent system prompts through skill absorption.
  Analyzes agent performance, extracts missing capabilities from available skills,
  and enriches agent prompts with new abilities. Works with sub-agents.directory
  agents and custom agents. Validates improvements from multiple sources before
  applying. Triggers: 'improve agent prompt', 'agent self-improve',
  'evolve agent', 'обучи агента', 'улучши промпт агента',
  'agent learning', 'agent skill absorption', 'приклей скилл к агенту',
  'agent enrichment', 'наделить агента', 'прокачай агента'
user-invocable: true
disable-model-invocation: false
allowed-tools: Read Write Edit Bash Grep Glob Agent WebSearch
metadata:
  author: artvision
  version: "1.0"
  category: agent-infrastructure
  based-on: "Voyager (NVIDIA), SAGE, 4-Gate Validation model"
---

# Agent Prompt Evolve

Improve agent system prompts by discovering and absorbing capabilities
from skills, session history, and external sources.

## Core Concept

```
Agent Prompt (who I am)
    +
Skill (what I can do)     →  ENRICHED Agent Prompt (who I am + new abilities)
    +
Validation (is it safe?)
```

An agent's system prompt defines its identity and capabilities.
This skill analyzes gaps and enriches the prompt with new abilities
extracted from skills, patterns, and verified sources.

## Modes

### Mode 1: Gap Analysis
`/agent-prompt-evolve analyze <agent-name>`

1. Read agent's current prompt (from `~/.claude/agents/` or sub-agents.directory)
2. Run agent on a test task
3. Identify where the agent struggled or produced weak output
4. Search available skills for capabilities that would help
5. Report gaps with recommended skill absorptions

### Mode 2: Skill Absorption
`/agent-prompt-evolve absorb <agent-name> <skill-name>`

1. Read the target agent's current system prompt
2. Read the skill's SKILL.md
3. Extract candidate capability (what agent would gain)
4. **Run 5-Gate Proficiency Validation** (see below):
   - Gate 1: Purpose alignment (internal reasoning)
   - Gate 2: Factual accuracy (WebSearch 2+ sources per claim)
   - Gate 3: Best practices (search official docs, current standards)
   - Gate 4: Contradiction check (diff with existing prompt)
   - Gate 5: Behavioral test (3 tasks, before vs after)
5. If ALL gates pass → extract and adapt instructions
6. Rewrite agent prompt with new capability in "Absorbed" section
7. Save with changelog + validation report + source URLs

### Mode 3: Auto-Evolve
`/agent-prompt-evolve auto <agent-name>`

1. Read last 3 session logs where this agent was used
2. Extract patterns: what worked, what failed, what was missing
3. Search skills library for matching capabilities
4. Run 3-source validation on each candidate
5. Apply all validated improvements
6. Generate diff report

### Mode 4: Create From Skills
`/agent-prompt-evolve create <new-agent-name> <skill1> <skill2> ...`

1. Read each skill
2. Synthesize a new agent prompt combining capabilities
3. Validate: no conflicts between skills, coherent identity
4. Write to `~/.claude/agents/<new-agent-name>.md`

## 5-Gate Proficiency Validation Pipeline

NEVER absorb a capability into an agent prompt without passing ALL 5 gates.
Each gate uses EXTERNAL reliable sources, not the skill's own claims.

```
GATE 1: PURPOSE ALIGNMENT (internal check)
├── Does the capability serve the agent's role?
├── Would a human expert in this role use this?
├── Is it within the agent's domain or overreach?
└── Score: 0-10 (threshold: 7+)
└── Method: LLM reasoning

GATE 2: FACTUAL ACCURACY (external sources)
├── Extract all factual claims from the capability
├── For EACH claim, verify against 2+ reliable sources:
│   ├── Official documentation (MDN, Python docs, RFC, etc.)
│   ├── Academic papers (arxiv, Google Scholar)
│   ├── Industry reports (Statista, SensorTower, data.ai)
│   ├── Official APIs / changelogs
│   └── Reputable tech publications (not blogs/forums)
├── Flag unverifiable claims as [UNVERIFIED]
├── Remove or mark claims verified by only 1 source as [WEAK]
└── Score: % of claims verified by 2+ sources (threshold: 80%+)
└── Method: WebSearch + WebFetch per claim, log sources

GATE 3: BEST PRACTICES CHECK (professional standards)
├── Does the approach match industry best practices?
├── Search for:
│   ├── Official style guides (Google, Airbnb, PEP8, etc.)
│   ├── Framework documentation (latest stable version)
│   ├── Security advisories (OWASP, CVE databases)
│   └── Conference talks / expert opinions (last 12 months)
├── Check for deprecated patterns or outdated advice
├── Verify version numbers and compatibility
└── Score: 0-10 (threshold: 7+)
└── Method: WebSearch for "[topic] best practices 2026"

GATE 4: CONTRADICTION CHECK (existing prompt)
├── Does new capability contradict existing agent abilities?
├── Does it duplicate something already in the prompt?
├── Does it change the agent's personality/tone?
├── Would merging create ambiguous instructions?
└── Score: PASS/FAIL
└── Method: Diff analysis between old and new prompt

GATE 5: BEHAVIORAL TEST (live proof)
├── Run agent WITHOUT new capability on 3 test tasks → baseline
├── Run agent WITH new capability on same 3 tasks → enriched
├── Compare:
│   ├── Quality: is output measurably better?
│   ├── Regression: did anything that worked before break?
│   ├── Token usage: did prompt bloat slow things down?
│   └── Coherence: does agent still have clear identity?
└── Score: enriched must beat baseline on 2/3 tasks, 0 regressions
└── Method: Agent tool with before/after comparison
```

### Gate Results Format

```
VALIDATION REPORT: [capability] → [agent]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Gate 1 (Purpose):     8/10  PASS
Gate 2 (Facts):       12/15 claims verified (80%)  PASS
  - "Zalo has 75M MAU in Vietnam" → verified: TechInAsia, Statista
  - "BiP has 25M in Turkey" → verified: Turkcell IR, SimilarWeb
  - "UPI handles 85% payments" → [WEAK] only NPCI source
Gate 3 (Best Practice): 9/10  PASS
Gate 4 (Contradiction): PASS (no conflicts)
Gate 5 (Behavioral):   3/3 tasks improved, 0 regressions  PASS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERDICT: ABSORB (all gates passed)
Sources: 8 external, 0 unverified claims remaining
```

### Source Reliability Tiers

| Tier | Source Type | Trust Level |
|------|-----------|-------------|
| A | Official docs, RFCs, academic papers, gov data | Full trust |
| B | Major tech publications, industry reports, official blogs | High trust |
| C | Stack Overflow (high-vote), reputable tutorials, conference talks | Moderate |
| D | Personal blogs, forums, Reddit, AI-generated content | Low — needs A/B confirmation |
| F | Skill's own claims about itself, unverifiable statements | Zero trust |

**Rule: Every absorbed fact must have at least 1 Tier A/B source.**
If only Tier C/D available → mark as [UNVERIFIED] in agent prompt.

ALL five gates must pass. If any fails, DO NOT absorb. Report which gate failed and why.

## Agent Prompt Structure

When enriching, maintain this structure:

```markdown
# Agent: <name>

## Identity (WHO — never change without permission)
<role, expertise, personality>

## Core Capabilities (WHAT — original abilities)
<existing capabilities>

## Absorbed Capabilities (WHAT — from skills)
<new capabilities with source attribution>
### From: <skill-name> (absorbed <date>)
<extracted and adapted instructions>

## Tools & Methods (HOW)
<tools available, preferred approaches>

## Constraints (WHAT NOT)
<boundaries, limitations, safety rules>

## Changelog
| Date | Skill | What Changed | Validation Score |
```

## Key Rules

### DO:
- Keep agent identity intact — skills ADD abilities, don't replace personality
- Attribute every absorbed capability to its source skill
- Version every change with date and validation scores
- Test before and after on real tasks
- Prefer extracting PRINCIPLES over copying INSTRUCTIONS verbatim
- Merge overlapping capabilities (don't duplicate)

### DON'T:
- Absorb a skill that contradicts the agent's core role
- Copy entire SKILL.md into agent prompt (extract, don't copy)
- Skip validation — even internal skills can degrade performance
- Grow prompt beyond 2000 tokens (diminishing returns, proven by research)
- Absorb without testing on sample tasks first

## Unbounded Growth Prevention

Research (Voyager, SAGE papers) shows skill libraries degrade past a critical size.

**Limits:**
- Max 5 absorbed capabilities per agent
- Each absorption must improve measurable output quality
- Quarterly review: remove capabilities with <20% usage
- If prompt exceeds 2000 tokens → compress or remove least-used

## Integration with Existing Skills

This skill works with:
- `/ai-evolve` — evolves SKILL files (this skill evolves AGENT prompts)
- `/continuous-learning` — extracts patterns from sessions (this skill absorbs them)
- `/skill-generator` — creates new skills (this skill feeds them to agents)
- `/run-agent` — loads agents from directory (enriched agents live there)

## Example Flow

```
User: "прокачай агента market-researcher"

1. Read ~/.claude/agents/market-researcher.md (or sub-agents.directory)
2. Read last 3 sessions where market-researcher was used
3. Found: agent didn't know local payment methods per country
4. Search skills: /market-research has country microplan knowledge
5. Validate:
   - Source 1: Purpose alignment = 9/10 (directly relevant)
   - Source 2: Cross-check PIX/UPI/Kaspi data = verified
   - Source 3: Test on "research Vietnam market" = improved output
6. Extract: "For each country, research local payment methods..."
7. Insert into agent prompt under "Absorbed Capabilities"
8. Save + log change

Result: market-researcher now automatically includes local payments
```

## File Locations

| What | Where |
|------|-------|
| Agent prompts | `~/.claude/agents/*.md` |
| Sub-agents directory | `~/artvision-data/sub-agents.directory/` |
| Skills library | `~/.claude/skills/*/SKILL.md` |
| Session logs | `~/.claude/projects/*/sessions/` |
| Enrichment logs | `~/artvision-data/docs/agent-enrichments.log` |
