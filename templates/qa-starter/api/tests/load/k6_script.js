// k6 load test. Run:  k6 run tests/load/k6_script.js
// Install k6: https://k6.io/docs/get-started/installation/
//
// Env:
//   BASE_URL    — target API (default http://localhost:8000)
//   K6_VUS      — virtual users (default 20)
//   K6_DURATION — duration (default 30s)

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const errorRate = new Rate("errors");
const apiLatency = new Trend("api_latency");

const BASE = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  scenarios: {
    steady_load: {
      executor: "constant-vus",
      vus: Number(__ENV.K6_VUS || 20),
      duration: __ENV.K6_DURATION || "30s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],        // <1% errors
    http_req_duration: ["p(95)<500", "p(99)<1000"],
    errors: ["rate<0.01"],
  },
};

export default function () {
  // GET /health
  let res = http.get(`${BASE}/health`);
  apiLatency.add(res.timings.duration);
  const healthOk = check(res, {
    "GET /health -> 200": (r) => r.status === 200,
    "health body has status": (r) => r.json("status") !== undefined,
  });
  errorRate.add(!healthOk);

  // GET /users?limit=20
  res = http.get(`${BASE}/users?limit=20`);
  apiLatency.add(res.timings.duration);
  const listOk = check(res, {
    "GET /users -> 200": (r) => r.status === 200,
    "returns array": (r) => Array.isArray(r.json()),
  });
  errorRate.add(!listOk);

  sleep(0.2 + Math.random() * 0.3);
}

export function handleSummary(data) {
  return {
    "reports/k6-summary.json": JSON.stringify(data, null, 2),
    stdout: textSummary(data),
  };
}

function textSummary(data) {
  const m = data.metrics;
  const p = (name, key = "p(95)") =>
    m[name] && m[name].values[key] !== undefined ? m[name].values[key].toFixed(2) : "n/a";
  return (
    `\n=== k6 summary ===\n` +
    `http_req_duration  p95=${p("http_req_duration")}ms  p99=${p("http_req_duration", "p(99)")}ms\n` +
    `http_req_failed    rate=${((m.http_req_failed?.values.rate || 0) * 100).toFixed(2)}%\n` +
    `iterations         ${m.iterations?.values.count ?? 0}\n`
  );
}
