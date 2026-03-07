---
name: telegram-bot-deployment
description: Best practices for deploying Telegram bots with Docker, webhooks, process management, monitoring, and scaling strategies
---

# Telegram Bot Deployment

This skill covers everything needed to deploy, monitor, and scale a Telegram
bot in production. It applies to both Node.js (grammY, Telegraf) and Python
(aiogram, python-telegram-bot) bots.

---

## 1. Polling vs Webhook Mode

### Long Polling

The bot continuously asks the Telegram API for new updates.

**Pros:**
- No public URL or SSL certificate required
- Works behind NAT, firewalls, and on local machines
- Simpler initial setup

**Cons:**
- Higher latency (depends on poll interval)
- Wastes bandwidth when idle
- Only one process can poll at a time (no horizontal scaling)

**When to use:** Development, small bots, VPS without a domain, bots behind
restrictive firewalls.

```javascript
// grammY - polling
bot.start();
```

```python
# aiogram - polling
dp.run_polling(bot)
```

### Webhook

Telegram pushes updates to your HTTPS endpoint.

**Pros:**
- Near-instant delivery of updates
- No wasted bandwidth
- Multiple workers can handle incoming requests (scalable)

**Cons:**
- Requires a public HTTPS URL with a valid certificate
- Slightly more complex setup (reverse proxy, SSL)

**When to use:** Production deployments, bots handling high traffic, bots
deployed alongside a web application.

```javascript
// grammY - webhook with express
import express from "express";
import { webhookCallback } from "grammy";

const app = express();
app.use(express.json());
app.use("/bot-webhook", webhookCallback(bot, "express"));
app.listen(3000);
```

```python
# aiogram - webhook with aiohttp
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
app = web.Application()
handler.register(app, path="/bot-webhook")
web.run_app(app, host="0.0.0.0", port=3000)
```

Set the webhook URL via the API:

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://bot.example.com/bot-webhook" \
  -d "secret_token=<RANDOM_SECRET>"
```

Always use `secret_token` to verify that requests actually come from Telegram.

---

## 2. Docker Compose Setup

### Single Bot

```yaml
# docker-compose.yml
version: "3.8"

services:
  bot:
    build:
      context: .
      dockerfile: Dockerfile
    env_file: .env
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "node", "healthcheck.js"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: json-file
      options:
        max-size: "30m"
        max-file: "3"

  db:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: botuser
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
      POSTGRES_DB: botdb
    secrets:
      - db_password
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U botuser -d botdb"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  pgdata:
  redisdata:

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

### Multi-Bot

Run several bots in one compose project. Share the database and Redis.

```yaml
services:
  bot-main:
    build:
      context: ./bots/main
    env_file: ./bots/main/.env
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy

  bot-admin:
    build:
      context: ./bots/admin
    env_file: ./bots/admin/.env
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: botuser
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: bots

  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data

volumes:
  pgdata:
  redisdata:
```

---

## 3. Webhook Setup with Nginx Reverse Proxy + SSL

```nginx
# /etc/nginx/sites-available/bot.example.com
server {
    listen 80;
    server_name bot.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name bot.example.com;

    ssl_certificate     /etc/letsencrypt/live/bot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # Webhook endpoint
    location /bot-webhook {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Telegram sends JSON, increase buffer for large updates
        proxy_buffer_size 16k;
        proxy_buffers 4 16k;
    }

    # Block everything else
    location / {
        return 404;
    }
}
```

Obtain a certificate with Certbot:

```bash
sudo certbot --nginx -d bot.example.com
```

Telegram requires one of these ports for webhooks: 443, 80, 88, or 8443.

---

## 4. PM2 Process Management

Use PM2 when deploying directly on a VPS without Docker.

```javascript
// ecosystem.config.js
module.exports = {
  apps: [
    {
      name: "telegram-bot",
      script: "dist/index.js",
      instances: 1,                // bots using polling MUST use 1 instance
      autorestart: true,
      max_memory_restart: "300M",
      watch: false,
      env_production: {
        NODE_ENV: "production",
        BOT_MODE: "polling",       // or "webhook"
      },
      error_file: "/var/log/telegram-bot/error.log",
      out_file: "/var/log/telegram-bot/out.log",
      merge_logs: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      kill_timeout: 10000,         // 10s graceful shutdown
      listen_timeout: 5000,
    },
  ],
};
```

Commands:

```bash
pm2 start ecosystem.config.js --env production
pm2 save
pm2 startup     # auto-start on reboot
pm2 logs telegram-bot --lines 50
pm2 monit       # live dashboard
```

If using webhook mode with multiple workers, set `instances` to the desired
count and use `exec_mode: "cluster"`.

---

## 5. Environment Variables and Secrets

### .env File

```bash
# .env (never commit this file)
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
BOT_MODE=polling
DATABASE_URL=postgresql://botuser:secret@localhost:5432/botdb
REDIS_URL=redis://localhost:6379
LOG_LEVEL=info
WEBHOOK_DOMAIN=https://bot.example.com
WEBHOOK_PATH=/bot-webhook
WEBHOOK_SECRET=random-secret-string-here
ADMIN_CHAT_ID=123456789
```

### Docker Secrets

For Swarm or Compose, use secrets instead of environment variables for
sensitive values.

```yaml
secrets:
  bot_token:
    file: ./secrets/bot_token.txt

services:
  bot:
    secrets:
      - bot_token
    environment:
      BOT_TOKEN_FILE: /run/secrets/bot_token
```

Read the secret in code:

```javascript
import { readFileSync } from "fs";

const token = process.env.BOT_TOKEN_FILE
  ? readFileSync(process.env.BOT_TOKEN_FILE, "utf-8").trim()
  : process.env.BOT_TOKEN;
```

---

## 6. Health Checks and Auto-Restart

### Simple Health Check Script (polling mode)

```javascript
// healthcheck.js
import net from "net";

const client = new net.Socket();
client.connect(3000, "127.0.0.1", () => {
  client.end();
  process.exit(0);
});
client.on("error", () => process.exit(1));
```

### Application-Level Health Endpoint

Even polling bots should expose an HTTP health endpoint for monitoring.

```javascript
import express from "express";

const health = express();
health.get("/health", (req, res) => {
  res.json({
    status: "ok",
    uptime: process.uptime(),
    botInfo: bot.botInfo?.username ?? "unknown",
    mode: process.env.BOT_MODE,
  });
});
health.listen(3001);
```

Docker compose health check:

```yaml
healthcheck:
  test: ["CMD", "wget", "--spider", "-q", "http://localhost:3001/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 15s
```

---

## 7. Logging Configuration

### Node.js -- pino

```javascript
import pino from "pino";

export const logger = pino({
  level: process.env.LOG_LEVEL || "info",
  transport:
    process.env.NODE_ENV !== "production"
      ? { target: "pino-pretty" }
      : undefined,
  redact: ["botToken", "*.botToken"],
});

// Log every update
bot.use(async (ctx, next) => {
  const start = Date.now();
  await next();
  const ms = Date.now() - start;
  logger.info({
    updateId: ctx.update.update_id,
    type: ctx.updateType,
    from: ctx.from?.id,
    chat: ctx.chat?.id,
    ms,
  });
});
```

### Python -- loguru

```python
from loguru import logger
import sys

logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}",
    level="INFO",
    serialize=True,
)
logger.add(
    "/var/log/bot/bot.log",
    rotation="50 MB",
    retention="30 days",
    compression="gz",
    level="DEBUG",
)
```

---

## 8. Database Deployment

### PostgreSQL

```yaml
services:
  db:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      POSTGRES_USER: botuser
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: botdb
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U botuser -d botdb"]
      interval: 10s
      timeout: 5s
      retries: 5
    shm_size: 128mb
```

Run migrations before starting the bot:

```yaml
services:
  migrate:
    image: bot:latest
    command: ["npx", "prisma", "migrate", "deploy"]
    depends_on:
      db:
        condition: service_healthy
  bot:
    depends_on:
      migrate:
        condition: service_completed_successfully
```

### SQLite

For lightweight bots, SQLite is sufficient. Mount the database file as a volume.

```yaml
services:
  bot:
    volumes:
      - ./data:/app/data
    environment:
      DATABASE_URL: file:/app/data/bot.db
```

Ensure the directory exists and has correct permissions before starting.

---

## 9. Redis for Sessions and Queues

```yaml
services:
  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --maxmemory 128mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
```

Use Redis for:

- **Session storage:** Store conversation state per user/chat.
- **Rate limit counters:** Track API usage per user.
- **Job queues:** Offload heavy work (image processing, external API calls) to
  background workers using BullMQ (Node.js) or Celery (Python).

```javascript
// grammY session with Redis
import { RedisAdapter } from "@grammyjs/storage-redis";
import { createClient } from "redis";

const redis = createClient({ url: process.env.REDIS_URL });
await redis.connect();

bot.use(session({
  initial: () => ({ step: "idle" }),
  storage: new RedisAdapter({ instance: redis }),
}));
```

---

## 10. CI/CD with GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy Bot

on:
  push:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
      - run: npm run lint
      - run: npm test

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/telegram-bot
            docker compose pull
            docker compose up -d --remove-orphans
            docker image prune -f
```

---

## 11. Monitoring

### Bot Uptime

Use an external service (UptimeRobot, Healthchecks.io) to ping the health
endpoint every 60 seconds. Alert on two consecutive failures.

### Message Throughput

Track updates per minute with a Prometheus counter.

```javascript
import client from "prom-client";

const updatesTotal = new client.Counter({
  name: "bot_updates_total",
  help: "Total number of Telegram updates processed",
  labelNames: ["type"],
});

bot.use(async (ctx, next) => {
  updatesTotal.inc({ type: ctx.updateType });
  await next();
});
```

### Error Rates

Track handler errors and alert if the error rate exceeds a threshold.

```javascript
const errorsTotal = new client.Counter({
  name: "bot_errors_total",
  help: "Total number of handler errors",
  labelNames: ["handler"],
});

bot.catch((err) => {
  errorsTotal.inc({ handler: err.ctx?.updateType ?? "unknown" });
  logger.error({ err: err.error, update: err.ctx?.update }, "Bot error");
});
```

### Grafana Dashboard

Create a dashboard showing:
- Updates per minute (by type)
- Error rate percentage
- Response latency (p50, p95, p99)
- Active users (unique from IDs per hour)
- Memory and CPU usage of the bot container

---

## 12. Backup Strategies

### Database Dumps

```bash
#!/bin/bash
# /scripts/backup.sh
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/bot"
mkdir -p "$BACKUP_DIR"

# PostgreSQL dump
docker exec bot-db pg_dump -U botuser botdb | gzip > "${BACKUP_DIR}/db_${TIMESTAMP}.gz"

# Keep last 30 days
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete
```

Schedule with cron: `0 3 * * * /scripts/backup.sh`

### Session Data

If sessions are in Redis, schedule periodic RDB snapshots.

```yaml
services:
  redis:
    command: redis-server --save 900 1 --save 300 10 --appendonly yes
    volumes:
      - redisdata:/data
```

Copy `/data/dump.rdb` to a backup location daily.

### SQLite Backup

```bash
sqlite3 /app/data/bot.db ".backup /backups/bot_${TIMESTAMP}.db"
```

---

## 13. Scaling

### Multiple Workers (Webhook Mode)

In webhook mode, run multiple worker processes behind a load balancer. Each
worker handles incoming webhook requests independently.

```yaml
services:
  bot:
    build: .
    deploy:
      replicas: 3
    environment:
      BOT_MODE: webhook

  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - bot
```

Nginx upstream configuration:

```nginx
upstream bot_workers {
    least_conn;
    server bot:3000;
}

server {
    listen 443 ssl;
    location /bot-webhook {
        proxy_pass http://bot_workers;
    }
}
```

### Worker Processes for Heavy Tasks

Offload CPU-intensive or slow tasks to a background queue.

```
[Telegram] --> [Webhook Handler] --> [Redis Queue] --> [Worker]
                    |                                      |
                    v                                      v
              (fast reply)                          (process image,
                                                     call external API)
```

### Polling Mode Limitation

Polling mode does NOT support multiple instances. Only one process can call
`getUpdates` at a time. If you need to scale, switch to webhook mode.

---

## 14. Common Issues and Solutions

### API Rate Limits

Telegram enforces limits on bot API calls:
- **Messages to a single chat:** ~1 per second
- **Messages to different chats:** ~30 per second
- **Bulk notifications:** ~25-30 messages per second globally

Solution: Use a message queue with rate limiting.

```javascript
import Bottleneck from "bottleneck";

const limiter = new Bottleneck({
  maxConcurrent: 1,
  minTime: 35,  // ~28 messages per second
});

async function sendMessage(chatId, text) {
  return limiter.schedule(() => bot.api.sendMessage(chatId, text));
}
```

### Flood Wait (429 Error)

When you hit the rate limit, Telegram returns a 429 error with a
`retry_after` field.

```javascript
bot.api.config.use(async (prev, method, payload, signal) => {
  try {
    return await prev(method, payload, signal);
  } catch (err) {
    if (err.error_code === 429) {
      const wait = err.parameters?.retry_after ?? 5;
      logger.warn(`Flood wait: sleeping ${wait}s`);
      await new Promise((r) => setTimeout(r, wait * 1000));
      return prev(method, payload, signal);
    }
    throw err;
  }
});
```

### Session Conflicts

If two processes try to poll simultaneously, Telegram will return conflict
errors and one process will stop receiving updates.

**Fix:** Ensure only one polling instance runs at a time. Use a lock in Redis
or a single-instance deployment.

```javascript
// Redis lock to prevent duplicate polling
const lockKey = "bot:polling:lock";
const acquired = await redis.set(lockKey, process.pid, { NX: true, EX: 60 });
if (!acquired) {
  logger.fatal("Another instance is already polling. Exiting.");
  process.exit(1);
}
// Refresh lock every 30s
setInterval(() => redis.expire(lockKey, 60), 30000);
```

### Webhook Not Receiving Updates

Troubleshooting steps:

1. **Verify webhook is set:**
   `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

2. **Check for pending errors:** The `last_error_message` field in the
   response above shows the most recent delivery failure.

3. **Verify SSL:** Telegram only sends webhooks to valid HTTPS endpoints.
   Self-signed certificates need to be uploaded via `setWebhook`.

4. **Check firewall:** Ensure port 443 (or 8443) is open for incoming
   connections from Telegram IPs (149.154.160.0/20, 91.108.4.0/22).

5. **Verify the bot responds with 200:** Telegram retries on non-2xx responses
   and will eventually disable the webhook after too many failures.

### Memory Leaks

Long-running bots can accumulate memory over time.

- Set `max_memory_restart` in PM2 or memory limits in Docker.
- Profile with `--inspect` and Chrome DevTools.
- Check for event listener leaks and unbounded caches.

```yaml
# Docker memory limit
services:
  bot:
    deploy:
      resources:
        limits:
          memory: 512M
```

---

## Quick Start Template

For a new bot deployment, copy this minimal setup and expand as needed.

```bash
# Project structure
my-bot/
  src/
    index.ts
  Dockerfile
  docker-compose.yml
  .env
  .env.example
  .dockerignore
  healthcheck.js
  ecosystem.config.js
```

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
RUN addgroup -S bot && adduser -S bot -G bot
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
COPY healthcheck.js ./
USER bot
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

Start the bot: `docker compose up -d`
View logs: `docker compose logs -f bot`
Restart: `docker compose restart bot`
Update: `docker compose pull && docker compose up -d`
