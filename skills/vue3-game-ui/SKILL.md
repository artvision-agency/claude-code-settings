---
name: vue3-game-ui
description: Vue 3 game UI development with Composition API, Pinia, WebSocket multiplayer, animations, and multi-platform builds
---

# Vue 3 Game UI Development

## Composition API and Composables for Game Logic

All game logic MUST be extracted into composables. Never put game logic directly in components.

### Core Game Composable Pattern

```typescript
// composables/useGameEngine.ts
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useGameStore } from '@/stores/game'
import { useSound } from '@/composables/useSound'

export function useGameEngine() {
  const store = useGameStore()
  const { playSound } = useSound()

  const gameState = ref<'idle' | 'playing' | 'paused' | 'finished'>('idle')
  const frameId = ref<number | null>(null)
  const lastTimestamp = ref(0)
  const deltaTime = ref(0)

  const isPlaying = computed(() => gameState.value === 'playing')

  function startGame() {
    gameState.value = 'playing'
    store.resetScore()
    playSound('game-start')
    lastTimestamp.value = performance.now()
    frameId.value = requestAnimationFrame(gameLoop)
  }

  function gameLoop(timestamp: number) {
    deltaTime.value = (timestamp - lastTimestamp.value) / 1000
    lastTimestamp.value = timestamp

    if (gameState.value !== 'playing') return

    store.updateGameObjects(deltaTime.value)
    store.checkCollisions()
    store.updateScore(deltaTime.value)

    frameId.value = requestAnimationFrame(gameLoop)
  }

  function pauseGame() {
    gameState.value = 'paused'
    if (frameId.value) cancelAnimationFrame(frameId.value)
  }

  function resumeGame() {
    gameState.value = 'playing'
    lastTimestamp.value = performance.now()
    frameId.value = requestAnimationFrame(gameLoop)
  }

  onUnmounted(() => {
    if (frameId.value) cancelAnimationFrame(frameId.value)
  })

  return { gameState, isPlaying, deltaTime, startGame, pauseGame, resumeGame }
}
```

### Card Game Composable

```typescript
// composables/useCardGame.ts
import { ref, computed } from 'vue'
import type { Card, Deck, Hand } from '@/types/game'

export function useCardGame(deckSize = 52) {
  const deck = ref<Deck>([])
  const playerHand = ref<Hand>([])
  const opponentHand = ref<Hand>([])
  const discardPile = ref<Card[]>([])
  const selectedCardIndex = ref<number | null>(null)

  const canPlay = computed(() => selectedCardIndex.value !== null)

  function shuffle(cards: Card[]): Card[] {
    const shuffled = [...cards]
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
    }
    return shuffled
  }

  function drawCard(hand: Hand, count = 1): void {
    for (let i = 0; i < count && deck.value.length > 0; i++) {
      const card = deck.value.pop()!
      hand.push({ ...card, faceUp: true })
    }
  }

  function playCard(index: number): Card | null {
    if (index < 0 || index >= playerHand.value.length) return null
    const [card] = playerHand.value.splice(index, 1)
    discardPile.value.push(card)
    selectedCardIndex.value = null
    return card
  }

  return {
    deck, playerHand, opponentHand, discardPile,
    selectedCardIndex, canPlay,
    shuffle, drawCard, playCard,
  }
}
```

## Pinia State Management for Game State

```typescript
// stores/game.ts
import { defineStore } from 'pinia'

interface GameState {
  score: number
  level: number
  lives: number
  combo: number
  objects: GameObject[]
  settings: GameSettings
}

interface GameObject {
  id: string
  type: string
  x: number
  y: number
  vx: number
  vy: number
  active: boolean
}

interface GameSettings {
  soundEnabled: boolean
  musicVolume: number
  sfxVolume: number
  hapticEnabled: boolean
  difficulty: 'easy' | 'normal' | 'hard'
}

export const useGameStore = defineStore('game', {
  state: (): GameState => ({
    score: 0,
    level: 1,
    lives: 3,
    combo: 0,
    objects: [],
    settings: {
      soundEnabled: true,
      musicVolume: 0.7,
      sfxVolume: 1.0,
      hapticEnabled: true,
      difficulty: 'normal',
    },
  }),

  getters: {
    highScore: (state) => {
      const stored = localStorage.getItem('highScore')
      return Math.max(state.score, stored ? parseInt(stored, 10) : 0)
    },
    activeObjects: (state) => state.objects.filter((o) => o.active),
    difficultyMultiplier: (state) => {
      const map = { easy: 0.7, normal: 1.0, hard: 1.5 }
      return map[state.settings.difficulty]
    },
  },

  actions: {
    resetScore() {
      this.score = 0
      this.combo = 0
      this.level = 1
      this.lives = 3
    },
    addScore(points: number) {
      this.combo++
      this.score += points * this.combo * this.difficultyMultiplier
      if (this.score > this.highScore) {
        localStorage.setItem('highScore', String(this.score))
      }
    },
    resetCombo() {
      this.combo = 0
    },
    updateGameObjects(dt: number) {
      for (const obj of this.objects) {
        if (!obj.active) continue
        obj.x += obj.vx * dt
        obj.y += obj.vy * dt
      }
    },
    checkCollisions() {
      // Implement per-game collision logic
    },
    updateScore(_dt: number) {
      // Implement per-game scoring
    },
    loadSettings() {
      const saved = localStorage.getItem('gameSettings')
      if (saved) this.settings = JSON.parse(saved)
    },
    saveSettings() {
      localStorage.setItem('gameSettings', JSON.stringify(this.settings))
    },
  },
})
```

## WebSocket Real-Time Multiplayer Integration

```typescript
// composables/useMultiplayer.ts
import { ref, onUnmounted } from 'vue'
import { useGameStore } from '@/stores/game'

interface MultiplayerMessage {
  type: 'join' | 'leave' | 'action' | 'state_sync' | 'ping' | 'pong'
  payload: unknown
  timestamp: number
  playerId?: string
}

export function useMultiplayer(serverUrl: string) {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const roomId = ref<string | null>(null)
  const players = ref<Map<string, PlayerInfo>>(new Map())
  const latency = ref(0)
  const store = useGameStore()

  let pingInterval: ReturnType<typeof setInterval> | null = null
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  let reconnectAttempts = 0
  const MAX_RECONNECT_ATTEMPTS = 5

  function connect(room: string, token: string) {
    roomId.value = room
    const url = `${serverUrl}?room=${room}&token=${token}`
    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      connected.value = true
      reconnectAttempts = 0
      startPing()
    }

    ws.value.onmessage = (event) => {
      const msg: MultiplayerMessage = JSON.parse(event.data)
      handleMessage(msg)
    }

    ws.value.onclose = () => {
      connected.value = false
      stopPing()
      attemptReconnect()
    }

    ws.value.onerror = () => {
      ws.value?.close()
    }
  }

  function handleMessage(msg: MultiplayerMessage) {
    switch (msg.type) {
      case 'state_sync':
        store.$patch(msg.payload as Partial<typeof store.$state>)
        break
      case 'action':
        store.applyRemoteAction(msg.payload)
        break
      case 'join':
        players.value.set(msg.playerId!, msg.payload as PlayerInfo)
        break
      case 'leave':
        players.value.delete(msg.playerId!)
        break
      case 'pong':
        latency.value = Date.now() - msg.timestamp
        break
    }
  }

  function send(type: MultiplayerMessage['type'], payload: unknown) {
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return
    ws.value.send(JSON.stringify({ type, payload, timestamp: Date.now() }))
  }

  function startPing() {
    pingInterval = setInterval(() => send('ping', null), 5000)
  }

  function stopPing() {
    if (pingInterval) clearInterval(pingInterval)
  }

  function attemptReconnect() {
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return
    reconnectAttempts++
    const delay = Math.min(1000 * 2 ** reconnectAttempts, 30000)
    reconnectTimeout = setTimeout(() => {
      if (roomId.value) connect(roomId.value, '')
    }, delay)
  }

  function disconnect() {
    stopPing()
    if (reconnectTimeout) clearTimeout(reconnectTimeout)
    ws.value?.close()
    ws.value = null
  }

  onUnmounted(disconnect)

  return { connected, latency, players, connect, disconnect, send }
}
```

## CSS Animations and Transitions for Cards/Effects

```vue
<!-- components/GameCard.vue -->
<template>
  <div
    class="card-wrapper"
    :class="{ 'card--selected': selected, 'card--played': played }"
    @click="$emit('select')"
  >
    <Transition name="card-flip" mode="out-in">
      <div v-if="faceUp" key="front" class="card card--front">
        <span class="card__suit">{{ card.suit }}</span>
        <span class="card__rank">{{ card.rank }}</span>
      </div>
      <div v-else key="back" class="card card--back" />
    </Transition>
  </div>
</template>

<style scoped>
.card-wrapper {
  perspective: 800px;
  cursor: pointer;
  transition: transform 0.2s ease;
}
.card-wrapper:hover {
  transform: translateY(-8px);
}
.card--selected {
  transform: translateY(-16px) scale(1.05);
  filter: drop-shadow(0 8px 16px rgba(0, 0, 0, 0.3));
}
.card--played {
  animation: card-play 0.5s ease-out forwards;
}

.card {
  width: 80px;
  height: 120px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  backface-visibility: hidden;
}
.card--front {
  background: white;
  border: 2px solid #333;
}
.card--back {
  background: linear-gradient(135deg, #1a5276, #2e86c1);
  border: 2px solid #154360;
}

/* Flip transition */
.card-flip-enter-active,
.card-flip-leave-active {
  transition: transform 0.4s ease, opacity 0.2s ease;
}
.card-flip-enter-from {
  transform: rotateY(-90deg);
  opacity: 0;
}
.card-flip-leave-to {
  transform: rotateY(90deg);
  opacity: 0;
}

/* Play animation */
@keyframes card-play {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.2) translateY(-30px); opacity: 0.8; }
  100% { transform: scale(0.5) translateY(-60px); opacity: 0; }
}

/* Combo effects */
@keyframes combo-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.3); text-shadow: 0 0 20px gold; }
}
.combo-text {
  animation: combo-pulse 0.6s ease-in-out;
  color: gold;
  font-weight: bold;
}
</style>
```

## Responsive Game UI (Mobile-First)

```vue
<!-- layouts/GameLayout.vue -->
<template>
  <div class="game-layout" :class="{ 'game-layout--landscape': isLandscape }">
    <header class="game-hud">
      <div class="game-hud__score">{{ store.score }}</div>
      <div class="game-hud__level">Lv. {{ store.level }}</div>
      <div class="game-hud__lives">
        <span v-for="i in store.lives" :key="i" class="heart">&#10084;</span>
      </div>
    </header>
    <main class="game-area">
      <slot />
    </main>
    <footer class="game-controls">
      <slot name="controls" />
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useScreenOrientation } from '@/composables/useScreenOrientation'
import { useGameStore } from '@/stores/game'

const store = useGameStore()
const { isLandscape } = useScreenOrientation()
</script>

<style scoped>
.game-layout {
  display: grid;
  grid-template-rows: 48px 1fr auto;
  height: 100dvh;
  width: 100vw;
  overflow: hidden;
  touch-action: manipulation;
  user-select: none;
  -webkit-user-select: none;
}
.game-hud {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  font-size: 14px;
}
.game-area {
  position: relative;
  overflow: hidden;
}
.game-controls {
  padding: 8px;
  padding-bottom: env(safe-area-inset-bottom, 8px);
  background: rgba(0, 0, 0, 0.4);
}

/* Tablet */
@media (min-width: 768px) {
  .game-hud { font-size: 18px; padding: 0 24px; }
  .game-layout { grid-template-rows: 56px 1fr auto; }
}

/* Desktop */
@media (min-width: 1024px) {
  .game-layout {
    max-width: 800px;
    margin: 0 auto;
  }
}

/* Landscape mobile */
.game-layout--landscape {
  grid-template-rows: 36px 1fr auto;
}
.game-layout--landscape .game-hud {
  font-size: 12px;
}
</style>
```

## Multi-Platform Builds (Vite for VK Games, Yandex Games)

```typescript
// vite.config.ts
import { defineConfig, type UserConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const platform = process.env.VITE_PLATFORM || 'web'

const platformConfigs: Record<string, Partial<UserConfig>> = {
  web: {
    base: '/',
  },
  vk: {
    base: './',
    build: {
      outDir: 'dist-vk',
      assetsInlineLimit: 8192,
    },
  },
  yandex: {
    base: './',
    build: {
      outDir: 'dist-yandex',
      assetsInlineLimit: 4096,
    },
  },
}

export default defineConfig({
  plugins: [vue()],
  define: {
    __PLATFORM__: JSON.stringify(platform),
  },
  ...platformConfigs[platform],
})
```

```typescript
// platforms/vk.ts
import bridge from '@vkontakte/vk-bridge'

export async function initVKPlatform() {
  await bridge.send('VKWebAppInit')
  const user = await bridge.send('VKWebAppGetUserInfo')
  return { userId: user.id, name: user.first_name, avatar: user.photo_100 }
}

export async function showVKAd(): Promise<boolean> {
  try {
    await bridge.send('VKWebAppShowNativeAds', { ad_format: 'reward' })
    return true
  } catch {
    return false
  }
}
```

```typescript
// platforms/yandex.ts
declare const YaGames: { init: () => Promise<YandexSDK> }

export async function initYandexPlatform() {
  const ysdk = await YaGames.init()
  const player = await ysdk.getPlayer()
  return { sdk: ysdk, playerId: player.getUniqueID() }
}
```

## Sound Effects and Haptic Feedback

```typescript
// composables/useSound.ts
import { ref } from 'vue'
import { Howl } from 'howler'
import { useGameStore } from '@/stores/game'

const sounds = new Map<string, Howl>()

export function useSound() {
  const store = useGameStore()
  const loaded = ref(false)

  function preload(manifest: Record<string, string>) {
    for (const [name, src] of Object.entries(manifest)) {
      sounds.set(name, new Howl({ src: [src], preload: true, volume: store.settings.sfxVolume }))
    }
    loaded.value = true
  }

  function playSound(name: string) {
    if (!store.settings.soundEnabled) return
    const sound = sounds.get(name)
    if (sound) {
      sound.volume(store.settings.sfxVolume)
      sound.play()
    }
  }

  function stopAll() {
    for (const sound of sounds.values()) sound.stop()
  }

  return { loaded, preload, playSound, stopAll }
}

// composables/useHaptic.ts
export function useHaptic() {
  const store = useGameStore()

  function vibrate(pattern: number | number[]) {
    if (!store.settings.hapticEnabled) return
    if ('vibrate' in navigator) navigator.vibrate(pattern)
  }

  const light = () => vibrate(10)
  const medium = () => vibrate(30)
  const heavy = () => vibrate(50)
  const success = () => vibrate([30, 50, 30])
  const error = () => vibrate([50, 30, 50, 30, 50])

  return { vibrate, light, medium, heavy, success, error }
}
```

## Game Loop Patterns in Vue

```typescript
// composables/useGameLoop.ts
import { ref, onUnmounted } from 'vue'

type UpdateFn = (dt: number) => void

export function useGameLoop() {
  const fps = ref(0)
  const running = ref(false)
  let frameId: number | null = null
  let lastTime = 0
  let fpsCounter = 0
  let fpsTime = 0
  const callbacks: UpdateFn[] = []

  function onUpdate(fn: UpdateFn) {
    callbacks.push(fn)
  }

  function tick(timestamp: number) {
    const dt = Math.min((timestamp - lastTime) / 1000, 0.1) // cap at 100ms
    lastTime = timestamp

    fpsCounter++
    fpsTime += dt
    if (fpsTime >= 1) {
      fps.value = fpsCounter
      fpsCounter = 0
      fpsTime = 0
    }

    for (const cb of callbacks) cb(dt)

    if (running.value) frameId = requestAnimationFrame(tick)
  }

  function start() {
    if (running.value) return
    running.value = true
    lastTime = performance.now()
    frameId = requestAnimationFrame(tick)
  }

  function stop() {
    running.value = false
    if (frameId !== null) cancelAnimationFrame(frameId)
  }

  onUnmounted(stop)

  return { fps, running, start, stop, onUpdate }
}
```

## Performance Optimization

```typescript
// Virtual list for leaderboards / inventory
// composables/useVirtualList.ts
import { ref, computed } from 'vue'

export function useVirtualList<T>(items: Ref<T[]>, itemHeight: number, containerHeight: number) {
  const scrollTop = ref(0)

  const visibleRange = computed(() => {
    const start = Math.floor(scrollTop.value / itemHeight)
    const end = Math.min(start + Math.ceil(containerHeight / itemHeight) + 2, items.value.length)
    return { start, end }
  })

  const visibleItems = computed(() =>
    items.value.slice(visibleRange.value.start, visibleRange.value.end).map((item, i) => ({
      item,
      index: visibleRange.value.start + i,
      style: { transform: `translateY(${(visibleRange.value.start + i) * itemHeight}px)` },
    }))
  )

  const totalHeight = computed(() => items.value.length * itemHeight)

  function onScroll(e: Event) {
    scrollTop.value = (e.target as HTMLElement).scrollTop
  }

  return { visibleItems, totalHeight, onScroll }
}
```

```typescript
// Lazy component loading
// router/index.ts
const GameBoard = () => import('@/views/GameBoard.vue')
const Leaderboard = () => import('@/views/Leaderboard.vue')
const Shop = () => import('@/views/Shop.vue')

// Use shallowRef for large game objects that do not need deep reactivity
import { shallowRef } from 'vue'
const particleSystem = shallowRef<ParticleSystem>(new ParticleSystem())
```

## TypeScript Strict Mode with Game Types

```typescript
// types/game.ts
export type Suit = 'hearts' | 'diamonds' | 'clubs' | 'spades'
export type Rank = 'A' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9' | '10' | 'J' | 'Q' | 'K'

export interface Card {
  id: string
  suit: Suit
  rank: Rank
  faceUp: boolean
  value: number
}

export type Deck = Card[]
export type Hand = Card[]

export interface PlayerInfo {
  id: string
  name: string
  avatar: string
  score: number
  connected: boolean
}

export interface GameConfig {
  maxPlayers: number
  turnTimeLimit: number
  deckCount: number
  rules: GameRules
}

export interface GameRules {
  allowDraw: boolean
  maxHandSize: number
  winCondition: 'empty_hand' | 'highest_score' | 'target_score'
  targetScore?: number
}

// Discriminated union for game events
export type GameEvent =
  | { type: 'card_played'; playerId: string; card: Card }
  | { type: 'card_drawn'; playerId: string; count: number }
  | { type: 'turn_started'; playerId: string; timeLimit: number }
  | { type: 'round_ended'; scores: Record<string, number> }
  | { type: 'game_over'; winner: string; finalScores: Record<string, number> }

// Strict event handler
export function handleGameEvent(event: GameEvent): void {
  switch (event.type) {
    case 'card_played':
      console.log(`${event.playerId} played ${event.card.rank} of ${event.card.suit}`)
      break
    case 'card_drawn':
      console.log(`${event.playerId} drew ${event.count} card(s)`)
      break
    case 'turn_started':
      console.log(`Turn started for ${event.playerId}, ${event.timeLimit}s`)
      break
    case 'round_ended':
      console.log('Round scores:', event.scores)
      break
    case 'game_over':
      console.log(`Winner: ${event.winner}`)
      break
    default: {
      const _exhaustive: never = event
      throw new Error(`Unhandled event: ${_exhaustive}`)
    }
  }
}
```
