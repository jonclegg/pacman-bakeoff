const { test, expect } = require("@playwright/test");
const gallery = require("./gallery");

const SORT_VALUE = {
  score: (entry) => entry.score,
  cost: (entry) => entry.cost_usd,
  time: (entry) => entry.duration_ms,
  tokens: (entry) => entry.output_tokens ?? entry.tokens_total,
  released: (entry) => (entry.released == null ? null : Date.parse(entry.released)),
};

test("gallery loads every card with no console errors", async ({ page }) => {
  const consoleErrors = await gallery.openGallery(page);
  await expect(page.locator(".grid .cab")).toHaveCount(gallery.META.length);
  await expect(page.locator(".models-list input")).not.toHaveCount(0);
  await page.waitForTimeout(1500);
  expect(consoleErrors).toEqual([]);
});

test("every sort option is offered", async ({ page }) => {
  await gallery.openGallery(page);
  const keys = await page.$$eval("[data-sort]", (buttons) => buttons.map((button) => button.dataset.sort));
  expect(keys.sort()).toEqual(Object.keys(SORT_VALUE).sort());
});

for (const [key, valueOf] of Object.entries(SORT_VALUE)) {
  test(`sort by ${key} orders the cards both ways`, async ({ page }) => {
    await gallery.openGallery(page);
    const orders = {};
    for (const order of ["desc", "asc"]) {
      await page.click(`[data-sort="${key}"]`);
      await page.click(`[data-order="${order}"]`);
      await expect(page.locator(`[data-sort="${key}"]`)).toHaveAttribute("aria-checked", "true");
      await expect(page.locator(`[data-order="${order}"]`)).toHaveAttribute("aria-checked", "true");

      const slugs = await gallery.shownSlugs(page);
      expect([...slugs].sort()).toEqual(gallery.META.map((entry) => entry.slug).sort());
      const values = slugs.map((slug) => valueOf(gallery.BY_SLUG.get(slug)));
      const known = values.filter((value) => value != null);
      expect(values.slice(known.length).every((value) => value == null), "cards without a value sort last").toBe(true);
      expect(known).toEqual([...known].sort((a, b) => (order === "desc" ? b - a : a - b)));
      orders[order] = slugs;
    }
    expect(orders.asc).not.toEqual(orders.desc);
  });
}

test("search narrows the cards and an empty result can be reset", async ({ page }) => {
  await gallery.openGallery(page);
  const total = gallery.META.length;
  const target = gallery.META.find(
    (entry) => gallery.META.filter((other) => JSON.stringify(other).toLowerCase().includes(entry.run.toLowerCase())).length === 1
  );

  await page.fill("#search", target.run);
  await expect(page.locator("[data-count]")).toHaveText(`1 / ${total}`);
  expect(await gallery.shownSlugs(page)).toEqual([target.slug]);

  await page.fill("#search", "no-such-model-anywhere");
  await expect(page.locator("[data-count]")).toHaveText(`0 / ${total}`);
  await expect(page.locator(".game-over")).toBeVisible();
  await page.click(".game-over-reset");
  await expect(page.locator("[data-count]")).toHaveText(`${total} / ${total}`);
  await expect(page.locator("#search")).toHaveValue("");
});

test("model filter shows only the checked models", async ({ page }) => {
  await gallery.openGallery(page);
  const total = gallery.META.length;
  await page.click(".models-toggle");
  const options = page.locator(".models-option");
  const first = options.nth(0);
  const second = options.nth(1);
  const firstName = await first.locator(".models-name").textContent();
  const firstCount = Number(await first.locator(".models-count").textContent());
  const secondCount = Number(await second.locator(".models-count").textContent());

  await first.locator("input").check();
  await expect(page.locator("[data-count]")).toHaveText(`${firstCount} / ${total}`);
  await expect(page.locator("[data-models-value]")).toHaveText(firstName);
  const names = await page.$$eval(".grid .cab:not([hidden]) .cab-link", (links) => links.map((link) => link.firstChild.textContent));
  expect(new Set(names)).toEqual(new Set([firstName]));

  await second.locator("input").check();
  await expect(page.locator("[data-count]")).toHaveText(`${firstCount + secondCount} / ${total}`);
  await expect(page.locator("[data-models-value]")).toHaveText("2 models");

  await page.click(".models-clear");
  await expect(page.locator("[data-count]")).toHaveText(`${total} / ${total}`);
  await expect(page.locator("[data-models-value]")).toHaveText("All");
});

test("every card links to an entry page that is served", async ({ page, request }) => {
  await gallery.openGallery(page);
  const hrefs = await page.$$eval(".grid .cab-link", (links) => links.map((link) => link.getAttribute("href")));
  expect(hrefs.sort()).toEqual(gallery.META.map((entry) => `./entries/${entry.slug}.html`).sort());
  for (const href of hrefs) {
    const response = await request.get(href.replace("./", "/"));
    expect(response.status(), href).toBe(200);
    expect(response.headers()["content-type"], href).toContain("text/html");
  }
});

test("clicking a card opens its game and back returns to the gallery", async ({ page }) => {
  await gallery.openGallery(page);
  const [slug] = await gallery.shownSlugs(page);
  await page.locator(`.cab-link[href="./entries/${slug}.html"]`).click();
  await expect(page.locator(".play")).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`#${slug.replace(/\./g, "\\.")}$`));
  await expect
    .poll(() => page.locator(".play-frame").evaluate((frame) => frame.contentWindow.location.pathname))
    .toMatch(new RegExp(`/entries/${slug.replace(/\./g, "\\.")}\\.html$`));

  await page.click(".play-back");
  await expect(page.locator(".play")).toBeHidden();
  await expect(page.locator(".play-frame")).toHaveCount(0);
});

test("a #slug link opens that game directly", async ({ page }) => {
  const entry = gallery.META.at(-1);
  await gallery.openGallery(page, `#${entry.slug}`);
  await expect(page.locator(".play")).toBeVisible();
  await expect
    .poll(() => page.locator(".play-frame").evaluate((frame) => frame.contentWindow.location.pathname))
    .toContain(`/entries/${entry.slug}.html`);
});
