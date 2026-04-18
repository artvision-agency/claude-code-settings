import { expect, test } from "@playwright/test";

test.describe("smoke", () => {
  test("homepage loads and shows main heading", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/.+/);
    const h1 = page.locator("h1").first();
    await expect(h1).toBeVisible();
  });

  test("primary CTA is clickable", async ({ page }) => {
    await page.goto("/");
    const cta = page.getByRole("link", { name: /get started|start|try/i }).first();
    if (await cta.count()) {
      await cta.click();
      await expect(page).not.toHaveURL("/");
    } else {
      test.skip();
    }
  });
});

test.describe("responsive", () => {
  for (const size of [
    { name: "mobile", width: 375, height: 667 },
    { name: "tablet", width: 768, height: 1024 },
    { name: "desktop", width: 1440, height: 900 },
  ] as const) {
    test(`no horizontal scroll at ${size.name}`, async ({ page }) => {
      await page.setViewportSize({ width: size.width, height: size.height });
      await page.goto("/");
      const scrollW = await page.evaluate(() => document.documentElement.scrollWidth);
      const clientW = await page.evaluate(() => document.documentElement.clientWidth);
      expect(scrollW).toBeLessThanOrEqual(clientW + 1);
    });
  }
});
