import { describe, expect, it } from "vitest";

// Example: real code would live in src/, imported like `import { add } from "../src/math";`
function add(a: number, b: number): number {
  return a + b;
}

function divide(a: number, b: number): number {
  if (b === 0) throw new Error("division by zero");
  return a / b;
}

describe("add", () => {
  it("sums two positives", () => {
    expect(add(2, 3)).toBe(5);
  });

  it.each([
    [1, 1, 2],
    [0, 0, 0],
    [-1, 1, 0],
  ])("add(%i, %i) === %i", (a, b, expected) => {
    expect(add(a, b)).toBe(expected);
  });
});

describe("divide", () => {
  it("divides", () => {
    expect(divide(10, 2)).toBe(5);
  });

  it("throws on zero", () => {
    expect(() => divide(1, 0)).toThrowError(/division by zero/);
  });
});
