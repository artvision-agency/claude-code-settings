"""Stress test: 10 concurrent virtual users hammering the bot.

Measures end-to-end latency (send → first bot reply) at p50/p95/p99.
Uses Telethon userbot accounts — you need a pool of N session files.

Env vars:
    TG_API_ID, TG_API_HASH           — app credentials
    TG_BOT_USERNAME                  — target bot (e.g. @my_bot)
    TG_STRESS_SESSIONS               — comma-separated paths to session files
                                       (or directory with *.session files)
    TG_STRESS_USERS                  — default 10; cannot exceed number of sessions
    TG_STRESS_ITERATIONS             — messages per user (default 5)
    TG_STRESS_COMMAND                — command to send (default /start)

Run:
    pytest tests/stress/test_concurrent.py -s --run-integration
"""

from __future__ import annotations

import asyncio
import os
import statistics
import time
from pathlib import Path

import pytest
from telethon import TelegramClient


def _session_files() -> list[str]:
    raw = os.environ.get("TG_STRESS_SESSIONS", "")
    if not raw:
        return []
    if "," in raw:
        return [s.strip() for s in raw.split(",") if s.strip()]
    p = Path(raw)
    if p.is_dir():
        return [str(x) for x in sorted(p.glob("*.session"))]
    return [raw]


async def _one_user(
    session: str,
    api_id: int,
    api_hash: str,
    bot: str,
    command: str,
    iterations: int,
) -> list[float]:
    latencies: list[float] = []
    async with TelegramClient(session, api_id, api_hash) as client:
        for _ in range(iterations):
            start = time.perf_counter()
            sent = await client.send_message(bot, command)
            deadline = start + 15.0
            while time.perf_counter() < deadline:
                async for msg in client.iter_messages(bot, limit=3):
                    if msg.id > sent.id and msg.out is False:
                        latencies.append(time.perf_counter() - start)
                        break
                else:
                    await asyncio.sleep(0.1)
                    continue
                break
            # tiny gap to avoid back-to-back TG flood
            await asyncio.sleep(0.2)
    return latencies


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_10_users() -> None:
    api_id_s = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")
    bot = os.environ.get("TG_BOT_USERNAME", "").lstrip("@")
    if not (api_id_s and api_hash and bot):
        pytest.skip("TG_API_ID / TG_API_HASH / TG_BOT_USERNAME not set")

    sessions = _session_files()
    n_users = int(os.environ.get("TG_STRESS_USERS", "10"))
    if len(sessions) < n_users:
        pytest.skip(f"need {n_users} sessions, got {len(sessions)}")

    iterations = int(os.environ.get("TG_STRESS_ITERATIONS", "5"))
    command = os.environ.get("TG_STRESS_COMMAND", "/start")
    api_id = int(api_id_s)

    tasks = [
        _one_user(sessions[i], api_id, api_hash, bot, command, iterations)
        for i in range(n_users)
    ]
    results = await asyncio.gather(*tasks)
    latencies = [x for r in results for x in r]

    assert latencies, "no replies received — bot down or blocking"

    latencies.sort()
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    p99 = latencies[int(len(latencies) * 0.99) - 1]

    print(
        f"\n[stress] users={n_users} iterations={iterations} total={len(latencies)} "
        f"p50={p50:.2f}s p95={p95:.2f}s p99={p99:.2f}s"
    )

    # Soft SLOs — tune per bot.
    assert p50 < 2.0, f"p50 too high: {p50:.2f}s"
    assert p95 < 5.0, f"p95 too high: {p95:.2f}s"
    assert p99 < 10.0, f"p99 too high: {p99:.2f}s"
