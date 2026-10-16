const { test, expect } = require("@playwright/test");
const gallery = require("./gallery");

test.beforeEach(async ({ page }) => {
  await gallery.stubExternal(page);
  await page.goto("/");
});

test("every meta.json entry has the fields the gallery requires", async ({ page }) => {
  const problems = await page.evaluate(
    (entries) =>
      entries.flatMap((entry) => {
        try {
          assertEntry(entry);
          return [];
        } catch (error) {
          return [error.message];
        }
      }),
    gallery.META
  );
  expect(problems).toEqual([]);
  await page.evaluate((entries) => assertOneCardPerModelAndEffort(entries), gallery.META);
});

test("a card missing a required field or company fails validation", async ({ page }) => {
  const accepted = await page.evaluate((entry) => {
    const broken = REQUIRED_FIELDS.map((field) => {
      const copy = structuredClone(entry);
      delete copy[field];
      return [`missing ${field}`, copy];
    });
    broken.push(["unmapped company", { ...entry, display_model: "Zeta 1" }]);
    broken.push(["bad released date", { ...entry, released: "soon" }]);
    return broken.flatMap(([label, copy]) => {
      try {
        assertEntry(copy);
        return [label];
      } catch {
        return [];
      }
    });
  }, gallery.META[0]);
  expect(accepted).toEqual([]);
});
