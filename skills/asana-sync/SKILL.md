---
name: asana-sync
description: >
  This skill should be used when the user types "/asana", "асана", "синк асана",
  "asana sync", or asks to sync sessions with Asana tasks. Collects Claude Code
  sessions for the day, matches them against Asana tasks, creates missing tasks,
  and updates deadlines.
---

# Asana Session Sync

Synchronize Claude Code sessions with Asana tasks — ensure every work session
has a corresponding tracked task with proper project assignment and deadline.

## Workflow

### 1. Collect Today's Sessions

Run the collection script to extract session summaries:

```bash
python3 ~/.claude/skills/asana-sync/scripts/collect_sessions.py
```

The script outputs JSON with session ID, first user message, size, and timestamp.

### 2. Get Asana Workspace & Projects

Use `mcp__asana__asana_list_workspaces` to get workspace GID.
Then `mcp__asana__asana_search_projects` to list all projects.

### 3. Search Existing Tasks

For each session, search Asana for matching tasks:
- Use `mcp__asana__asana_search_tasks` with `text` parameter matching session topic
- Check `completed: false` to find active tasks
- Match by session keywords from first user message

### 4. Create or Update Tasks

For sessions without matching Asana tasks:
- Determine the correct project from session content (client name → project)
- Use `mcp__asana__asana_create_task` with:
  - `name`: concise task title from session topic
  - `notes`: session ID for traceability + brief description
  - `due_on`: today or next business day
  - `assignee`: "me"
  - `project_id`: matched project GID

For existing tasks that need updates:
- Use `mcp__asana__asana_update_task` to update due date or notes

### 5. Report

Display a summary table:

| Сессия | Тема | Asana | Действие |
|--------|------|-------|----------|
| abc123 | ANT Partners slugs | ✅ Existing | Updated |
| def456 | Варикоз созвон | ✅ Created | New task |
| ghi789 | Voice mode check | ⏭️ Skipped | Informational |

## Project Matching Rules

Map session content to Asana projects by keywords:

| Ключевое слово | Проект Asana |
|----------------|-------------|
| ant, ant-partners, ант парт | ANT.partners |
| otido, отидо | Otido-group |
| extru, экстру | Extru-Tech |
| atribeaute, атрибьют | Атрибьют |
| varikoz, варикоз, advertmed | Presale: AdvertMed |
| symmetron, симметрон | Presale: Symmetron |
| madwave | Madwave |
| ai vision, ai.artvision | AI Vision |
| structural, stressedskin | Structural Engineering |
| портной | Передвижной портной |
| loyalmed | LoyalMed Конкурент |

Sessions that are purely informational (voice mode check, sync, short commands)
should be skipped — mark as "⏭️ Skipped" in the report.

## Skip Criteria

Skip creating tasks for sessions that are:
- Under 5KB (too small to be meaningful work)
- First message is a resume/continuation (`--resume`, `--continue`)
- Purely meta (sync, git, voice check, session lookup)
- Already have a matching task in Asana

## Error Handling

If Asana API returns "Payment Required" (rate limit):
- Wait 60 seconds and retry once
- If still failing, save pending tasks to `~/.claude/asana-pending.json`
- Report which tasks could not be synced

## Scripts

- **`scripts/collect_sessions.py`** — Extract and summarize today's sessions
