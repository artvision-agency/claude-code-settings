import { expect, test } from "@playwright/test";

// Visual regression baseline. First run creates snapshots under
// tests/visual/__snapshots__/. Subsequent runs compare and fail on diff >threshold.
//
// To refresh (after intentional UI change):
//   npx playwright test tests/visual --update-snapshots

test.describe("visual regression", () => {
  const pages = [
    { path: "/", name: "home" },
    { path: "/pricing", name: "pricing" },
  ];

  for (const p of pages) {
    test(`${p.name} — full page snapshot`, async ({ page }) => {
      const resp = await page.goto(p.path, { waitUntil: "networkidle" });
      if (!resp || resp.status() >= 400) test.skip();

      // Hide dynamic elements that break snapshots (time, random).
      await page.addStyleTag({
        content: `
          [data-dynamic], .timestamp, .countdown, video, iframe { visibility: hidden !important; }
          * { animation: none !important; transition: none !important; }
        `,
      });

      await expect(page).toHaveScreenshot(`${p.name}.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.01, // 1% tolerance
        animations: "disabled",
      });
    });
  }
});
