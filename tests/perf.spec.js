const { test, expect } = require("@playwright/test");
const gallery = require("./gallery");

const BUDGET = {
  desktop: { layers: 80, animations: 15 },
  mobile: { layers: 40, animations: 15 },
};
const SLOW_FRAME_MS = 50;
const MAX_SLOW_FRAME_SHARE = 0.1;

async function layerCount(page) {
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("LayerTree.enable");
  const layers = await new Promise((resolve) => {
    cdp.on("LayerTree.layerTreeDidChange", (event) => event.layers && resolve(event.layers));
    page.evaluate(() => scrollBy(0, 1));
  });
  await cdp.detach();
  return layers.length;
}

test("idle gallery stays within the layer and animation budget", async ({ page }, testInfo) => {
  const budget = BUDGET[testInfo.project.name];
  await gallery.openGallery(page);
  await page.waitForTimeout(2500);
  const animations = await page.evaluate(() => document.getAnimations().filter((a) => a.playState === "running").length);
  const layers = await layerCount(page);
  testInfo.annotations.push({ type: "perf", description: `layers=${layers} running animations=${animations}` });
  expect(layers).toBeLessThanOrEqual(budget.layers);
  expect(animations).toBeLessThanOrEqual(budget.animations);
});

test("scrolling the whole gallery stays within the frame budget", async ({ page }, testInfo) => {
  await gallery.openGallery(page);
  await page.waitForTimeout(2500);
  await page.evaluate(() => {
    window.__frames = [];
    let last = performance.now();
    const tick = (now) => {
      window.__frames.push(now - last);
      last = now;
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });

  const viewport = page.viewportSize();
  await page.mouse.move(viewport.width / 2, viewport.height / 2);
  const bottom = await page.evaluate(() => document.documentElement.scrollHeight - innerHeight);
  while ((await page.evaluate(() => scrollY)) < bottom - 2) {
    await page.mouse.wheel(0, Math.round(viewport.height * 0.8));
    await page.waitForTimeout(250);
  }

  const frames = await page.evaluate(() => window.__frames.slice(1));
  const slow = frames.filter((ms) => ms > SLOW_FRAME_MS).length;
  const share = slow / frames.length;
  testInfo.annotations.push({
    type: "perf",
    description: `frames=${frames.length} slow=${slow} (${(share * 100).toFixed(1)}%) worst=${Math.round(Math.max(...frames))}ms`,
  });
  expect(share).toBeLessThanOrEqual(MAX_SLOW_FRAME_SHARE);
});
