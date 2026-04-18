// Global test setup — runs once before all tests.
// Vitest picks it up via vitest.config.ts -> test.setupFiles.

import { afterAll, afterEach, beforeAll, beforeEach, vi } from "vitest";

// ---------- Global hooks ----------

beforeAll(() => {
  // Example: set deterministic timezone for date-based tests
  process.env.TZ = "UTC";
});

beforeEach(() => {
  // Reset any module-level state between tests if needed.
});

afterEach(() => {
  vi.restoreAllMocks();
});

afterAll(() => {
  // Clean up global resources (DB pools, open handles).
});

// ---------- Global mocks ----------

// Example: stub fetch by default. Override per-test with vi.spyOn or vi.mocked.
// globalThis.fetch = vi.fn();

// ---------- Type augmentations (if needed) ----------

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Vi {
    interface AsymmetricMatchersContaining {
      // add custom matcher types here
    }
  }
}

export {};
