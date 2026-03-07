---
name: production-readiness-checklist
description: Comprehensive checklist for deploying applications to production with Docker, monitoring, security, and CI/CD best practices
---

# Production Readiness Checklist

Use this checklist before every production deployment. Each section contains
actionable items with concrete configuration examples. Copy the checklist into
an issue or PR description and tick items off as you verify them.

---

## 1. Docker Configuration

### Production vs Development Compose

Maintain separate compose files. Use `docker-compose.yml` as the base and
`docker-compose.prod.yml` as the production override.

```yaml
# docker-compose.yml (base)
services:
  app:
    build:
      context: .
      target: production
    env_file: .env
    restart: unless-stopped

# docker-compose.prod.yml (override)
services:
  app:
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 1G
        reservations:
          cpus: "0.5"
          memory: 256M
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"
```

Run with: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

### Multi-Stage Builds

Keep images small. Use a builder stage for compilation and a slim runtime stage.

```dockerfile
# Stage 1 - build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2 - production
FROM node:20-alpine AS production
WORKDIR /app
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
USER appuser
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

### Non-Root User

Never run containers as root. Always create and switch to a dedicated user.

```dockerfile
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
```

Verify after build: `docker run --rm <image> whoami` should NOT print `root`.

### Health Checks

Define health checks in the Dockerfile or compose file so the orchestrator
knows when the service is truly ready.

```yaml
services:
  app:
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## 2. Process Management

### PM2 (Node.js without Docker)

```javascript
// ecosystem.config.js
module.exports = {
  apps: [
    {
      name: "app-prod",
      script: "dist/index.js",
      instances: "max",
      exec_mode: "cluster",
      max_memory_restart: "500M",
      env_production: {
        NODE_ENV: "production",
        PORT: 3000,
      },
      error_file: "/var/log/app/error.log",
      out_file: "/var/log/app/out.log",
      merge_logs: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
    },
  ],
};
```

Start: `pm2 start ecosystem.config.js --env production`
Save: `pm2 save && pm2 startup`

### Docker Restart Policies

Use `unless-stopped` for most services. Use `on-failure` with a retry limit for
jobs that should not restart indefinitely.

```yaml
services:
  app:
    restart: unless-stopped       # restarts unless manually stopped
  worker:
    restart: on-failure
    deploy:
      restart_policy:
        condition: on-failure
        max_attempts: 5
        delay: 10s
```

### Graceful Shutdown

Handle SIGTERM and SIGINT to close connections cleanly before the process exits.

```javascript
const server = app.listen(PORT);

async function gracefulShutdown(signal) {
  console.log(`Received ${signal}. Shutting down gracefully...`);
  server.close(() => {
    console.log("HTTP server closed.");
  });
  await database.disconnect();
  await cache.quit();
  process.exit(0);
}

process.on("SIGTERM", () => gracefulShutdown("SIGTERM"));
process.on("SIGINT", () => gracefulShutdown("SIGINT"));
```

Set `stop_grace_period: 30s` in compose to give the app time before Docker
sends SIGKILL.

---

## 3. Environment and Secrets

### NODE_ENV=production

Always set `NODE_ENV=production` in production. This enables optimizations in
Express, disables verbose error output, and tells npm to skip devDependencies.

### Secrets Management

Never commit `.env` files to version control.

**Option A -- `.env` files on the host (simple)**

```bash
# .env.production (kept on server, NOT in repo)
DATABASE_URL=postgresql://user:pass@db:5432/app
REDIS_URL=redis://cache:6379
JWT_SECRET=<generated-secret>
```

**Option B -- Docker secrets (Swarm / Compose v3.1+)**

```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt

services:
  app:
    secrets:
      - db_password
```

**Option C -- HashiCorp Vault / AWS Secrets Manager**

Fetch secrets at startup via the provider SDK. Rotate secrets without redeploying.

---

## 4. Logging

### Structured JSON Logs

Use a structured logger. Raw `console.log` strings are hard to parse in
aggregation systems.

**Node.js -- pino**

```javascript
import pino from "pino";

const logger = pino({
  level: process.env.LOG_LEVEL || "info",
  transport:
    process.env.NODE_ENV !== "production"
      ? { target: "pino-pretty" }
      : undefined,
  redact: ["req.headers.authorization", "body.password"],
});
```

**Python -- loguru**

```python
from loguru import logger
import sys

logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO",
    serialize=True,  # JSON output
)
```

### Log Levels

| Level | Use for |
|-------|---------|
| error | Unexpected failures needing immediate attention |
| warn  | Degraded state, recoverable issues |
| info  | Key business events (request handled, job completed) |
| debug | Diagnostic detail, disabled in production |

### Log Rotation

When writing to files, configure rotation to avoid filling the disk.

```yaml
# Docker logging driver
logging:
  driver: json-file
  options:
    max-size: "50m"
    max-file: "5"
```

For PM2: `pm2 install pm2-logrotate && pm2 set pm2-logrotate:max_size 50M`

---

## 5. Monitoring and Alerting

### Health Endpoints

Expose `/health` (liveness) and `/ready` (readiness) endpoints.

```javascript
app.get("/health", (req, res) => {
  res.json({ status: "ok", uptime: process.uptime() });
});

app.get("/ready", async (req, res) => {
  const dbOk = await checkDatabase();
  const cacheOk = await checkRedis();
  const allOk = dbOk && cacheOk;
  res.status(allOk ? 200 : 503).json({ db: dbOk, cache: cacheOk });
});
```

### Prometheus Metrics

Use `prom-client` (Node.js) or `prometheus_client` (Python) to expose a
`/metrics` endpoint.

```javascript
import client from "prom-client";

client.collectDefaultMetrics();

const httpDuration = new client.Histogram({
  name: "http_request_duration_seconds",
  help: "Duration of HTTP requests in seconds",
  labelNames: ["method", "route", "status"],
  buckets: [0.01, 0.05, 0.1, 0.5, 1, 5],
});

app.get("/metrics", async (req, res) => {
  res.set("Content-Type", client.register.contentType);
  res.end(await client.register.metrics());
});
```

### Uptime Alerts

Use an external pinger (UptimeRobot, Healthchecks.io, or Grafana synthetic
monitoring) to hit `/health` every 60 seconds and alert on two consecutive
failures.

---

## 6. Database

### Migrations Strategy

Run migrations as a separate step before starting the application.

```yaml
services:
  migrate:
    image: myapp:latest
    command: ["npx", "prisma", "migrate", "deploy"]
    depends_on:
      db:
        condition: service_healthy
  app:
    depends_on:
      migrate:
        condition: service_completed_successfully
```

### Backups

Automate daily backups with cron or a sidecar container.

```bash
#!/bin/bash
# /scripts/backup-db.sh
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "/backups/db_${TIMESTAMP}.gz"
find /backups -name "*.gz" -mtime +30 -delete  # keep 30 days
```

### Connection Pooling

Use PgBouncer or the driver's built-in pool. Never open unlimited connections.

```javascript
// Prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")  // ?connection_limit=20&pool_timeout=10
}
```

---

## 7. Security

### HTTPS / TLS

Terminate TLS at the reverse proxy (Nginx, Caddy, Traefik) or load balancer.
Never expose plain HTTP to the internet.

```nginx
server {
    listen 443 ssl http2;
    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://app:3000;
    }
}
```

### CORS

Restrict origins to known front-end domains.

```javascript
app.use(cors({
  origin: ["https://app.example.com"],
  methods: ["GET", "POST", "PUT", "DELETE"],
  credentials: true,
}));
```

### Rate Limiting

Protect APIs from abuse.

```javascript
import rateLimit from "express-rate-limit";

app.use(rateLimit({
  windowMs: 15 * 60 * 1000,  // 15 minutes
  max: 100,                   // per IP
  standardHeaders: true,
}));
```

### Input Validation

Validate and sanitize every input. Use zod, joi, or class-validator.

### Dependency Audit

Run `npm audit` / `pip-audit` in CI. Fail the build on high-severity findings.

---

## 8. Performance

### Response Compression

Enable gzip/brotli at the reverse proxy or in the app.

```javascript
import compression from "compression";
app.use(compression());
```

### Caching

- HTTP caching: `Cache-Control` headers for static assets.
- Application cache: Redis for frequently read data.
- CDN: Put static assets behind Cloudflare / CloudFront.

### Connection Reuse

Enable HTTP keep-alive. Reuse database and Redis connections via pooling.
Avoid creating new connections per request.

---

## 9. CI/CD Pipeline

A minimal production pipeline:

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run lint
      - run: npm test

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: registry.example.com/app:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        run: |
          ssh deploy@server "
            docker pull registry.example.com/app:${{ github.sha }} &&
            docker compose -f docker-compose.prod.yml up -d
          "
```

---

## 10. Rollback Plan

### Blue-Green Deployment

Run the new version alongside the old one. Switch traffic only after health
checks pass. If the new version fails, switch back instantly.

### Canary Releases

Route a small percentage of traffic (5-10%) to the new version. Monitor error
rates. Gradually increase traffic if metrics are healthy.

### Database Rollback

- Use reversible migrations (up + down).
- Test the down migration in staging before deploying.
- Keep the old application version compatible with the new schema for at least
  one release cycle (expand-and-contract pattern).

---

## Pre-Deployment Checklist

Copy this checklist and verify every item before deploying.

### Docker
- [ ] Production compose file uses resource limits
- [ ] Multi-stage Dockerfile produces a minimal image
- [ ] Container runs as non-root user
- [ ] Health check is defined and tested
- [ ] Logging driver is configured with rotation

### Process Management
- [ ] Restart policy is set (unless-stopped or on-failure)
- [ ] Graceful shutdown handles SIGTERM correctly
- [ ] Stop grace period is configured (30s recommended)

### Environment and Secrets
- [ ] NODE_ENV=production (or equivalent) is set
- [ ] No secrets in source control or Docker image
- [ ] `.env` file permissions are restricted (chmod 600)
- [ ] Secrets rotation plan is documented

### Logging
- [ ] Structured JSON logging is enabled
- [ ] Log level is set to info (not debug)
- [ ] Sensitive fields are redacted
- [ ] Log rotation or max-size is configured

### Monitoring
- [ ] /health endpoint returns 200 when service is alive
- [ ] /ready endpoint checks downstream dependencies
- [ ] Prometheus metrics are exposed
- [ ] External uptime monitor is configured
- [ ] Alerts are set for error rate and latency spikes

### Database
- [ ] Migrations run before application starts
- [ ] Automated daily backups are scheduled
- [ ] Backup restore has been tested
- [ ] Connection pool size is configured
- [ ] Slow query logging is enabled

### Security
- [ ] HTTPS is enforced; HTTP redirects to HTTPS
- [ ] CORS allows only known origins
- [ ] Rate limiting is enabled on public endpoints
- [ ] Input validation is applied to all user input
- [ ] `npm audit` / `pip-audit` passes with no high-severity issues
- [ ] Security headers are set (HSTS, X-Content-Type-Options, etc.)

### Performance
- [ ] Response compression is enabled
- [ ] Static assets have Cache-Control headers
- [ ] Database queries are indexed for common access patterns
- [ ] Connection pooling is configured for DB and Redis

### CI/CD
- [ ] Automated tests pass on every push
- [ ] Linting runs in CI
- [ ] Docker image is built and pushed by CI
- [ ] Deployment is automated (no manual SSH)
- [ ] Pipeline has a manual approval gate for production

### Rollback
- [ ] Previous version image is available in the registry
- [ ] Rollback procedure is documented and tested
- [ ] Database migrations are reversible
- [ ] Team knows how to trigger a rollback in under 5 minutes
