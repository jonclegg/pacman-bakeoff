const fs = require("fs");
const path = require("path");
const { expect } = require("@playwright/test");

const META = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "entries", "meta.json"), "utf8"));
const BY_SLUG = new Map(META.map((entry) => [entry.slug, entry]));
const STUBS = [
  [/googletagmanager\.com/, "application/javascript"],
  [/fonts\.googleapis\.com/, "text/css"],
  [/fonts\.gstatic\.com/, "font/woff2"],
];

async function stubExternal(page) {
  for (const [pattern, contentType] of STUBS) {
    await page.route(pattern, (route) => route.fulfill({ status: 200, contentType, body: "" }));
  }
}

// Opens the gallery and returns the console errors raised by the gallery itself.
// Errors inside entry iframes are the games' own and are not the gallery's to fix.
async function openGallery(page, hash = "") {
  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error" && !msg.location().url.includes("/entries/")) consoleErrors.push(msg.text());
  });
  await page.addInitScript(() => {
    if (window !== window.top) return;
    window.__galleryErrors = [];
    addEventListener("error", (event) => window.__galleryErrors.push(String(event.message)));
    addEventListener("unhandledrejection", (event) => window.__galleryErrors.push(String(event.reason)));
  });
  await stubExternal(page);
  await page.goto(`/${hash}`);
  await page.waitForFunction(
    () => window.__galleryErrors.length || document.querySelector("[data-count]").textContent !== "--"
  );
  expect(await page.evaluate(() => window.__galleryErrors)).toEqual([]);
  await expect(page.locator("[data-count]")).toHaveText(`${META.length} / ${META.length}`);
  return consoleErrors;
}

async function shownSlugs(page) {
  return page.$$eval(".grid .cab:not([hidden]) .cab-link", (links) =>
    links.map((link) => link.getAttribute("href").replace("./entries/", "").replace(/\.html$/, ""))
  );
}

module.exports = { META, BY_SLUG, stubExternal, openGallery, shownSlugs };
