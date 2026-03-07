---
name: graceful-shutdown-nodejs
description: Graceful shutdown patterns for Node.js services including HTTP, WebSocket, BullMQ, Prisma, Redis, and grammY bot
---

# Graceful Shutdown Patterns for Node.js

## Overview

Graceful shutdown ensures a service stops cleanly: no dropped requests, no corrupted state, no orphaned connections.
The shutdown sequence is always: **stop accepting new work, drain in-flight work, close resources, exit**.

## Signal Handling (SIGTERM, SIGINT)

```typescript
// shutdown/signals.ts
type ShutdownHook = () => Promise<void>

const hooks: ShutdownHook[] = []
let isShuttingDown = false

export function onShutdown(hook: ShutdownHook): void {
  hooks.push(hook)
}

export function setupSignalHandlers(options: { timeout?: number } = {}): void {
  const timeout = options.timeout ?? 30_000

  async function shutdown(signal: string) {
    if (isShuttingDown) return
    isShuttingDown = true
    console.log(`\n[shutdown] Received ${signal}, starting graceful shutdown...`)

    // Force exit after timeout
    const forceTimer = setTimeout(() => {
      console.error('[shutdown] Timeout exceeded, forcing exit')
      process.exit(1)
    }, timeout)
    forceTimer.unref()

    // Run all hooks in reverse registration order (LIFO)
    for (let i = hooks.length - 1; i >= 0; i--) {
      try {
        await hooks[i]()
      } catch (err) {
        console.error(`[shutdown] Hook ${i} failed:`, err)
      }
    }

    console.log('[shutdown] Clean exit')
    process.exit(0)
  }

  process.on('SIGTERM', () => shutdown('SIGTERM'))
  process.on('SIGINT', () => shutdown('SIGINT'))

  // Handle uncaught errors during shutdown
  process.on('uncaughtException', (err) => {
    console.error('[shutdown] Uncaught exception:', err)
    if (!isShuttingDown) shutdown('uncaughtException')
  })

  process.on('unhandledRejection', (reason) => {
    console.error('[shutdown] Unhandled rejection:', reason)
    if (!isShuttingDown) shutdown('unhandledRejection')
  })
}

export function isTerminating(): boolean {
  return isShuttingDown
}
```

## Shutdown Sequence Ordering

The correct order for shutdown hooks matters. Register them in the order they should run on shutdown (LIFO means the last registered hook runs first).

```typescript
// index.ts
import { setupSignalHandlers, onShutdown } from './shutdown/signals'

async function main() {
  setupSignalHandlers({ timeout: 30_000 })

  // 1. First registered = last to close (database is the last thing to shut down)
  const prisma = new PrismaClient()
  await prisma.$connect()
  onShutdown(async () => {
    console.log('[shutdown] Disconnecting Prisma...')
    await prisma.$disconnect()
  })

  // 2. Redis
  const redis = createRedisClient()
  onShutdown(async () => {
    console.log('[shutdown] Closing Redis...')
    await redis.quit()
  })

  // 3. BullMQ workers
  const worker = createWorker(redis)
  onShutdown(async () => {
    console.log('[shutdown] Closing BullMQ worker...')
    await worker.close()
  })

  // 4. WebSocket server
  const wss = createWebSocketServer()
  onShutdown(async () => {
    console.log('[shutdown] Closing WebSocket server...')
    await closeWebSocketServer(wss)
  })

  // 5. HTTP server (last registered = first to close = stop accepting requests first)
  const server = createHttpServer()
  onShutdown(async () => {
    console.log('[shutdown] Closing HTTP server...')
    await closeHttpServer(server)
  })

  server.listen(3000, () => {
    console.log('Server listening on :3000')
  })
}

main()
```

## HTTP Server Shutdown with Keep-Alive Handling

```typescript
// shutdown/http.ts
import http from 'node:http'

const connections = new Set<import('node:net').Socket>()

export function trackConnections(server: http.Server): void {
  server.on('connection', (socket) => {
    connections.add(socket)
    socket.on('close', () => connections.delete(socket))
  })
}

export function closeHttpServer(
  server: http.Server,
  options: { drainTimeout?: number } = {}
): Promise<void> {
  const drainTimeout = options.drainTimeout ?? 10_000

  return new Promise((resolve, reject) => {
    // Stop accepting new connections
    server.close((err) => {
      if (err) reject(err)
      else resolve()
    })

    // Set a short keep-alive timeout to allow in-flight requests to finish
    // but prevent new requests on existing connections
    for (const socket of connections) {
      // End idle connections immediately
      if (!(socket as any)._httpMessage) {
        socket.destroy()
      } else {
        // Active connections: set a short timeout
        socket.setTimeout(drainTimeout)
      }
    }

    // Force-close remaining connections after drain timeout
    setTimeout(() => {
      for (const socket of connections) {
        socket.destroy()
      }
    }, drainTimeout)
  })
}
```

### Express/Fastify Integration

```typescript
// With Express
import express from 'express'
import { trackConnections, closeHttpServer } from './shutdown/http'

const app = express()

// Middleware to reject requests during shutdown
app.use((req, res, next) => {
  if (isTerminating()) {
    res.status(503).set('Connection', 'close').json({ error: 'Server shutting down' })
    return
  }
  next()
})

const server = app.listen(3000)
trackConnections(server)

onShutdown(() => closeHttpServer(server))
```

```typescript
// With Fastify
import Fastify from 'fastify'

const fastify = Fastify({ logger: true })

// Fastify has built-in graceful shutdown
onShutdown(async () => {
  await fastify.close()
})
```

## WebSocket Graceful Disconnect

```typescript
// shutdown/websocket.ts
import { WebSocketServer, WebSocket } from 'ws'

export function closeWebSocketServer(wss: WebSocketServer): Promise<void> {
  return new Promise((resolve) => {
    // Notify all clients that server is shutting down
    for (const client of wss.clients) {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify({
          type: 'server_shutdown',
          message: 'Server is restarting, please reconnect shortly.',
          reconnectAfter: 5000,
        }))
        // Close with code 1001 (Going Away)
        client.close(1001, 'Server shutting down')
      }
    }

    // Wait for clients to disconnect, with timeout
    const checkInterval = setInterval(() => {
      if (wss.clients.size === 0) {
        clearInterval(checkInterval)
        wss.close(() => resolve())
      }
    }, 100)

    // Force close after 5 seconds
    setTimeout(() => {
      clearInterval(checkInterval)
      for (const client of wss.clients) {
        client.terminate()
      }
      wss.close(() => resolve())
    }, 5000)
  })
}
```

## BullMQ Worker Shutdown

```typescript
// workers/gameWorker.ts
import { Worker, Queue } from 'bullmq'
import type { RedisOptions } from 'ioredis'

const redisOpts: RedisOptions = {
  host: process.env.REDIS_HOST ?? 'localhost',
  port: parseInt(process.env.REDIS_PORT ?? '6379'),
  maxRetriesPerRequest: null, // Required by BullMQ
}

const worker = new Worker(
  'game-tasks',
  async (job) => {
    switch (job.name) {
      case 'processMove':
        await processGameMove(job.data)
        break
      case 'endRound':
        await endGameRound(job.data)
        break
    }
  },
  {
    connection: redisOpts,
    concurrency: 5,
    // Lock duration should be less than shutdown timeout
    lockDuration: 30_000,
  }
)

worker.on('completed', (job) => {
  console.log(`Job ${job.id} completed`)
})

worker.on('failed', (job, err) => {
  console.error(`Job ${job?.id} failed:`, err.message)
})

// Graceful shutdown for BullMQ worker:
// 1. Stops picking up new jobs
// 2. Waits for current jobs to complete (up to lock duration)
// 3. Closes Redis connection
onShutdown(async () => {
  console.log('[shutdown] Draining BullMQ worker...')
  await worker.close()
  console.log('[shutdown] BullMQ worker closed')
})
```

### Queue Scheduler and Flow Producer

```typescript
// If using QueueScheduler (BullMQ < 4) or FlowProducer
const queue = new Queue('game-tasks', { connection: redisOpts })

onShutdown(async () => {
  await queue.close()
})
```

## Prisma / Database Disconnect

```typescript
// db/prisma.ts
import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient({
  log: process.env.NODE_ENV === 'development' ? ['query', 'warn', 'error'] : ['warn', 'error'],
})

export { prisma }

// Register shutdown hook
onShutdown(async () => {
  console.log('[shutdown] Disconnecting Prisma...')
  await prisma.$disconnect()
  console.log('[shutdown] Prisma disconnected')
})
```

### Handling In-Flight Transactions

```typescript
// Use an AbortController pattern for long-running transactions
import { isTerminating } from './shutdown/signals'

export async function longRunningTask() {
  const batchSize = 100
  let processed = 0

  while (processed < totalCount) {
    if (isTerminating()) {
      console.log(`[task] Shutdown requested, stopping at ${processed}/${totalCount}`)
      break
    }

    await prisma.$transaction(async (tx) => {
      const batch = await tx.item.findMany({ skip: processed, take: batchSize })
      for (const item of batch) {
        await tx.item.update({ where: { id: item.id }, data: { processed: true } })
      }
    })

    processed += batchSize
  }
}
```

## Redis Connection Cleanup

```typescript
// db/redis.ts
import Redis from 'ioredis'

export function createRedisClient(): Redis {
  const redis = new Redis({
    host: process.env.REDIS_HOST ?? 'localhost',
    port: parseInt(process.env.REDIS_PORT ?? '6379'),
    // Do not reconnect during shutdown
    retryStrategy(times) {
      if (isTerminating()) return null
      return Math.min(times * 200, 5000)
    },
    enableReadyCheck: true,
    maxRetriesPerRequest: 3,
  })

  redis.on('error', (err) => {
    console.error('[redis] Error:', err.message)
  })

  return redis
}

// Shutdown hook
onShutdown(async () => {
  console.log('[shutdown] Closing Redis...')
  // quit() sends the QUIT command and waits for reply
  // disconnect() forces close immediately
  // Always prefer quit() for graceful shutdown
  await redis.quit()
  console.log('[shutdown] Redis closed')
})
```

### Pub/Sub Cleanup

```typescript
const subscriber = redis.duplicate()
await subscriber.subscribe('game:events')

subscriber.on('message', (channel, message) => {
  handleGameEvent(JSON.parse(message))
})

onShutdown(async () => {
  await subscriber.unsubscribe()
  await subscriber.quit()
})
```

## grammY Bot Stop (Polling + Webhook Modes)

### Polling Mode

```typescript
// bot/index.ts
import { Bot } from 'grammy'

const bot = new Bot(process.env.BOT_TOKEN!)

bot.command('start', (ctx) => ctx.reply('Hello!'))

// Start polling
bot.start({
  onStart: () => console.log('Bot started (polling)'),
})

// Graceful stop for polling:
// 1. Stops fetching new updates
// 2. Finishes processing current update batch
// 3. Closes the bot instance
onShutdown(async () => {
  console.log('[shutdown] Stopping bot (polling)...')
  await bot.stop()
  console.log('[shutdown] Bot stopped')
})
```

### Webhook Mode (with Express)

```typescript
import express from 'express'
import { Bot, webhookCallback } from 'grammy'

const bot = new Bot(process.env.BOT_TOKEN!)
const app = express()

app.use(express.json())
app.post('/webhook', webhookCallback(bot, 'express'))

const server = app.listen(3000)
trackConnections(server)

// In webhook mode, bot.stop() is not needed since updates come via HTTP.
// Just stop the HTTP server.
onShutdown(async () => {
  // First delete the webhook so Telegram stops sending updates
  await bot.api.deleteWebhook()
  console.log('[shutdown] Webhook deleted')

  // Then close the HTTP server (drain in-flight webhook requests)
  await closeHttpServer(server)
})
```

### grammY Runner (Long Polling with Concurrency)

```typescript
import { Bot } from 'grammy'
import { run } from '@grammyjs/runner'

const bot = new Bot(process.env.BOT_TOKEN!)
const runner = run(bot)

onShutdown(async () => {
  console.log('[shutdown] Stopping grammY runner...')
  // runner.stop() is the equivalent of bot.stop() for the runner
  if (runner.isRunning()) {
    await runner.stop()
  }
  console.log('[shutdown] grammY runner stopped')
})
```

## Docker Stop Signal and Timeout Configuration

```dockerfile
# Dockerfile
FROM node:20-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY dist/ ./dist/

# Node.js handles SIGTERM by default
# Make sure your app listens for SIGTERM (not just SIGINT)
STOPSIGNAL SIGTERM

# Run as non-root
USER node

CMD ["node", "dist/index.js"]
```

```yaml
# docker-compose.yml
services:
  app:
    build: .
    stop_signal: SIGTERM
    # Time Docker waits before SIGKILL after sending stop_signal
    # Must be GREATER than your app's shutdown timeout
    stop_grace_period: 45s
    deploy:
      restart_policy:
        condition: on-failure
        max_attempts: 3
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3000/health"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s
```

### Important: Node.js in Docker

```dockerfile
# BAD: npm start wraps node in a shell process that does not forward signals
CMD ["npm", "start"]

# GOOD: run node directly so it receives SIGTERM
CMD ["node", "dist/index.js"]

# ALSO GOOD: use tini as init process to forward signals
RUN apk add --no-cache tini
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["node", "dist/index.js"]
```

## Health Check Endpoints During Shutdown

```typescript
// health/index.ts
import { Router } from 'express'
import { isTerminating } from '../shutdown/signals'

const healthRouter = Router()

// Liveness probe: is the process alive?
healthRouter.get('/health/live', (_req, res) => {
  res.status(200).json({ status: 'ok' })
})

// Readiness probe: is the service ready to accept traffic?
healthRouter.get('/health/ready', (_req, res) => {
  if (isTerminating()) {
    // Return 503 so load balancers stop sending traffic
    res.status(503).json({ status: 'shutting_down' })
    return
  }

  // Check dependencies
  const checks = {
    database: checkDatabase(),
    redis: checkRedis(),
    queue: checkQueue(),
  }

  const allHealthy = Object.values(checks).every((c) => c.healthy)

  res.status(allHealthy ? 200 : 503).json({
    status: allHealthy ? 'ok' : 'degraded',
    checks,
  })
})

export { healthRouter }
```

### Kubernetes Integration

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 45
      containers:
        - name: app
          livenessProbe:
            httpGet:
              path: /health/live
              port: 3000
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 3000
            initialDelaySeconds: 5
            periodSeconds: 5
          lifecycle:
            preStop:
              exec:
                # Give the load balancer time to remove this pod
                command: ["sleep", "5"]
```

## Common Mistakes

### 1. Exceeding Kill Timeout

```typescript
// BAD: Shutdown takes longer than Docker's stop_grace_period
onShutdown(async () => {
  await processAllRemainingItems() // Could take minutes
  await prisma.$disconnect()
})

// GOOD: Respect the timeout, stop early if needed
onShutdown(async () => {
  await processRemainingItems({ maxDuration: 20_000 })
  await prisma.$disconnect()
})
```

### 2. Resource Leaks from Missing Cleanup

```typescript
// BAD: setInterval prevents clean exit
setInterval(() => syncStats(), 60_000)

// GOOD: track and clear intervals
const statsInterval = setInterval(() => syncStats(), 60_000)
onShutdown(async () => {
  clearInterval(statsInterval)
})
```

### 3. Not Handling Duplicate Signals

```typescript
// BAD: shutdown runs twice on rapid Ctrl+C
process.on('SIGINT', async () => {
  await cleanup() // Runs twice, may cause errors
  process.exit(0)
})

// GOOD: guard against re-entry (already shown in the signals module above)
let isShuttingDown = false
async function shutdown() {
  if (isShuttingDown) return
  isShuttingDown = true
  // ...
}
```

### 4. Using process.exit() Without Cleanup

```typescript
// BAD: skips all cleanup
if (criticalError) process.exit(1)

// GOOD: trigger graceful shutdown
if (criticalError) {
  console.error('Critical error, shutting down')
  process.kill(process.pid, 'SIGTERM')
}
```

### 5. Not Draining the Event Loop

```typescript
// BAD: process exits while async operations are in flight
server.close(() => {
  process.exit(0) // Pending database writes may be lost
})

// GOOD: wait for all shutdown hooks to complete before exiting
// (handled by the shutdown module pattern shown above)
```

### 6. Ignoring npm start Signal Forwarding in Docker

When using `npm start` in Docker, the npm process wraps Node.js in a shell.
SIGTERM goes to npm, not your Node.js process. Always use `node` directly or `tini`.

## Complete Example: Full Service Shutdown

```typescript
// index.ts - putting it all together
import { setupSignalHandlers, onShutdown } from './shutdown/signals'
import { createApp } from './app'
import { prisma } from './db/prisma'
import { createRedisClient } from './db/redis'
import { createWorker } from './workers'
import { Bot } from 'grammy'

async function main() {
  setupSignalHandlers({ timeout: 30_000 })

  // Layer 1: Database (closes last)
  await prisma.$connect()
  onShutdown(async () => {
    await prisma.$disconnect()
  })

  // Layer 2: Redis
  const redis = createRedisClient()
  onShutdown(async () => {
    await redis.quit()
  })

  // Layer 3: Background workers
  const worker = createWorker(redis)
  onShutdown(async () => {
    await worker.close()
  })

  // Layer 4: Telegram bot
  const bot = new Bot(process.env.BOT_TOKEN!)
  bot.start()
  onShutdown(async () => {
    await bot.stop()
  })

  // Layer 5: HTTP server (closes first)
  const { server } = createApp(prisma, redis)
  onShutdown(async () => {
    await closeHttpServer(server)
  })

  console.log('All services started')
}

main().catch((err) => {
  console.error('Failed to start:', err)
  process.exit(1)
})
```
