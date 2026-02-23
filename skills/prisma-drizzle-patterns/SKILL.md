---
name: prisma-drizzle-patterns
description: TypeScript ORM patterns for Prisma and Drizzle including schema design, migrations, testing, and performance optimization
---

# TypeScript ORM Patterns: Prisma and Drizzle

## Prisma: Schema Design, Relations, Migrations, Seeding

### Schema Design

```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String
  role      Role     @default(PLAYER)
  createdAt DateTime @default(now()) @map("created_at")
  updatedAt DateTime @updatedAt @map("updated_at")
  deletedAt DateTime? @map("deleted_at")

  profile   Profile?
  games     GamePlayer[]
  scores    Score[]

  @@index([email])
  @@index([deletedAt])
  @@map("users")
}

model Profile {
  id        String @id @default(cuid())
  userId    String @unique @map("user_id")
  avatar    String?
  bio       String?
  level     Int    @default(1)
  xp        Int    @default(0)

  user User @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@map("profiles")
}

model Game {
  id        String     @id @default(cuid())
  code      String     @unique
  status    GameStatus @default(WAITING)
  maxPlayers Int       @default(4) @map("max_players")
  config    Json       @default("{}")
  createdAt DateTime   @default(now()) @map("created_at")
  updatedAt DateTime   @updatedAt @map("updated_at")

  players GamePlayer[]
  rounds  Round[]

  @@index([status])
  @@index([code])
  @@map("games")
}

model GamePlayer {
  id       String @id @default(cuid())
  gameId   String @map("game_id")
  userId   String @map("user_id")
  joinedAt DateTime @default(now()) @map("joined_at")
  isHost   Boolean @default(false) @map("is_host")

  game Game @relation(fields: [gameId], references: [id], onDelete: Cascade)
  user User @relation(fields: [userId], references: [id])

  @@unique([gameId, userId])
  @@map("game_players")
}

model Round {
  id       String @id @default(cuid())
  gameId   String @map("game_id")
  number   Int
  data     Json   @default("{}")

  game   Game    @relation(fields: [gameId], references: [id], onDelete: Cascade)
  scores Score[]

  @@unique([gameId, number])
  @@map("rounds")
}

model Score {
  id      String @id @default(cuid())
  roundId String @map("round_id")
  userId  String @map("user_id")
  points  Int

  round Round @relation(fields: [roundId], references: [id], onDelete: Cascade)
  user  User  @relation(fields: [userId], references: [id])

  @@unique([roundId, userId])
  @@map("scores")
}

enum Role {
  PLAYER
  MODERATOR
  ADMIN
}

enum GameStatus {
  WAITING
  IN_PROGRESS
  FINISHED
  CANCELLED
}
```

### Migrations

```bash
# Create a migration from schema changes
npx prisma migrate dev --name add_game_tables

# Apply migrations in production (no prompts, no seed)
npx prisma migrate deploy

# Reset database (dev only: drop, recreate, migrate, seed)
npx prisma migrate reset
```

### Seeding

```typescript
// prisma/seed.ts
import { PrismaClient, Role } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  // Upsert to make seeding idempotent
  const admin = await prisma.user.upsert({
    where: { email: 'admin@example.com' },
    update: {},
    create: {
      email: 'admin@example.com',
      name: 'Admin',
      role: Role.ADMIN,
      profile: {
        create: { level: 99, xp: 999999 },
      },
    },
  })

  // Seed test players
  const players = await Promise.all(
    Array.from({ length: 10 }, (_, i) =>
      prisma.user.upsert({
        where: { email: `player${i}@example.com` },
        update: {},
        create: {
          email: `player${i}@example.com`,
          name: `Player ${i}`,
          profile: { create: { level: i + 1, xp: i * 100 } },
        },
      })
    )
  )

  console.log(`Seeded admin: ${admin.id}, players: ${players.length}`)
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
```

```json
// package.json
{
  "prisma": {
    "seed": "tsx prisma/seed.ts"
  }
}
```

## Prisma: Generated Client, Type-Safe Queries, Transactions

```typescript
// services/gameService.ts
import { PrismaClient, GameStatus, Prisma } from '@prisma/client'

const prisma = new PrismaClient()

// Type-safe query with includes
async function getGameWithPlayers(gameId: string) {
  return prisma.game.findUniqueOrThrow({
    where: { id: gameId },
    include: {
      players: {
        include: {
          user: {
            select: { id: true, name: true, email: true },
          },
        },
        orderBy: { joinedAt: 'asc' },
      },
      rounds: {
        include: { scores: true },
        orderBy: { number: 'asc' },
      },
    },
  })
}

// Cursor-based pagination
async function getLeaderboard(cursor?: string, take = 20) {
  return prisma.user.findMany({
    take,
    ...(cursor ? { skip: 1, cursor: { id: cursor } } : {}),
    select: {
      id: true,
      name: true,
      profile: { select: { level: true, xp: true } },
    },
    orderBy: { profile: { xp: 'desc' } },
    where: { deletedAt: null },
  })
}

// Interactive transaction for game creation
async function createGame(hostUserId: string, maxPlayers: number) {
  return prisma.$transaction(async (tx) => {
    const code = generateGameCode()

    const game = await tx.game.create({
      data: {
        code,
        maxPlayers,
        players: {
          create: { userId: hostUserId, isHost: true },
        },
      },
      include: { players: true },
    })

    // Update host's profile
    await tx.profile.update({
      where: { userId: hostUserId },
      data: { xp: { increment: 10 } },
    })

    return game
  })
}

// Batch operations with transaction
async function endRound(gameId: string, roundNumber: number, scores: { userId: string; points: number }[]) {
  return prisma.$transaction(async (tx) => {
    const round = await tx.round.create({
      data: {
        gameId,
        number: roundNumber,
        scores: {
          createMany: {
            data: scores,
          },
        },
      },
      include: { scores: true },
    })

    // Update all player XP in bulk
    await Promise.all(
      scores.map((s) =>
        tx.profile.update({
          where: { userId: s.userId },
          data: { xp: { increment: s.points } },
        })
      )
    )

    return round
  })
}

// Soft delete pattern
async function softDeleteUser(userId: string) {
  return prisma.user.update({
    where: { id: userId },
    data: { deletedAt: new Date() },
  })
}

// Middleware for automatic soft delete filtering
prisma.$use(async (params, next) => {
  if (params.model === 'User') {
    if (params.action === 'findMany' || params.action === 'findFirst') {
      params.args.where = { ...params.args.where, deletedAt: null }
    }
  }
  return next(params)
})
```

## Drizzle ORM: Schema Definition, Query Builder, Migrations

### Schema Definition (PostgreSQL)

```typescript
// drizzle/schema.ts
import { pgTable, text, integer, timestamp, boolean, json, pgEnum, uniqueIndex, index } from 'drizzle-orm/pg-core'
import { relations } from 'drizzle-orm'
import { createId } from '@paralleldrive/cuid2'

export const roleEnum = pgEnum('role', ['PLAYER', 'MODERATOR', 'ADMIN'])
export const gameStatusEnum = pgEnum('game_status', ['WAITING', 'IN_PROGRESS', 'FINISHED', 'CANCELLED'])

export const users = pgTable('users', {
  id: text('id').$defaultFn(() => createId()).primaryKey(),
  email: text('email').notNull().unique(),
  name: text('name').notNull(),
  role: roleEnum('role').default('PLAYER').notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
  deletedAt: timestamp('deleted_at'),
}, (table) => ({
  emailIdx: index('users_email_idx').on(table.email),
  deletedAtIdx: index('users_deleted_at_idx').on(table.deletedAt),
}))

export const profiles = pgTable('profiles', {
  id: text('id').$defaultFn(() => createId()).primaryKey(),
  userId: text('user_id').notNull().unique().references(() => users.id, { onDelete: 'cascade' }),
  avatar: text('avatar'),
  bio: text('bio'),
  level: integer('level').default(1).notNull(),
  xp: integer('xp').default(0).notNull(),
})

export const games = pgTable('games', {
  id: text('id').$defaultFn(() => createId()).primaryKey(),
  code: text('code').notNull().unique(),
  status: gameStatusEnum('status').default('WAITING').notNull(),
  maxPlayers: integer('max_players').default(4).notNull(),
  config: json('config').default({}).notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
}, (table) => ({
  statusIdx: index('games_status_idx').on(table.status),
}))

export const gamePlayers = pgTable('game_players', {
  id: text('id').$defaultFn(() => createId()).primaryKey(),
  gameId: text('game_id').notNull().references(() => games.id, { onDelete: 'cascade' }),
  userId: text('user_id').notNull().references(() => users.id),
  joinedAt: timestamp('joined_at').defaultNow().notNull(),
  isHost: boolean('is_host').default(false).notNull(),
}, (table) => ({
  gameUserUnique: uniqueIndex('game_players_game_user_idx').on(table.gameId, table.userId),
}))

export const rounds = pgTable('rounds', {
  id: text('id').$defaultFn(() => createId()).primaryKey(),
  gameId: text('game_id').notNull().references(() => games.id, { onDelete: 'cascade' }),
  number: integer('number').notNull(),
  data: json('data').default({}).notNull(),
}, (table) => ({
  gameNumberUnique: uniqueIndex('rounds_game_number_idx').on(table.gameId, table.number),
}))

export const scores = pgTable('scores', {
  id: text('id').$defaultFn(() => createId()).primaryKey(),
  roundId: text('round_id').notNull().references(() => rounds.id, { onDelete: 'cascade' }),
  userId: text('user_id').notNull().references(() => users.id),
  points: integer('points').notNull(),
}, (table) => ({
  roundUserUnique: uniqueIndex('scores_round_user_idx').on(table.roundId, table.userId),
}))

// Relations
export const usersRelations = relations(users, ({ one, many }) => ({
  profile: one(profiles, { fields: [users.id], references: [profiles.userId] }),
  gamePlayers: many(gamePlayers),
  scores: many(scores),
}))

export const gamesRelations = relations(games, ({ many }) => ({
  players: many(gamePlayers),
  rounds: many(rounds),
}))

export const gamePlayersRelations = relations(gamePlayers, ({ one }) => ({
  game: one(games, { fields: [gamePlayers.gameId], references: [games.id] }),
  user: one(users, { fields: [gamePlayers.userId], references: [users.id] }),
}))

export const roundsRelations = relations(rounds, ({ one, many }) => ({
  game: one(games, { fields: [rounds.gameId], references: [games.id] }),
  scores: many(scores),
}))

export const scoresRelations = relations(scores, ({ one }) => ({
  round: one(rounds, { fields: [scores.roundId], references: [rounds.id] }),
  user: one(users, { fields: [scores.userId], references: [users.id] }),
}))
```

### Query Builder

```typescript
// db/queries.ts
import { eq, and, isNull, desc, sql, gt } from 'drizzle-orm'
import { db } from './connection'
import { users, profiles, games, gamePlayers, rounds, scores } from './schema'

// Simple select
async function getUserByEmail(email: string) {
  const [user] = await db
    .select()
    .from(users)
    .where(and(eq(users.email, email), isNull(users.deletedAt)))
    .limit(1)
  return user ?? null
}

// Join query
async function getGameWithPlayers(gameId: string) {
  return db
    .select({
      game: games,
      player: {
        userId: gamePlayers.userId,
        isHost: gamePlayers.isHost,
        name: users.name,
      },
    })
    .from(games)
    .innerJoin(gamePlayers, eq(games.id, gamePlayers.gameId))
    .innerJoin(users, eq(gamePlayers.userId, users.id))
    .where(eq(games.id, gameId))
}

// Relational query (Drizzle query API)
async function getGameWithRelations(gameId: string) {
  return db.query.games.findFirst({
    where: eq(games.id, gameId),
    with: {
      players: {
        with: { user: true },
        orderBy: (gp, { asc }) => [asc(gp.joinedAt)],
      },
      rounds: {
        with: { scores: true },
        orderBy: (r, { asc }) => [asc(r.number)],
      },
    },
  })
}

// Aggregate query
async function getLeaderboard(limit = 20) {
  return db
    .select({
      userId: users.id,
      name: users.name,
      totalPoints: sql<number>`COALESCE(SUM(${scores.points}), 0)`.as('total_points'),
    })
    .from(users)
    .leftJoin(scores, eq(users.id, scores.userId))
    .where(isNull(users.deletedAt))
    .groupBy(users.id, users.name)
    .orderBy(desc(sql`total_points`))
    .limit(limit)
}

// Insert with returning
async function createUser(data: { email: string; name: string }) {
  const [user] = await db.insert(users).values(data).returning()
  return user
}

// Update
async function updateProfile(userId: string, data: { level?: number; xp?: number }) {
  const [updated] = await db
    .update(profiles)
    .set({ ...data })
    .where(eq(profiles.userId, userId))
    .returning()
  return updated
}

// Upsert (insert on conflict update)
async function upsertScore(roundId: string, userId: string, points: number) {
  return db
    .insert(scores)
    .values({ roundId, userId, points })
    .onConflictDoUpdate({
      target: [scores.roundId, scores.userId],
      set: { points },
    })
    .returning()
}

// Transaction
async function createGameWithHost(hostUserId: string, code: string) {
  return db.transaction(async (tx) => {
    const [game] = await tx.insert(games).values({ code }).returning()

    await tx.insert(gamePlayers).values({
      gameId: game.id,
      userId: hostUserId,
      isHost: true,
    })

    await tx
      .update(profiles)
      .set({ xp: sql`${profiles.xp} + 10` })
      .where(eq(profiles.userId, hostUserId))

    return game
  })
}
```

## Drizzle: SQLite + better-sqlite3 Integration

```typescript
// db/sqlite.ts
import { drizzle } from 'drizzle-orm/better-sqlite3'
import Database from 'better-sqlite3'
import * as schema from './schema-sqlite'

const sqlite = new Database('app.db')
sqlite.pragma('journal_mode = WAL')
sqlite.pragma('foreign_keys = ON')

export const db = drizzle(sqlite, { schema })
```

```typescript
// db/schema-sqlite.ts
import { sqliteTable, text, integer } from 'drizzle-orm/sqlite-core'

export const users = sqliteTable('users', {
  id: text('id').primaryKey(),
  email: text('email').notNull().unique(),
  name: text('name').notNull(),
  role: text('role', { enum: ['PLAYER', 'MODERATOR', 'ADMIN'] }).default('PLAYER').notNull(),
  createdAt: text('created_at').notNull().$defaultFn(() => new Date().toISOString()),
  deletedAt: text('deleted_at'),
})

export const scores = sqliteTable('scores', {
  id: text('id').primaryKey(),
  userId: text('user_id').notNull().references(() => users.id),
  points: integer('points').notNull(),
  createdAt: text('created_at').notNull().$defaultFn(() => new Date().toISOString()),
})
```

## Drizzle: PostgreSQL + node-postgres

```typescript
// db/postgres.ts
import { drizzle } from 'drizzle-orm/node-postgres'
import { Pool } from 'pg'
import * as schema from './schema'

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000,
})

export const db = drizzle(pool, { schema })

// Graceful shutdown
export async function closeDatabase() {
  await pool.end()
}
```

## Migration Strategies

### Drizzle Migrations

```typescript
// drizzle.config.ts
import { defineConfig } from 'drizzle-kit'

export default defineConfig({
  schema: './drizzle/schema.ts',
  out: './drizzle/migrations',
  dialect: 'postgresql',
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
})
```

```bash
# Generate migration from schema changes
npx drizzle-kit generate

# Apply migrations
npx drizzle-kit migrate

# Push schema directly (dev only, no migration files)
npx drizzle-kit push

# Open Drizzle Studio (visual database browser)
npx drizzle-kit studio
```

### Production Migration Script

```typescript
// scripts/migrate.ts
import { migrate } from 'drizzle-orm/node-postgres/migrator'
import { db } from '../db/postgres'

async function main() {
  console.log('Running migrations...')
  await migrate(db, { migrationsFolder: './drizzle/migrations' })
  console.log('Migrations complete')
  process.exit(0)
}

main().catch((err) => {
  console.error('Migration failed:', err)
  process.exit(1)
})
```

## Testing with In-Memory Databases

### SQLite In-Memory (Drizzle)

```typescript
// test/db.ts
import { drizzle } from 'drizzle-orm/better-sqlite3'
import Database from 'better-sqlite3'
import { migrate } from 'drizzle-orm/better-sqlite3/migrator'
import * as schema from '../drizzle/schema-sqlite'

export function createTestDb() {
  const sqlite = new Database(':memory:')
  sqlite.pragma('foreign_keys = ON')
  const db = drizzle(sqlite, { schema })

  // Apply migrations to in-memory db
  migrate(db, { migrationsFolder: './drizzle/migrations-sqlite' })

  return { db, close: () => sqlite.close() }
}
```

```typescript
// test/gameService.test.ts
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { createTestDb } from './db'
import { users, games, gamePlayers } from '../drizzle/schema-sqlite'
import { eq } from 'drizzle-orm'

describe('GameService', () => {
  let db: ReturnType<typeof createTestDb>['db']
  let close: () => void

  beforeEach(() => {
    const testDb = createTestDb()
    db = testDb.db
    close = testDb.close
  })

  afterEach(() => close())

  it('should create a game with host', async () => {
    // Seed a user
    await db.insert(users).values({ id: 'user1', email: 'test@example.com', name: 'Test' })

    // Create game
    const [game] = await db.insert(games).values({ id: 'game1', code: 'ABC123' }).returning()
    await db.insert(gamePlayers).values({ id: 'gp1', gameId: game.id, userId: 'user1', isHost: true })

    // Assert
    const players = await db.select().from(gamePlayers).where(eq(gamePlayers.gameId, game.id))
    expect(players).toHaveLength(1)
    expect(players[0].isHost).toBe(true)
  })
})
```

### Prisma Test Setup (with Docker)

```typescript
// test/prismaTestSetup.ts
import { PrismaClient } from '@prisma/client'
import { execSync } from 'node:child_process'

const TEST_DATABASE_URL = `postgresql://postgres:postgres@localhost:5433/test_${process.pid}`

export async function setupTestDatabase(): Promise<PrismaClient> {
  process.env.DATABASE_URL = TEST_DATABASE_URL

  // Create the test database
  execSync(`createdb -h localhost -p 5433 -U postgres test_${process.pid}`, {
    env: { ...process.env, PGPASSWORD: 'postgres' },
  })

  // Run migrations
  execSync('npx prisma migrate deploy', { env: process.env })

  return new PrismaClient({ datasourceUrl: TEST_DATABASE_URL })
}

export async function teardownTestDatabase(prisma: PrismaClient): Promise<void> {
  await prisma.$disconnect()
  execSync(`dropdb -h localhost -p 5433 -U postgres test_${process.pid}`, {
    env: { ...process.env, PGPASSWORD: 'postgres' },
  })
}
```

## Connection Pooling and Performance

### Prisma Connection Pool

```typescript
// Prisma manages connection pool internally
const prisma = new PrismaClient({
  datasources: {
    db: {
      url: `${process.env.DATABASE_URL}?connection_limit=20&pool_timeout=30`,
    },
  },
})
```

### Drizzle with pg Pool

```typescript
import { Pool } from 'pg'

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,               // Maximum connections in pool
  min: 5,                // Minimum idle connections
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000,
  statement_timeout: 10_000,
})

// Monitor pool health
pool.on('error', (err) => console.error('Pool error:', err))
pool.on('connect', () => console.log('New connection established'))
```

### Query Performance Tips

```typescript
// 1. Select only needed columns (both Prisma and Drizzle)
// Prisma:
await prisma.user.findMany({ select: { id: true, name: true } })
// Drizzle:
await db.select({ id: users.id, name: users.name }).from(users)

// 2. Use pagination (cursor-based is better than offset)
// Drizzle cursor-based:
async function paginate(cursor?: string, limit = 20) {
  const query = db.select().from(users).orderBy(users.id).limit(limit)
  if (cursor) {
    return query.where(gt(users.id, cursor))
  }
  return query
}

// 3. Batch inserts (Drizzle)
await db.insert(scores).values(
  results.map((r) => ({ roundId, userId: r.userId, points: r.points }))
)

// 4. Use prepared statements for repeated queries (Drizzle)
const getUserById = db
  .select()
  .from(users)
  .where(eq(users.id, sql.placeholder('id')))
  .prepare('get_user_by_id')

const user = await getUserById.execute({ id: 'some-id' })
```

## Common Patterns

### Soft Delete

```typescript
// Drizzle: soft delete helper
import { isNull, and } from 'drizzle-orm'

function withSoftDelete<T extends { deletedAt: any }>(table: T) {
  return isNull(table.deletedAt)
}

// Usage
await db.select().from(users).where(and(withSoftDelete(users), eq(users.role, 'PLAYER')))

// Soft delete action
await db.update(users).set({ deletedAt: new Date().toISOString() }).where(eq(users.id, userId))
```

### Automatic Timestamps

```typescript
// Drizzle: updated_at trigger (PostgreSQL)
// In a migration SQL file:
// CREATE OR REPLACE FUNCTION update_updated_at()
// RETURNS TRIGGER AS $$
// BEGIN
//   NEW.updated_at = NOW();
//   RETURN NEW;
// END;
// $$ LANGUAGE plpgsql;
//
// CREATE TRIGGER users_updated_at
//   BEFORE UPDATE ON users
//   FOR EACH ROW
//   EXECUTE FUNCTION update_updated_at();

// Or handle in application code:
async function updateUser(id: string, data: Partial<typeof users.$inferInsert>) {
  return db.update(users).set({ ...data, updatedAt: new Date() }).where(eq(users.id, id))
}
```

### Enums

```typescript
// Prisma: enums are defined in schema.prisma (see above)

// Drizzle PostgreSQL: native enum
export const gameStatusEnum = pgEnum('game_status', ['WAITING', 'IN_PROGRESS', 'FINISHED', 'CANCELLED'])

// Drizzle SQLite: text with enum constraint (no native enum support)
export const games = sqliteTable('games', {
  status: text('status', { enum: ['WAITING', 'IN_PROGRESS', 'FINISHED', 'CANCELLED'] }).notNull(),
})

// TypeScript type from Drizzle schema
type GameStatus = typeof games.$inferSelect['status']
```

## Choosing Between Prisma and Drizzle

### When to Use Prisma

- Rapid prototyping where schema-first design is preferred
- Teams that prefer declarative schema files (`.prisma`)
- Projects needing Prisma Studio for visual database browsing
- When you want automatic client generation with full TypeScript types
- Complex relation handling with nested creates/updates
- Projects that use multiple database providers (switching between them)

### When to Use Drizzle

- Performance-critical applications (Drizzle generates fewer queries)
- When you want SQL-like syntax in TypeScript
- SQLite projects (Drizzle's SQLite support is more mature)
- When you need full control over generated SQL
- Serverless/edge deployments (smaller bundle size)
- Teams comfortable writing SQL who want type safety on top

### Key Differences

```
| Feature              | Prisma                    | Drizzle                    |
|---------------------|---------------------------|----------------------------|
| Schema definition   | .prisma file              | TypeScript files           |
| Query style         | Object-based API          | SQL-like builder           |
| Bundle size         | ~2MB (engine binary)      | ~50KB                      |
| Migrations          | prisma migrate            | drizzle-kit                |
| Raw SQL             | $queryRaw / $executeRaw   | sql`` template tag         |
| Relations           | Implicit (schema-defined) | Explicit (relations())     |
| Transactions        | $transaction              | db.transaction             |
| Edge support        | Prisma Accelerate needed  | Native                     |
| SQLite              | Basic support             | First-class support        |
| Learning curve      | Lower                     | Higher (SQL knowledge)     |
```

### Migration Path: Prisma to Drizzle

If migrating from Prisma to Drizzle, use `drizzle-kit introspect` to generate Drizzle schema from an existing database:

```bash
# Generate Drizzle schema from existing Prisma-managed database
npx drizzle-kit introspect
```

This produces TypeScript schema files matching your current database structure, allowing a gradual migration without changing the database.
