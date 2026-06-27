# Session Context Anchors

Always make durable task context explicit instead of relying on model memory.

## Project Session Brief

When starting, resuming, or continuing substantial work in a project/client folder:

1. Look for the nearest `SESSION.md` from the current working directory upward.
2. If there is no nearby file and the task is substantial project/client work, create one with:
   `/Users/antonk/artvision-data/.agents/skills/artvision-session-context/scripts/ensure-session.sh "$PWD"`
3. If there is no nearby file but the task clearly belongs to an existing client/page root, check likely roots under `/Users/antonk/artvision-data/clients/`.
4. Read it before planning or editing.
5. Update it when the objective, references, selected assets, TODO state, deploy URL, or verification state materially changes.

For UoSmile docyurov clone, the current brief is:

`/Users/antonk/artvision-data/clients/usmile/pages/docyurov-usmile/SESSION.md`

## Agents And Commands Registry

When the user mentions agents, subagents, swarm, рой, консилиум, cons, slash commands, Codex, Claude commands, or asks what tools are available, read:

`/Users/antonk/artvision-data/AGENTS_COMMANDS_REGISTRY.md`

Use it as the shared source of truth for:

- Claude `/cons`, `/swarm`, `/run-agent`, `/explain-agents`;
- Codex `multi_agent_v1.spawn_agent`, `wait_agent`, `send_input`, `close_agent`;
- the difference between thinking/decision workflows and doing/fix/verify workflows.

## Rule Of Thumb

- `SESSION.md` answers: "why does this session exist and what is left?"
- `AGENTS_COMMANDS_REGISTRY.md` answers: "which orchestration command or agent layer should be used?"

## Mandatory Session Footer

At the end of final user-facing answers for substantial project/client work, include a compact session footer from the active `SESSION.md`.

Preferred command:

`/Users/antonk/artvision-data/.agents/skills/artvision-session-context/scripts/session-footer.sh "$PWD"`

If the command is not run, include the same information manually:

`📌 Session: <theme> | TODO: <done>/<total> | URL: <target> | Lead: <active runtime>`

Keep it one line. Do not duplicate the whole TODO list unless the user asks.
