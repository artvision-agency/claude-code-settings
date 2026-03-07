---
name: run-agent
description: "Load and run a custom agent from sub-agents.directory (129 agents, 300+ lines each). Usage: /run-agent [agent-name] [task]. Lists available agents if no name given."
argument-hint: "[agent-name] [task description]"
---

# /run-agent — Custom Agent Launcher

## What this does

Loads a custom agent prompt from `/Users/antonk/sub-agents.directory/content/` and executes
the given task using that agent's full 300+ line system prompt via the Task tool.

This solves the problem that `~/.claude/agents/` files are NOT loaded by the Task tool.
Instead, this skill reads the .md file and passes its content as the Task tool prompt.

## How it works

```
/run-agent competitive-analyst "analyze ant.partners competitors"
         │                      │
         ▼                      ▼
   Read .md file           Task description
         │
         ▼
   Task(subagent_type="general-purpose",
        prompt="[agent .md content]\n\n---\nTASK: [user task]")
```

## Execution Steps

### Step 1: Parse arguments

Extract `[agent-name]` and `[task]` from user input.

If no agent name given, list available agents:
```bash
ls /Users/antonk/sub-agents.directory/content/*/*.md | sed 's|.*/||;s|\.md||' | sort
```

### Step 2: Find the agent file

Search for the agent by name:
```bash
find /Users/antonk/sub-agents.directory/content/ -name "[agent-name].md" -type f
```

If not found, show closest matches using grep.

### Step 3: Read the agent file

Use the Read tool to load the full .md content (including frontmatter with name, description, tools).

### Step 4: Determine the best Task subagent_type

Map the agent's `tools:` field to the closest built-in subagent_type:

| Agent tools field | Best subagent_type |
|---|---|
| Contains "WebSearch", "WebFetch" | `research-analyst` or `competitive-analyst` |
| Contains "Write", "Edit", "Bash" | `frontend-developer` or `backend-developer` |
| Contains only "Read", "Grep", "Glob" | `Explore` |
| General/mixed | `general-purpose` |

Also match by agent category:
- `01-core-development/` → matching dev type (frontend-developer, backend-developer, etc.)
- `04-quality-security/` → `code-reviewer`, `security-auditor`, etc.
- `10-research-analysis/` → `research-analyst`
- Default → `general-purpose`

### Step 5: Launch the agent

```
Task(
  subagent_type = [determined type],
  prompt = "[Full .md content]\n\n---\n\nTASK:\n[user's task description]"
)
```

### Step 6: Return results

Show the agent's output to the user.

## Agent Directory Structure

```
/Users/antonk/sub-agents.directory/content/
├── 01-core-development/       # api-designer, backend-developer, frontend-developer, fullstack
├── 02-language-specialists/   # angular, django, laravel, nextjs, golang, python, php
├── 03-infrastructure/         # devops, kubernetes, terraform, cloud-architect, sre
├── 04-quality-security/       # code-reviewer, qa-expert, security-auditor
├── 05-data-ai/                # data-engineer, ml-engineer, llm-architect
├── 06-developer-experience/   # documentation-engineer, refactoring-specialist
├── 07-specialized-domains/    # seo-specialist, fintech, blockchain, game-developer
├── 08-business-product/       # product-manager, technical-writer, ux-researcher
├── 09-meta-orchestration/     # multi-agent-coordinator, workflow-orchestrator
└── 10-research-analysis/      # competitive-analyst, market-researcher, trend-analyst
```

## Examples

```
/run-agent                                    → list all 129 agents
/run-agent competitive-analyst                → show agent description
/run-agent competitive-analyst "analyze ant.partners vs competitors in Moscow"
/run-agent seo-specialist "audit artvision.pro for technical SEO issues"
/run-agent wordpress-master "review WP REST API integration for artvision.pro"
```

## Important Notes

- The agent's .md content becomes the system prompt for the Task tool agent
- Each invocation uses an isolated context (Task tool = separate context window)
- The built-in subagent_type provides tool access (Read, Write, Bash, etc.)
- The .md content provides domain expertise and workflow instructions
- Cost: ~300 lines of prompt overhead per invocation
