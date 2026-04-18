"""Locust load test (Python alternative to k6).

Install:
    pip install locust

Run UI:
    locust -f tests/load/locustfile.py --host http://localhost:8000

Headless (CI-friendly):
    locust -f tests/load/locustfile.py --host http://localhost:8000 \\
        --headless -u 50 -r 10 -t 30s --html reports/locust.html

Flags:
    -u  — total users (peak)
    -r  — spawn rate (users per second)
    -t  — duration
"""

from __future__ import annotations

import random

from locust import HttpUser, between, events, task


class ApiUser(HttpUser):
    wait_time = between(0.2, 0.6)

    @task(3)
    def health(self) -> None:
        self.client.get("/health", name="/health")

    @task(5)
    def list_users(self) -> None:
        self.client.get("/users?limit=20", name="/users?limit=20")

    @task(1)
    def get_random_user(self) -> None:
        user_id = random.randint(1, 100)
        self.client.get(f"/users/{user_id}", name="/users/:id")

    @task(1)
    def create_user(self) -> None:
        payload = {
            "name": f"user_{random.randint(1, 10_000)}",
            "email": f"user{random.randint(1, 10_000)}@example.com",
        }
        self.client.post("/users", json=payload, name="/users POST")


# Optional: fail the whole run if SLO is violated in headless mode.
@events.quitting.add_listener  # type: ignore[misc]
def _check_slos(environment, **_kwargs: object) -> None:  # type: ignore[no-untyped-def]
    stats = environment.stats
    total = stats.total
    if total.num_requests == 0:
        return
    p95 = total.get_response_time_percentile(0.95)
    fail_rate = total.num_failures / total.num_requests
    print(f"[locust] p95={p95:.0f}ms fail_rate={fail_rate * 100:.2f}%")
    if p95 > 500 or fail_rate > 0.01:
        environment.process_exit_code = 1
