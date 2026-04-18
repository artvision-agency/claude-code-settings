import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    setupFiles: ["tests/setup.ts"],
    include: ["tests/**/*.{test,spec}.{ts,tsx,js,jsx}", "src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["node_modules", "dist", ".idea", ".git", ".cache"],
    reporters: ["default", ["junit", { outputFile: "reports/junit.xml" }]],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov", "json-summary"],
      reportsDirectory: "coverage",
      include: ["src/**/*.{ts,tsx,js,jsx}"],
      exclude: [
        "src/**/*.d.ts",
        "src/**/*.test.{ts,tsx,js,jsx}",
        "src/**/*.spec.{ts,tsx,js,jsx}",
        "src/**/index.{ts,tsx,js,jsx}",
      ],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 75,
        statements: 80,
      },
    },
  },
});
