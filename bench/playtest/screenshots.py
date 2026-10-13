"""Screenshots for the v4 visual check (bench/scoring/v4.md).

Usage: python3 bench/playtest/screenshots.py name1,name2 --out DIR [--base URL]

Writes DIR/<name>/1-attract-1s.jpg, 2-attract-6s.jpg (no input), 3-start (Enter, then any Start button),
4-play-5s and 5-play-14s (random held arrows), plus capture.json with page errors.
"""
import argparse, asyncio, json, random
from pathlib import Path
from playwright.async_api import async_playwright

_ap = argparse.ArgumentParser()
_ap.add_argument("names")
_ap.add_argument("--out", required=True, type=Path)
_ap.add_argument("--base", default="https://jonclegg.github.io/pacman-bakeoff/entries/")
ARGS = _ap.parse_args()
BASE, OUT, NAMES = ARGS.base, ARGS.out, ARGS.names.split(",")
ARROWS = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"]
BUTTON_JS = """() => {
  const rx = /start|play|begin|insert|new game/i;
  const els = [...document.querySelectorAll('button, [role=button], a, .btn, .button, div, span')].filter(e => {
    const r = e.getBoundingClientRect(); const st = getComputedStyle(e);
    return r.width > 10 && r.height > 10 && r.width < 500 && st.visibility !== 'hidden' && st.display !== 'none'
      && st.opacity !== '0' && e.children.length <= 2 && rx.test((e.innerText||'').trim()) && (e.innerText||'').length < 40; });
  const b = els.find(e => e.tagName === 'BUTTON') || els[0];
  if (!b) return null; const r = b.getBoundingClientRect(); return {x: r.x + r.width/2, y: r.y + r.height/2};
}"""


async def shoot(page, directory, label):
    await page.screenshot(path=str(directory / f"{label}.jpg"), type="jpeg", quality=88)


async def bot(page, seconds):
    held = None
    end = asyncio.get_event_loop().time() + seconds
    while asyncio.get_event_loop().time() < end:
        key = random.choice(ARROWS)
        if held:
            await page.keyboard.up(held)
        await page.keyboard.down(key); held = key
        await asyncio.sleep(random.uniform(0.4, 1.0))
    if held:
        await page.keyboard.up(held)


async def capture(browser, name, semaphore):
    async with semaphore:
        directory = OUT / name; directory.mkdir(parents=True, exist_ok=True)
        context = await browser.new_context(viewport={"width": 900, "height": 1000}, device_scale_factor=2)
        page = await context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:200]))
        await page.goto(BASE + name + ".html", wait_until="load", timeout=30000)
        await asyncio.sleep(1.0); await shoot(page, directory, "1-attract-1s")
        await asyncio.sleep(5.0); await shoot(page, directory, "2-attract-6s")
        await page.keyboard.press("Enter"); await asyncio.sleep(0.3)
        button = await page.evaluate(BUTTON_JS)
        if button:
            await page.mouse.click(button["x"], button["y"])
        await asyncio.sleep(1.5); await shoot(page, directory, "3-start")
        await bot(page, 5); await shoot(page, directory, "4-play-5s")
        await bot(page, 9); await shoot(page, directory, "5-play-14s")
        (directory / "capture.json").write_text(json.dumps({"errors": errors, "start_button": bool(button)}, indent=1))
        await context.close()
        print("done", name, flush=True)


async def main():
    semaphore = asyncio.Semaphore(6)
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        await asyncio.gather(*(capture(browser, n, semaphore) for n in NAMES))
        await browser.close()

asyncio.run(main())
