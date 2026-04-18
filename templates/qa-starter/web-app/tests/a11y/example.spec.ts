import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.describe("accessibility (axe-core)", () => {
  const pages = ["/", "/about", "/pricing"];

  for (const path of pages) {
    test(`${path} — WCAG 2.1 AA, no critical violations`, async ({ page }) => {
      const resp = await page.goto(path, { waitUntil: "domcontentloaded" });
      if (!resp || resp.status() >= 400) {
        test.skip();
      }

      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();

      const critical = results.violations.filter(
        (v) => v.impact === "critical" || v.impact === "serious",
      );

      if (critical.length) {
        console.warn(`axe violations on ${path}:`);
        for (const v of critical) {
          console.warn(`  [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length} nodes)`);
        }
      }

      expect(critical).toEqual([]);
    });
  }
});
