---
name: multi-bot-telegram-architecture
description: Patterns for building multi-bot Telegram platforms with shared infrastructure, message passing, and coordinated deployment
---

# Multi-Bot Telegram Architecture

## Overview

When building a platform with multiple Telegram bots (e.g., a food delivery system with CLIENT, COURIER, RESTAURANT, and ADMIN bots), each bot runs as a separate process but shares infrastructure. This skill covers the architecture patterns that keep bots decoupled yet coordinated.

## Monorepo Structure (pnpm Workspaces)

Organize the project as a monorepo with shared packages:

```
project-root/
  pnpm-workspace.yaml
  package.json
  packages/
    shared-db/           # Prisma schema + client
      prisma/
        schema.prisma
        migrations/
      src/
        index.ts
      package.json
    shared-types/        # TypeScript interfaces, enums
      src/
        roles.ts
        events.ts
        index.ts
      package.json
    queue/               # BullMQ queue definitions
      src/
        queues.ts
        workers.ts
        index.ts
      package.json
  bots/
    client-bot/
      src/
        handlers/
        middlewares/
        scenes/
        index.ts
      package.json
    courier-bot/
      src/
        handlers/
        middlewares/
        index.ts
      package.json
    restaurant-bot/
      src/
        handlers/
        middlewares/
        index.ts
      package.json
    admin-bot/
      src/
        handlers/
        middlewares/
        index.ts
      package.json
  docker-compose.yml
```

pnpm-workspace.yaml:

```yaml
packages:
  - "packages/*"
  - "bots/*"
```

Root package.json scripts:

```json
{
  "scripts": {
    "dev:client": "pnpm --filter client-bot dev",
    "dev:courier": "pnpm --filter courier-bot dev",
    "dev:all": "pnpm -r --parallel dev",
    "db:migrate": "pnpm --filter shared-db prisma migrate deploy",
    "db:generate": "pnpm --filter shared-db prisma generate",
    "build": "pnpm -r build",
    "test": "pnpm -r test",
    "test:e2e": "pnpm --filter e2e-tests test"
  }
}
```

## Shared Database (Prisma)

All bots share a single Prisma schema. The `shared-db` package exports the client:

```prisma
// packages/shared-db/prisma/schema.prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

enum UserRole {
  CLIENT
  COURIER
  ADMIN
  RESTAURANT
}

model User {
  id         Int      @id @default(autoincrement())
  telegramId BigInt   @unique
  role       UserRole
  name       String
  phone      String?
  isActive   Boolean  @default(true)
  createdAt  DateTime @default(now())
  orders     Order[]  @relation("clientOrders")
  deliveries Order[]  @relation("courierOrders")
}

model Order {
  id           Int         @id @default(autoincrement())
  status       OrderStatus @default(PENDING)
  clientId     Int
  client       User        @relation("clientOrders", fields: [clientId], references: [id])
  courierId    Int?
  courier      User?       @relation("courierOrders", fields: [courierId], references: [id])
  restaurantId Int
  items        Json
  total        Decimal     @db.Decimal(10, 2)
  createdAt    DateTime    @default(now())
  updatedAt    DateTime    @updatedAt
}

enum OrderStatus {
  PENDING
  CONFIRMED
  PREPARING
  READY
  PICKED_UP
  DELIVERED
  CANCELLED
}
```

Export the client as a singleton:

```typescript
// packages/shared-db/src/index.ts
import { PrismaClient } from "@prisma/client";

let prisma: PrismaClient | null = null;

export function getDb(): PrismaClient {
  if (!prisma) {
    prisma = new PrismaClient({
      log: process.env.NODE_ENV === "development" ? ["query"] : [],
    });
  }
  return prisma;
}

export async function disconnectDb(): Promise<void> {
  if (prisma) {
    await prisma.$disconnect();
    prisma = null;
  }
}

export * from "@prisma/client";
```

For Python projects, use SQLAlchemy with the same pattern:

```python
# packages/shared_db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

_engine = None
_session_factory = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=5,
            max_overflow=10,
        )
    return _engine

def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory
```

## Message Passing Between Bots (BullMQ / Redis)

Bots communicate via Redis-backed queues. Each bot subscribes to its own queue and publishes to others:

```typescript
// packages/queue/src/queues.ts
import { Queue, Worker, Job } from "bullmq";
import Redis from "ioredis";

const connection = new Redis(process.env.REDIS_URL!, { maxRetriesPerRequest: null });

export const QUEUE_NAMES = {
  CLIENT_NOTIFICATIONS: "client-notifications",
  COURIER_NOTIFICATIONS: "courier-notifications",
  RESTAURANT_NOTIFICATIONS: "restaurant-notifications",
  ADMIN_ALERTS: "admin-alerts",
  ORDER_EVENTS: "order-events",
} as const;

export function createQueue(name: string): Queue {
  return new Queue(name, { connection });
}

export function createWorker(
  name: string,
  processor: (job: Job) => Promise<void>,
  concurrency = 5
): Worker {
  const worker = new Worker(name, processor, {
    connection,
    concurrency,
    limiter: { max: 10, duration: 1000 },
  });

  worker.on("failed", (job, err) => {
    console.error(`Job ${job?.id} in ${name} failed:`, err.message);
  });

  return worker;
}
```

Event definitions:

```typescript
// packages/shared-types/src/events.ts
export interface OrderCreatedEvent {
  type: "ORDER_CREATED";
  orderId: number;
  clientTelegramId: number;
  restaurantId: number;
  items: Array<{ name: string; quantity: number; price: number }>;
}

export interface OrderStatusChangedEvent {
  type: "ORDER_STATUS_CHANGED";
  orderId: number;
  previousStatus: string;
  newStatus: string;
  clientTelegramId: number;
  courierTelegramId?: number;
}

export type BotEvent = OrderCreatedEvent | OrderStatusChangedEvent;
```

Publishing from the restaurant bot when an order is confirmed:

```typescript
// bots/restaurant-bot/src/handlers/confirm-order.ts
import { createQueue, QUEUE_NAMES } from "@project/queue";

const clientQueue = createQueue(QUEUE_NAMES.CLIENT_NOTIFICATIONS);
const courierQueue = createQueue(QUEUE_NAMES.COURIER_NOTIFICATIONS);

export async function handleConfirmOrder(ctx: Context, orderId: number) {
  const db = getDb();
  const order = await db.order.update({
    where: { id: orderId },
    data: { status: "CONFIRMED" },
    include: { client: true },
  });

  await clientQueue.add("order-confirmed", {
    type: "ORDER_STATUS_CHANGED",
    orderId: order.id,
    newStatus: "CONFIRMED",
    clientTelegramId: Number(order.client.telegramId),
  });

  await courierQueue.add("new-order-available", {
    type: "ORDER_CREATED",
    orderId: order.id,
    restaurantId: order.restaurantId,
  });

  await ctx.reply("Order confirmed. Client and couriers have been notified.");
}
```

## Notification Dispatcher Pattern

Each bot has a singleton notification dispatcher that sends Telegram messages from queue jobs:

```typescript
// bots/client-bot/src/notification-dispatcher.ts
import { Telegraf } from "telegraf";
import { createWorker, QUEUE_NAMES } from "@project/queue";
import { Worker } from "bullmq";

export class NotificationDispatcher {
  private worker: Worker | null = null;
  private bot: Telegraf;

  constructor(bot: Telegraf) {
    this.bot = bot;
  }

  start(): void {
    this.worker = createWorker(
      QUEUE_NAMES.CLIENT_NOTIFICATIONS,
      async (job) => {
        const { type } = job.data;

        switch (type) {
          case "ORDER_STATUS_CHANGED":
            await this.handleStatusChange(job.data);
            break;
          default:
            console.warn(`Unknown event type: ${type}`);
        }
      },
      3
    );

    console.log("Client notification dispatcher started");
  }

  private async handleStatusChange(data: {
    clientTelegramId: number;
    orderId: number;
    newStatus: string;
  }): Promise<void> {
    const statusMessages: Record<string, string> = {
      CONFIRMED: "Your order has been confirmed by the restaurant!",
      PREPARING: "Your order is being prepared.",
      READY: "Your order is ready for pickup!",
      PICKED_UP: "A courier has picked up your order.",
      DELIVERED: "Your order has been delivered. Enjoy!",
    };

    const message = statusMessages[data.newStatus] || `Order status: ${data.newStatus}`;

    await this.bot.telegram.sendMessage(
      data.clientTelegramId,
      `Order #${data.orderId}: ${message}`
    );
  }

  async stop(): Promise<void> {
    if (this.worker) {
      await this.worker.close();
      this.worker = null;
    }
  }
}
```

## User Role Management

Shared authentication middleware validates user role before allowing access:

```typescript
// packages/shared-types/src/roles.ts
export enum UserRole {
  CLIENT = "CLIENT",
  COURIER = "COURIER",
  ADMIN = "ADMIN",
  RESTAURANT = "RESTAURANT",
}
```

```typescript
// bots/client-bot/src/middlewares/auth.ts
import { Context, MiddlewareFn } from "telegraf";
import { getDb, UserRole } from "@project/shared-db";

export interface AuthContext extends Context {
  dbUser: {
    id: number;
    telegramId: bigint;
    role: UserRole;
    name: string;
  };
}

export function requireRole(role: UserRole): MiddlewareFn<AuthContext> {
  return async (ctx, next) => {
    if (!ctx.from) {
      return ctx.reply("Could not identify you.");
    }

    const db = getDb();
    const user = await db.user.findUnique({
      where: { telegramId: ctx.from.id },
    });

    if (!user) {
      return ctx.reply("You are not registered. Use /start to register.");
    }

    if (user.role !== role) {
      return ctx.reply("You do not have access to this bot.");
    }

    if (!user.isActive) {
      return ctx.reply("Your account has been deactivated.");
    }

    ctx.dbUser = user;
    return next();
  };
}
```

Apply the middleware to the entire bot:

```typescript
// bots/courier-bot/src/index.ts
import { Telegraf } from "telegraf";
import { requireRole, AuthContext } from "./middlewares/auth";
import { UserRole } from "@project/shared-db";

const bot = new Telegraf<AuthContext>(process.env.COURIER_BOT_TOKEN!);

bot.use(requireRole(UserRole.COURIER));

bot.command("available_orders", async (ctx) => {
  // ctx.dbUser is guaranteed to be a COURIER here
});
```

## Docker Compose for Multi-Bot Deployment

```yaml
# docker-compose.yml
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: delivery_platform
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  migrate:
    build:
      context: .
      dockerfile: Dockerfile
      target: base
    command: pnpm db:migrate
    environment:
      DATABASE_URL: postgresql://app:${DB_PASSWORD}@postgres:5432/delivery_platform
    depends_on:
      postgres:
        condition: service_healthy

  client-bot:
    build:
      context: .
      dockerfile: Dockerfile
      target: client-bot
    environment:
      DATABASE_URL: postgresql://app:${DB_PASSWORD}@postgres:5432/delivery_platform
      REDIS_URL: redis://redis:6379
      BOT_TOKEN: ${CLIENT_BOT_TOKEN}
    depends_on:
      migrate:
        condition: service_completed_successfully
      redis:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 256M

  courier-bot:
    build:
      context: .
      dockerfile: Dockerfile
      target: courier-bot
    environment:
      DATABASE_URL: postgresql://app:${DB_PASSWORD}@postgres:5432/delivery_platform
      REDIS_URL: redis://redis:6379
      BOT_TOKEN: ${COURIER_BOT_TOKEN}
    depends_on:
      migrate:
        condition: service_completed_successfully
      redis:
        condition: service_healthy
    restart: unless-stopped

  restaurant-bot:
    build:
      context: .
      dockerfile: Dockerfile
      target: restaurant-bot
    environment:
      DATABASE_URL: postgresql://app:${DB_PASSWORD}@postgres:5432/delivery_platform
      REDIS_URL: redis://redis:6379
      BOT_TOKEN: ${RESTAURANT_BOT_TOKEN}
    depends_on:
      migrate:
        condition: service_completed_successfully
      redis:
        condition: service_healthy
    restart: unless-stopped

  admin-bot:
    build:
      context: .
      dockerfile: Dockerfile
      target: admin-bot
    environment:
      DATABASE_URL: postgresql://app:${DB_PASSWORD}@postgres:5432/delivery_platform
      REDIS_URL: redis://redis:6379
      BOT_TOKEN: ${ADMIN_BOT_TOKEN}
    depends_on:
      migrate:
        condition: service_completed_successfully
      redis:
        condition: service_healthy
    restart: unless-stopped

volumes:
  pgdata:
  redisdata:
```

Multi-stage Dockerfile:

```dockerfile
FROM node:20-alpine AS base
RUN corepack enable
WORKDIR /app
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY packages/ packages/
COPY bots/ bots/
RUN pnpm install --frozen-lockfile
RUN pnpm build

FROM base AS client-bot
CMD ["node", "bots/client-bot/dist/index.js"]

FROM base AS courier-bot
CMD ["node", "bots/courier-bot/dist/index.js"]

FROM base AS restaurant-bot
CMD ["node", "bots/restaurant-bot/dist/index.js"]

FROM base AS admin-bot
CMD ["node", "bots/admin-bot/dist/index.js"]
```

## Graceful Shutdown Coordination

Every bot must handle SIGTERM/SIGINT to close connections cleanly:

```typescript
// bots/client-bot/src/index.ts
import { Telegraf } from "telegraf";
import { disconnectDb } from "@project/shared-db";
import { NotificationDispatcher } from "./notification-dispatcher";

const bot = new Telegraf(process.env.BOT_TOKEN!);
const dispatcher = new NotificationDispatcher(bot);

async function shutdown(signal: string): Promise<void> {
  console.log(`Received ${signal}. Starting graceful shutdown...`);

  // 1. Stop accepting new updates
  bot.stop(signal);

  // 2. Stop processing queue jobs (waits for current jobs to finish)
  await dispatcher.stop();

  // 3. Close database connections
  await disconnectDb();

  console.log("Shutdown complete.");
  process.exit(0);
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));

async function main(): Promise<void> {
  dispatcher.start();
  await bot.launch();
  console.log("Client bot started");
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
```

## E2E Testing Multi-Bot Flows

Use a test harness that spins up all bots and simulates Telegram updates:

```typescript
// e2e-tests/src/order-flow.test.ts
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { getDb, disconnectDb } from "@project/shared-db";
import { createQueue, QUEUE_NAMES } from "@project/queue";

describe("Order flow E2E", () => {
  const db = getDb();

  beforeAll(async () => {
    await db.$executeRaw`TRUNCATE "User", "Order" CASCADE`;

    // Seed test users
    await db.user.createMany({
      data: [
        { telegramId: 1001, role: "CLIENT", name: "Test Client" },
        { telegramId: 1002, role: "COURIER", name: "Test Courier" },
        { telegramId: 1003, role: "RESTAURANT", name: "Test Restaurant" },
      ],
    });
  });

  afterAll(async () => {
    await disconnectDb();
  });

  it("should create order and propagate through queues", async () => {
    const order = await db.order.create({
      data: {
        clientId: 1,
        restaurantId: 1,
        items: [{ name: "Pizza", quantity: 1, price: 12.99 }],
        total: 12.99,
        status: "PENDING",
      },
    });

    // Simulate restaurant confirming the order
    const clientQueue = createQueue(QUEUE_NAMES.CLIENT_NOTIFICATIONS);
    await clientQueue.add("order-confirmed", {
      type: "ORDER_STATUS_CHANGED",
      orderId: order.id,
      newStatus: "CONFIRMED",
      clientTelegramId: 1001,
    });

    // Verify order status updated in DB
    const updated = await db.order.update({
      where: { id: order.id },
      data: { status: "CONFIRMED" },
    });
    expect(updated.status).toBe("CONFIRMED");

    // Verify queue job was created
    const waiting = await clientQueue.getWaiting();
    expect(waiting.length).toBeGreaterThanOrEqual(0);

    await clientQueue.close();
  });
});
```

## Key Principles

1. **Each bot is a separate process** -- they share nothing in memory, only through the database and message queues.
2. **Database is the source of truth** -- queues are for notifications and coordination, not for storing state.
3. **Idempotent message handlers** -- queue jobs may be retried, so handlers must tolerate duplicate processing.
4. **Role-based isolation** -- each bot enforces its own role check. A courier cannot interact with the client bot.
5. **Shared packages are versioned together** -- use `workspace:*` protocol in pnpm to ensure all bots use the same version of shared code.
6. **Health checks in Docker** -- use `depends_on` with `condition: service_healthy` to ensure bots start only after infrastructure is ready.
