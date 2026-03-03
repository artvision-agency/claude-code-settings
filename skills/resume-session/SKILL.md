---
name: resume-session
description: >-
  Read a previous Claude Code session log and summarize it for continuation in the current session.
  Use when the user wants to resume, review, or continue work from a past session without opening
  a new terminal. Triggers: 'resume session', 'read session', 'continue session', 'что было в сессии',
  'покажи сессию', 'resume <id>'.
argument-hint: <session_id or number> [--last N]
user-invocable: true
allowed-tools: Bash(python3 *) Read Grep
metadata:
  author: artvision
  version: "1.0"
  category: workflow
---

# Resume Session

Read and summarize a previous Claude Code session from its JSONL log.

## Arguments

`{{ARGUMENTS}}` — session ID (full or partial UUID), session name, or number from `claude-sessions`.

Optional flags:
- `--last N` — show only last N message pairs (useful for long sessions)

## Workflow

### Step 1: Find the session

If no argument provided, list recent sessions:
```bash
claude-sessions 2>&1 | head -30
```
Then ask which session to resume.

If argument is a name or number, proceed to Step 2.

### Step 2: Extract conversation

```bash
python3 ~/.claude/skills/resume-session/scripts/extract-session.py "{{ARGUMENTS}}" --last 40
```

For very large sessions (>5MB), use `--last 20` to avoid context overflow.

### Step 3: Summarize

After reading the extracted conversation, provide a **structured summary**:

```
## Session Summary: <topic>

**Theme:** one-line description
**Duration:** N user messages, M claude responses

### What was done:
- bullet points of completed work

### Where it stopped:
- last action / state

### Unfinished:
- what wasn't completed
- next steps if any

### Key decisions:
- important choices made during the session

### Files touched:
- list of files modified (if visible from tool calls)
```

### Step 4: Offer to continue

Ask: "Want to continue this work here, or need specific parts from that session?"

## Important

- Do NOT try to launch `claude --resume` from within a session — nested sessions are blocked
- Session files are in `~/.claude/projects/-Users-*/` as `.jsonl`
- Large sessions (>10MB) — use `--last 20` flag
- The script sorts by modification time, so number 1 = most recent session
