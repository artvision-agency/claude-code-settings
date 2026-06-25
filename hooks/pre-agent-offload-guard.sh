#!/usr/bin/env bash
# pre-agent-offload-guard.sh — PreToolUse(Agent)
# Блокирует запуск Opus-субагента (research-типа) на ОФФЛОУДАБЕЛЬНУЮ задачу
# (веб-ресёрч/разбор данных БЕЗ нашего приватного контекста) — её надо вести
# через round_table (FREE) / Codex / Gemini, не жечь Max-квоту Opus-роем.
# Правило: offload-heavy-to-cheaper-models.md. Прецедент: 2026-06-25 ROSTELEKOM
# (3 Opus research-analyst на обычный веб-поиск, 1 умер вернув 0).
# Bypass: OFFLOAD_OK=1

[ "${OFFLOAD_OK:-0}" = "1" ] && exit 0

input=$(cat)

# subagent_type и prompt из tool_input
sub=$(printf '%s' "$input" | python3 -c 'import sys,json
try:
  d=json.load(sys.stdin); ti=d.get("tool_input",{})
  print((ti.get("subagent_type") or "").lower())
except: print("")' 2>/dev/null)

prompt=$(printf '%s' "$input" | python3 -c 'import sys,json
try:
  d=json.load(sys.stdin); ti=d.get("tool_input",{})
  print((ti.get("prompt") or "").lower())
except: print("")' 2>/dev/null)

# только research/data-типы агентов = кандидаты на оффлоуд
case "$sub" in
  research-analyst|data-researcher|market-researcher|search-specialist|competitive-analyst|trend-analyst) ;;
  *) exit 0 ;;
esac

# сигнал «веб-ресёрч/разбор» (оффлоудабельно)
echo "$prompt" | grep -qiE 'websearch|webfetch|интернет|существует ли|есть ли|цена|тариф|стоимость|рисёрч|рисерч|research|найди|конкурент|обзор рынка|сколько стоит' || exit 0

# приватный контекст → НЕ блокировать (нужны наши данные)
if echo "$prompt" | grep -qiE 'clients/|tokens\.json|access\.md|наш(и|его)? (клиент|правил|секрет|данны)|приватн|context-log|внутренн'; then
  exit 0
fi

cat >&2 <<'MSG'
⛔ pre-agent-offload-guard: Opus-рой на ОФФЛОУДАБЕЛЬНУЮ задачу (веб-ресёрч/разбор без нашего приватного контекста).

Каждый Opus-субагент = +полный дамп правил (~110K input) по Max-цене.
Веди такую задачу дешевле (правило offload-heavy-to-cheaper-models.md):
  • round_table (FREE Groq) — mcp__llm-consilium__round_table
  • Codex (subagent_type codex:codex-rescue) — другой биллинг
  • Gemini (gemini-rescue) — FREE / другой биллинг
  • лёгкие WebSearch в main-процессе (без роя)

Opus-рой оправдан ТОЛЬКО когда нужен наш приватный контекст (клиент/правила/секреты).
Bypass: OFFLOAD_OK=1
MSG
exit 2
