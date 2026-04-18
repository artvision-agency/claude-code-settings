import { describe, expect, it } from "vitest";

// Pure unit test for a utility. Replace with real imports from src/.
function formatPrice(cents: number, currency = "USD"): string {
  const amount = (cents / 100).toFixed(2);
  return `${amount} ${currency}`;
}

describe("formatPrice", () => {
  it("formats USD by default", () => {
    expect(formatPrice(1999)).toBe("19.99 USD");
  });

  it.each([
    [0, "0.00 USD"],
    [1, "0.01 USD"],
    [100000, "1000.00 USD"],
  ])("edges: %i cents -> %s", (input, expected) => {
    expect(formatPrice(input)).toBe(expected);
  });

  it("supports custom currency", () => {
    expect(formatPrice(500, "EUR")).toBe("5.00 EUR");
  });
});
