---
name: e2e-bot-testing
description: End-to-end testing for Telegram bots using MTProto userbot automation with YAML scenarios and CI/CD integration
---

# E2E Testing for Telegram Bots

## Overview

E2E bot testing uses a real Telegram user account (userbot) to interact with bots through MTProto protocol.
This simulates actual user behavior: sending messages, tapping buttons, receiving responses, and verifying outcomes.

## YAML Scenario Format

Every test scenario is a YAML file describing a sequence of actions and assertions against a Telegram bot.

### Basic Scenario Structure

```yaml
# scenarios/start-command.yaml
name: Start command flow
description: Verify the /start command returns welcome message and main menu
tags:
  - smoke
  - onboarding
bot: "@MyGameBot"
timeout: 30s
rate_limit: 2s

steps:
  - action: send_command
    command: /start
    assert:
      - type: contains
        text: "Welcome to MyGame!"
      - type: keyboard
        buttons:
          - "Play"
          - "Leaderboard"
          - "Settings"

  - action: click_button
    text: "Play"
    assert:
      - type: contains
        text: "Choose game mode"
      - type: keyboard
        buttons:
          - "Single Player"
          - "Multiplayer"
          - "Back"

  - action: click_button
    text: "Back"
    assert:
      - type: contains
        text: "Welcome to MyGame!"
```

### Advanced Scenario with Variables and Conditional Steps

```yaml
# scenarios/game-flow.yaml
name: Full game play-through
description: Play a single-player game round from start to finish
tags:
  - game
  - full-flow
bot: "@MyGameBot"
timeout: 120s
rate_limit: 1s

variables:
  username: "TestUser_{{ random_id }}"

steps:
  - action: send_command
    command: /start

  - action: click_button
    text: "Play"

  - action: click_button
    text: "Single Player"
    assert:
      - type: contains
        text: "Game started"

  - action: wait
    duration: 3s

  - action: click_callback
    data: "answer:1"
    assert:
      - type: matches
        pattern: "(Correct|Wrong)! Score: \\d+"

  - action: click_callback
    data: "answer:2"

  - action: wait
    duration: 5s

  - action: send_message
    text: "/score"
    assert:
      - type: matches
        pattern: "Your score: \\d+"
      - type: contains
        text: "{{ username }}"
```

### Inline Keyboard (Callback) Testing

```yaml
# scenarios/inline-buttons.yaml
name: Inline keyboard navigation
tags:
  - inline
bot: "@MyGameBot"
timeout: 30s

steps:
  - action: send_command
    command: /settings

  - action: click_callback
    data: "settings:sound"
    assert:
      - type: contains
        text: "Sound settings"
      - type: inline_keyboard
        rows:
          - ["On", "Off"]
          - ["Back"]

  - action: click_callback
    data: "sound:off"
    assert:
      - type: contains
        text: "Sound disabled"
      - type: callback_answer
        text: "Settings saved!"
```

## MTProto Userbot Setup

### GramJS (TypeScript/Node.js) Setup

```typescript
// test/setup/client.ts
import { TelegramClient } from 'telegram'
import { StringSession } from 'telegram/sessions'

const API_ID = parseInt(process.env.TELEGRAM_API_ID!)
const API_HASH = process.env.TELEGRAM_API_HASH!
const SESSION = process.env.TELEGRAM_SESSION!

let client: TelegramClient | null = null

export async function getClient(): Promise<TelegramClient> {
  if (client && client.connected) return client

  client = new TelegramClient(
    new StringSession(SESSION),
    API_ID,
    API_HASH,
    {
      connectionRetries: 3,
      useWSS: false,
      requestRetries: 3,
    }
  )

  await client.connect()
  return client
}

export async function disconnectClient(): Promise<void> {
  if (client) {
    await client.disconnect()
    client = null
  }
}
```

### Generating a Session String

```typescript
// scripts/generate-session.ts
import { TelegramClient } from 'telegram'
import { StringSession } from 'telegram/sessions'
import input from 'input'

const API_ID = parseInt(process.env.TELEGRAM_API_ID!)
const API_HASH = process.env.TELEGRAM_API_HASH!

async function main() {
  const client = new TelegramClient(new StringSession(''), API_ID, API_HASH, {
    connectionRetries: 3,
  })

  await client.start({
    phoneNumber: async () => await input.text('Phone number: '),
    password: async () => await input.text('2FA password: '),
    phoneCode: async () => await input.text('Code: '),
    onError: (err) => console.error(err),
  })

  console.log('Session string:', client.session.save())
  await client.disconnect()
}

main()
```

## Action Types

### send_message

Send a plain text message to the bot.

```typescript
// runner/actions/sendMessage.ts
import { Api } from 'telegram'

export async function sendMessage(
  client: TelegramClient,
  botUsername: string,
  text: string
): Promise<Api.Message> {
  const result = await client.sendMessage(botUsername, { message: text })
  return result
}
```

### send_command

Send a bot command (shorthand for `send_message` with `/` prefix).

```typescript
export async function sendCommand(
  client: TelegramClient,
  botUsername: string,
  command: string
): Promise<Api.Message> {
  const text = command.startsWith('/') ? command : `/${command}`
  return sendMessage(client, botUsername, text)
}
```

### click_button

Click a reply keyboard button (not inline). Sends the button text as a message.

```typescript
export async function clickButton(
  client: TelegramClient,
  botUsername: string,
  buttonText: string,
  searchLimit = 5
): Promise<Api.Message> {
  const messages = await client.getMessages(botUsername, { limit: searchLimit })
  for (const msg of messages) {
    if (msg.replyMarkup instanceof Api.ReplyKeyboardMarkup) {
      for (const row of msg.replyMarkup.rows) {
        for (const button of row.buttons) {
          if (button.text === buttonText) {
            return sendMessage(client, botUsername, button.text)
          }
        }
      }
    }
  }
  throw new Error(`Button "${buttonText}" not found in last ${searchLimit} messages`)
}
```

### click_callback

Click an inline keyboard button using callback data.

```typescript
export async function clickCallback(
  client: TelegramClient,
  botUsername: string,
  callbackData: string,
  searchLimit = 5
): Promise<Api.messages.BotCallbackAnswer> {
  const messages = await client.getMessages(botUsername, { limit: searchLimit })
  for (const msg of messages) {
    if (msg.replyMarkup instanceof Api.ReplyInlineMarkup) {
      for (const row of msg.replyMarkup.rows) {
        for (const button of row.buttons) {
          if (button instanceof Api.KeyboardButtonCallback) {
            const data = Buffer.from(button.data).toString('utf-8')
            if (data === callbackData) {
              return client.invoke(
                new Api.messages.GetBotCallbackAnswer({
                  peer: botUsername,
                  msgId: msg.id,
                  data: button.data,
                })
              )
            }
          }
        }
      }
    }
  }
  throw new Error(`Callback "${callbackData}" not found in last ${searchLimit} messages`)
}
```

### wait

Pause execution for a specified duration.

```typescript
export function wait(durationMs: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, durationMs))
}
```

## Response Matching

### contains

Check that the bot's response contains a substring.

```typescript
export function assertContains(message: string, expected: string): void {
  if (!message.includes(expected)) {
    throw new AssertionError(
      `Expected message to contain "${expected}", got: "${message.slice(0, 200)}"`
    )
  }
}
```

### matches (regex)

Check response against a regular expression.

```typescript
export function assertMatches(message: string, pattern: string): void {
  const regex = new RegExp(pattern)
  if (!regex.test(message)) {
    throw new AssertionError(
      `Expected message to match /${pattern}/, got: "${message.slice(0, 200)}"`
    )
  }
}
```

### keyboard

Verify reply keyboard buttons.

```typescript
export function assertKeyboard(
  markup: Api.TypeReplyMarkup | undefined,
  expectedButtons: string[]
): void {
  if (!(markup instanceof Api.ReplyKeyboardMarkup)) {
    throw new AssertionError('Expected ReplyKeyboardMarkup, got: ' + markup?.className)
  }
  const actual = markup.rows.flatMap((row) => row.buttons.map((b) => b.text))
  for (const expected of expectedButtons) {
    if (!actual.includes(expected)) {
      throw new AssertionError(
        `Expected keyboard button "${expected}", found: [${actual.join(', ')}]`
      )
    }
  }
}
```

## Headless CLI Mode for CI/CD

```typescript
// cli/index.ts
import { program } from 'commander'
import { loadScenarios } from './loader'
import { runScenarios } from './runner'

program
  .name('bot-e2e')
  .description('E2E testing CLI for Telegram bots')
  .option('-s, --scenarios <glob>', 'Scenario files glob', 'scenarios/**/*.yaml')
  .option('-t, --tags <tags>', 'Filter by tags (comma-separated)')
  .option('-b, --bot <username>', 'Override bot username')
  .option('--timeout <ms>', 'Global timeout', '60000')
  .option('--rate-limit <ms>', 'Delay between scenarios', '3000')
  .option('--json', 'Output results as JSON')
  .option('--bail', 'Stop on first failure')
  .action(async (options) => {
    const scenarios = await loadScenarios(options.scenarios, options.tags?.split(','))

    const results = await runScenarios(scenarios, {
      botOverride: options.bot,
      timeout: parseInt(options.timeout),
      rateLimit: parseInt(options.rateLimit),
      bail: options.bail,
    })

    if (options.json) {
      console.log(JSON.stringify(results, null, 2))
    } else {
      printResults(results)
    }

    process.exit(results.failed > 0 ? 1 : 0)
  })

program.parse()
```

### CI/CD Integration (GitHub Actions)

```yaml
# .github/workflows/bot-e2e.yml
name: Bot E2E Tests
on:
  push:
    branches: [main]
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 20

      - run: npm ci

      - name: Run E2E tests
        env:
          TELEGRAM_API_ID: ${{ secrets.TELEGRAM_API_ID }}
          TELEGRAM_API_HASH: ${{ secrets.TELEGRAM_API_HASH }}
          TELEGRAM_SESSION: ${{ secrets.TELEGRAM_SESSION }}
        run: |
          npx bot-e2e \
            --scenarios scenarios/**/*.yaml \
            --tags smoke \
            --rate-limit 3000 \
            --json > results.json

      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-results
          path: results.json
```

## Multi-Bot Test Orchestration

```typescript
// runner/orchestrator.ts
interface BotTarget {
  username: string
  scenarios: ScenarioFile[]
}

export async function orchestrate(targets: BotTarget[], concurrency = 1): Promise<OrchestratorResult> {
  const allResults: ScenarioResult[] = []

  // Run bots sequentially (sharing one userbot session)
  for (const target of targets) {
    console.log(`\nTesting bot: ${target.username}`)

    for (const scenario of target.scenarios) {
      const result = await runSingleScenario(scenario, target.username)
      allResults.push(result)

      // Rate limit between scenarios to avoid Telegram flood
      await wait(3000)
    }

    // Longer pause between different bots
    await wait(5000)
  }

  return {
    total: allResults.length,
    passed: allResults.filter((r) => r.status === 'passed').length,
    failed: allResults.filter((r) => r.status === 'failed').length,
    skipped: allResults.filter((r) => r.status === 'skipped').length,
    results: allResults,
  }
}
```

## Rate Limiting Between Scenarios

```typescript
// runner/rateLimiter.ts
export class RateLimiter {
  private lastAction = 0
  private readonly minInterval: number

  constructor(minIntervalMs: number) {
    this.minInterval = minIntervalMs
  }

  async throttle(): Promise<void> {
    const now = Date.now()
    const elapsed = now - this.lastAction
    if (elapsed < this.minInterval) {
      await wait(this.minInterval - elapsed)
    }
    this.lastAction = Date.now()
  }
}

// Usage in scenario runner
const limiter = new RateLimiter(2000) // 2s between actions

for (const step of scenario.steps) {
  await limiter.throttle()
  await executeStep(client, step)
}
```

## Test Result Reporting (JSON Output)

```typescript
// types/results.ts
export interface ScenarioResult {
  name: string
  bot: string
  tags: string[]
  status: 'passed' | 'failed' | 'skipped'
  duration: number
  steps: StepResult[]
  error?: string
}

export interface StepResult {
  action: string
  status: 'passed' | 'failed' | 'skipped'
  duration: number
  assertions: AssertionResult[]
  error?: string
}

export interface AssertionResult {
  type: string
  expected: string
  actual: string
  passed: boolean
}

// Example JSON output:
// {
//   "total": 12,
//   "passed": 10,
//   "failed": 1,
//   "skipped": 1,
//   "duration": 87430,
//   "results": [
//     {
//       "name": "Start command flow",
//       "bot": "@MyGameBot",
//       "tags": ["smoke", "onboarding"],
//       "status": "passed",
//       "duration": 4523,
//       "steps": [...]
//     }
//   ]
// }
```

## Common Pitfalls

### Button Search Limits

When using `click_button` or `click_callback`, the action searches recent messages for the keyboard.
If the bot sends multiple messages, the keyboard may not be on the latest message.

```typescript
// BAD: default limit of 1 message may miss the keyboard
await clickCallback(client, bot, 'answer:1')

// GOOD: search more messages
await clickCallback(client, bot, 'answer:1', 10)
```

### Timing Issues

Bots may take variable time to respond. Always add wait steps or use polling.

```typescript
// runner/utils/waitForResponse.ts
export async function waitForResponse(
  client: TelegramClient,
  botUsername: string,
  afterMessageId: number,
  timeoutMs = 10000,
  pollInterval = 500
): Promise<Api.Message> {
  const deadline = Date.now() + timeoutMs

  while (Date.now() < deadline) {
    const messages = await client.getMessages(botUsername, { limit: 5 })
    const newMessage = messages.find(
      (m) => m.id > afterMessageId && m.senderId?.toString() !== 'self'
    )
    if (newMessage) return newMessage
    await wait(pollInterval)
  }

  throw new Error(`Timeout: no response from ${botUsername} within ${timeoutMs}ms`)
}
```

### Flood Wait Errors

Telegram rate-limits aggressively. Handle FloodWaitError gracefully.

```typescript
import { FloodWaitError } from 'telegram/errors'

export async function safeAction<T>(fn: () => Promise<T>, retries = 3): Promise<T> {
  for (let i = 0; i < retries; i++) {
    try {
      return await fn()
    } catch (err) {
      if (err instanceof FloodWaitError) {
        console.warn(`Flood wait: sleeping ${err.seconds}s`)
        await wait(err.seconds * 1000 + 1000)
      } else {
        throw err
      }
    }
  }
  throw new Error('Max retries exceeded')
}
```

## Database for Test Run Tracking

```typescript
// db/schema.ts (using Drizzle + SQLite)
import { sqliteTable, text, integer } from 'drizzle-orm/sqlite-core'

export const testRuns = sqliteTable('test_runs', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  startedAt: text('started_at').notNull(),
  finishedAt: text('finished_at'),
  total: integer('total').notNull().default(0),
  passed: integer('passed').notNull().default(0),
  failed: integer('failed').notNull().default(0),
  skipped: integer('skipped').notNull().default(0),
  trigger: text('trigger').notNull(), // 'manual' | 'ci' | 'schedule'
  branch: text('branch'),
  commitSha: text('commit_sha'),
  resultsJson: text('results_json'),
})

export const scenarioResults = sqliteTable('scenario_results', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  runId: integer('run_id').notNull().references(() => testRuns.id),
  name: text('name').notNull(),
  bot: text('bot').notNull(),
  status: text('status').notNull(), // 'passed' | 'failed' | 'skipped'
  duration: integer('duration').notNull(),
  error: text('error'),
})
```

```typescript
// db/tracker.ts
import { db } from './connection'
import { testRuns, scenarioResults } from './schema'

export async function saveTestRun(results: OrchestratorResult, meta: RunMeta): Promise<number> {
  const [run] = await db.insert(testRuns).values({
    startedAt: new Date().toISOString(),
    finishedAt: new Date().toISOString(),
    total: results.total,
    passed: results.passed,
    failed: results.failed,
    skipped: results.skipped,
    trigger: meta.trigger,
    branch: meta.branch,
    commitSha: meta.commitSha,
    resultsJson: JSON.stringify(results),
  }).returning()

  for (const r of results.results) {
    await db.insert(scenarioResults).values({
      runId: run.id,
      name: r.name,
      bot: r.bot,
      status: r.status,
      duration: r.duration,
      error: r.error ?? null,
    })
  }

  return run.id
}
```
