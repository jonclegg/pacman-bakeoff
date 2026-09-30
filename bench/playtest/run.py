"""Automated Pac-Man playtester.

Usage: python3 bench/playtest/run.py name1,name2 --out DIR [--secs 90] [--concurrency 4] [--base URL]

--base is the entries URL prefix; use .../pacman-bakeoff/dev/entries/ to test the dev preview.
Writes DIR/<name>.json and DIR/shots/. Needs `pip install playwright && playwright install chromium`.

Loads each entry in headless Chromium, starts the game, drives it with a random wall-following
bot (arrow keys, with WASD windows), tracks Pac-Man and the four ghosts by colour blobs on the
main canvas, and records audio/fps/scroll/error instrumentation. Pac static for 4 s despite 3+
directions triggers a screenshot + restart attempt, so game-over screens aren't counted as stuck.
"""
import argparse, asyncio, json, math, random, time
from pathlib import Path
from playwright.async_api import async_playwright

_ap = argparse.ArgumentParser()
_ap.add_argument("names")
_ap.add_argument("--out", required=True, type=Path)
_ap.add_argument("--secs", type=float, default=90)
_ap.add_argument("--concurrency", type=int, default=4)
_ap.add_argument("--base", default="https://jonclegg.github.io/pacman-bakeoff/entries/")
ARGS = _ap.parse_args()

INIT_JS = (Path(__file__).parent / "init.js").read_text()
OUT = ARGS.out; OUT.mkdir(parents=True, exist_ok=True)
SHOTS = OUT / "shots"; SHOTS.mkdir(exist_ok=True)
PLAY_SECONDS = ARGS.secs
CONCURRENCY = ARGS.concurrency
BASE = ARGS.base
SAMPLE = 0.2
ARROWS = {"U": "ArrowUp", "D": "ArrowDown", "L": "ArrowLeft", "R": "ArrowRight"}
WASD = {"U": "w", "D": "s", "L": "a", "R": "d"}
VEC = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
PERP = {"U": "LR", "D": "LR", "L": "UD", "R": "UD"}
GHOSTS = {"2": "red", "3": "pink", "4": "cyan", "5": "orange"}
BUTTON_RE = r"start|play|again|restart|new game|retry|begin|insert|continue|resume"

FIND_BUTTON_JS = """(re) => {
  const rx = new RegExp(re, 'i');
  const els = [...document.querySelectorAll('button, [role=button], a, .btn, .button, div, span')]
    .filter(e => { const r = e.getBoundingClientRect(); const st = getComputedStyle(e);
      return r.width > 10 && r.height > 10 && r.width < 500 && st.visibility !== 'hidden' && st.display !== 'none'
        && st.opacity !== '0' && e.children.length <= 2 && rx.test((e.innerText || '').trim()) && (e.innerText||'').length < 40; });
  const pref = els.find(e => e.tagName === 'BUTTON') || els[0];
  if (!pref) return null;
  const r = pref.getBoundingClientRect();
  return {x: r.x + r.width / 2, y: r.y + r.height / 2, text: pref.innerText.trim().slice(0, 30)};
}"""


def pick(frame):
    """Choose Pac-Man and ghost blobs from an analyzer frame."""
    if not frame or frame.get("err"):
        return None, {}, 8
    x0, y0, x1, y1 = frame["bbox"]
    bw = max(1, x1 - x0)
    tile = max(6.0, bw / 28.0)
    amin, amax = (0.3 * tile) ** 2, (2.6 * tile) ** 2

    def valid(b):
        asp = max(b["w"], b["h"]) / max(1, min(b["w"], b["h"]))
        return (amin <= b["n"] <= amax and asp <= 2.2
                and x0 - tile <= b["x"] <= x1 + tile and y0 - tile <= b["y"] <= y1 + tile)

    blobs = frame["blobs"]
    pacs = [b for b in blobs["1"] if valid(b)]
    pac = pacs[0] if pacs else None
    ghosts = {}
    for k, name in GHOSTS.items():
        v = [b for b in blobs[k] if valid(b)]
        if v:
            ghosts[name] = v[0]
    return pac, ghosts, tile


class Game:
    def __init__(self, name):
        self.name = name
        self.res = {"name": name, "notes": []}

    async def analyze(self, page, ref=False):
        try:
            return await page.evaluate("(r) => window.__analyze ? window.__analyze(r) : {err:'noanalyzer'}", ref)
        except Exception as e:
            return {"err": str(e)[:80]}

    async def click_button(self, page):
        try:
            b = await page.evaluate(FIND_BUTTON_JS, BUTTON_RE)
        except Exception:
            b = None
        if b:
            await page.mouse.click(b["x"], b["y"])
            return b["text"]
        return None

    async def canvas_click(self, page):
        try:
            box = await page.evaluate("""() => { const c=[...document.querySelectorAll('canvas')].sort((a,b)=>b.width*b.height-a.width*a.height)[0];
                if(!c) return null; const r=c.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}; }""")
            if box:
                await page.mouse.click(box["x"], box["y"])
        except Exception:
            pass

    async def pac_moves(self, page, secs=4.5):
        """Cycle held arrow keys; return True if Pac-Man travels > 1.5 tiles."""
        start = None; moved = 0
        t_end = time.time() + secs
        seq = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"]
        i = 0; last_sw = 0
        while time.time() < t_end:
            if time.time() - last_sw > 1.1:
                for k in seq:
                    await page.keyboard.up(k)
                await page.keyboard.down(seq[i % 4]); i += 1; last_sw = time.time()
            f = await self.analyze(page)
            pac, _, tile = pick(f)
            if pac:
                if start is None:
                    start = (pac["x"], pac["y"])
                moved = max(moved, math.hypot(pac["x"] - start[0], pac["y"] - start[1]))
                if moved > 1.5 * tile:
                    for k in seq:
                        await page.keyboard.up(k)
                    return True
            await asyncio.sleep(SAMPLE)
        for k in seq:
            await page.keyboard.up(k)
        return False

    async def try_start(self, page):
        actions = [("Enter", lambda: page.keyboard.press("Enter")),
                   ("button", lambda: self.click_button(page)),
                   ("Space", lambda: page.keyboard.press(" ")),
                   ("canvas-click", lambda: self.canvas_click(page)),
                   ("arrow-only", lambda: asyncio.sleep(0))]
        for label, act in actions:
            r = await act()
            if label == "button" and not r:
                continue
            await asyncio.sleep(0.3)
            if await self.pac_moves(page):
                return label + (f"({r})" if label == "button" and r else "")
        return None

    async def run(self, browser):
        name = self.name
        ctx = await browser.new_context(viewport={"width": 900, "height": 1000}, device_scale_factor=1)
        await ctx.add_init_script(INIT_JS)
        page = await ctx.new_page()
        perrs = []
        page.on("pageerror", lambda e: perrs.append(str(e)[:200]))
        page.on("console", lambda m: perrs.append("console: " + m.text[:200]) if m.type == "error" else None)
        try:
            await page.goto(BASE + name + ".html", wait_until="load", timeout=30000)
        except Exception as e:
            self.res["notes"].append(f"load error {e}")
        await asyncio.sleep(1.5)
        await page.screenshot(path=str(SHOTS / f"{name}_0title.jpg"), type="jpeg", quality=70)

        method = await self.try_start(page)
        self.res["start_method"] = method
        if not method:
            self.res["notes"].append("could not start / Pac never moved")
            await page.screenshot(path=str(SHOTS / f"{name}_1nostart.jpg"), type="jpeg", quality=70)
            await self.finish(page, perrs)
            await ctx.close()
            return self.res

        await self.analyze(page, ref=True)
        f0 = await self.analyze(page)
        _, _, tile = pick(f0)
        self.res["tile_px"] = round(tile, 1)
        frames0 = f0.get("frames", 0); t_start = time.time()

        cur = None; held = None
        attempts = []
        ctrl = {s: {d: [0, 0] for d in "UDLR"} for s in ("arrows", "wasd")}
        last_move_t = time.time(); last_pos = None; dirs_since_move = set()
        stuck_events = []; stuck_open = None
        static_events = []; static_trigger = False; stuck_cooldown = 0
        no_pac_since = None; restarts = 0; restart_fail = 0
        gstat = {g: {"seen": 0, "path": 0.0, "cells": set(), "anchor": None, "anchor_t": 0, "max_static": 0.0,
                     "onwall": 0, "first": None, "maxdisp": 0.0} for g in GHOSTS.values()}
        pac_stat = {"seen": 0, "onwall": 0, "cells": set(), "path": 0.0}
        all_ghosts_missing = 0; samples_play = 0
        shots_done = set()
        last_decide = 0; prev_pac = None
        while True:
            now = time.time(); el = now - t_start
            if el > PLAY_SECONDS:
                break
            scheme = "wasd" if (0.12 * PLAY_SECONDS < el < 0.32 * PLAY_SECONDS
                                or 0.7 * PLAY_SECONDS < el < 0.82 * PLAY_SECONDS) else "arrows"
            keys = WASD if scheme == "wasd" else ARROWS
            for mark, lab in ((5, "1early"), (PLAY_SECONDS * 0.5, "2mid"), (PLAY_SECONDS - 1, "3late")):
                if el > mark and lab not in shots_done:
                    shots_done.add(lab)
                    await page.screenshot(path=str(SHOTS / f"{name}_{lab}.jpg"), type="jpeg", quality=70)
            f = await self.analyze(page)
            pac, ghosts, _ = pick(f)
            samples_play += 1
            if pac:
                no_pac_since = None
                pac_stat["seen"] += 1
                pac_stat["onwall"] += 1 if pac["onWall"] else 0
                pac_stat["cells"].add((int(pac["x"] // tile), int(pac["y"] // tile)))
                p = (pac["x"], pac["y"])
                if prev_pac:
                    dd = math.hypot(p[0] - prev_pac[0], p[1] - prev_pac[1])
                    if dd < 3 * tile:
                        pac_stat["path"] += dd
                prev_pac = p
                if last_pos is None or math.hypot(p[0] - last_pos[0], p[1] - last_pos[1]) > 2.5:
                    if stuck_open:
                        stuck_events.append(round(now - stuck_open, 1)); stuck_open = None
                    last_pos = p; last_move_t = now; dirs_since_move = set()
                elif now - last_move_t > 4 and len(dirs_since_move) >= 3 and not stuck_open and now > stuck_cooldown:
                    static_trigger = True
            else:
                prev_pac = None
                if no_pac_since is None:
                    no_pac_since = now
            if pac and not ghosts and any(g["seen"] for g in gstat.values()):
                all_ghosts_missing += 1
            for g, st in gstat.items():
                b = ghosts.get(g)
                if not b:
                    st["anchor"] = None
                    continue
                st["seen"] += 1
                st["onwall"] += 1 if b["onWall"] else 0
                st["cells"].add((int(b["x"] // tile), int(b["y"] // tile)))
                if st["first"] is None:
                    st["first"] = (b["x"], b["y"])
                st["maxdisp"] = max(st["maxdisp"], math.hypot(b["x"] - st["first"][0], b["y"] - st["first"][1]) / tile)
                if st["anchor"] is None or math.hypot(b["x"] - st["anchor"][0], b["y"] - st["anchor"][1]) > 2.5:
                    if st["anchor"] is not None:
                        st["path"] += math.hypot(b["x"] - st["anchor"][0], b["y"] - st["anchor"][1])
                    st["anchor"] = (b["x"], b["y"]); st["anchor_t"] = now
                else:
                    st["max_static"] = max(st["max_static"], now - st["anchor_t"])
            for a in attempts:
                if a[5] is None and now - a[0] >= 0.8:
                    if pac and a[2]:
                        dx, dy = pac["x"] - a[2][0], pac["y"] - a[2][1]
                        vx, vy = VEC[a[1]]
                        if math.hypot(dx, dy) < 8 * tile:
                            ok = (dx * vx + dy * vy) > 0.5 * tile
                            ctrl[a[3]][a[1]][0] += 1
                            ctrl[a[3]][a[1]][1] += 1 if ok else 0
                            a[5] = ok
                        else:
                            a[5] = "skip"
                    else:
                        a[5] = "skip"
            if static_trigger:
                static_trigger = False
                ghosts_moving = [g for g, st in gstat.items() if st["anchor"] is not None and now - st["anchor_t"] < 3.5]
                shot = f"{name}_static{len(static_events)}.jpg"
                await page.screenshot(path=str(SHOTS / shot), type="jpeg", quality=70)
                if held:
                    await page.keyboard.up(held); held = None
                m = await self.try_start(page)
                static_events.append({"t": round(el, 1), "ghosts_moving": ghosts_moving, "recovered_by": m, "shot": shot})
                if m:
                    restarts += 1
                    last_move_t = time.time(); dirs_since_move = set(); last_pos = None
                else:
                    stuck_open = last_move_t
                    stuck_cooldown = time.time() + 15
                continue
            if no_pac_since and now - no_pac_since > 6:
                if held:
                    await page.keyboard.up(held); held = None
                m = await self.try_start(page)
                if m:
                    restarts += 1
                else:
                    restart_fail += 1
                no_pac_since = None
                last_move_t = time.time(); dirs_since_move = set(); last_pos = None
                continue
            if now - last_decide > 0.5 and pac:
                last_decide = now
                blocked = now - last_move_t > 0.45
                if cur is None or blocked:
                    nd = random.choice([d for d in "UDLR" if d != cur])
                elif random.random() < 0.3:
                    nd = random.choice(PERP[cur])
                else:
                    nd = None
                if nd:
                    if held:
                        await page.keyboard.up(held)
                    held = keys[nd]
                    await page.keyboard.down(held)
                    cur = nd
                    dirs_since_move.add(nd)
                    attempts.append([now, nd, (pac["x"], pac["y"]), scheme, None, None])
            await asyncio.sleep(SAMPLE)
        if held:
            await page.keyboard.up(held)
        if stuck_open:
            stuck_events.append(round(time.time() - stuck_open, 1))
        fN = await self.analyze(page)
        dur = time.time() - t_start
        r = self.res
        r["fps"] = round((fN.get("frames", 0) - frames0) / dur, 1) if dur else 0
        r["samples"] = samples_play
        r["pac_visible_frac"] = round(pac_stat["seen"] / max(1, samples_play), 2)
        r["pac_cells_visited"] = len(pac_stat["cells"])
        r["pac_path_tiles"] = round(pac_stat["path"] / tile, 1)
        r["pac_onwall_frac"] = round(pac_stat["onwall"] / max(1, pac_stat["seen"]), 3)
        r["stuck_events_s"] = stuck_events
        r["static_events"] = static_events
        r["restarts"] = restarts; r["restart_fail"] = restart_fail
        r["controls"] = {s: {d: f"{v[1]}/{v[0]}" for d, v in dd.items()} for s, dd in ctrl.items()}
        r["ghosts"] = {g: {"seen_frac": round(st["seen"] / max(1, samples_play), 2),
                           "cells": len(st["cells"]), "path_tiles": round(st["path"] / tile, 1),
                           "max_static_s": round(st["max_static"], 1), "maxdisp_tiles": round(st["maxdisp"], 1),
                           "onwall_frac": round(st["onwall"] / max(1, st["seen"]), 3)} for g, st in gstat.items()}
        r["all_ghost_colours_missing_samples"] = all_ghosts_missing
        await self.finish(page, perrs)
        await ctx.close()
        return r

    async def finish(self, page, perrs):
        try:
            a = await page.evaluate("() => window.__audit")
        except Exception:
            a = {}
        a = a or {}
        self.res["audio"] = {k: a.get(k) for k in ("ctx", "oscStarts", "bufStarts", "runningStarts", "states", "resumes", "mediaPlays")}
        self.res["max_scroll"] = a.get("maxScroll")
        self.res["errors"] = list(dict.fromkeys((a.get("errors") or []) + perrs))[:8]
        (OUT / f"{self.name}.json").write_text(json.dumps(self.res, indent=1, default=str))


async def main(names):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--disable-background-timer-throttling",
                                                                 "--disable-renderer-backgrounding",
                                                                 "--disable-backgrounding-occluded-windows"])
        sem = asyncio.Semaphore(CONCURRENCY)

        async def one(n):
            async with sem:
                t = time.time()
                try:
                    r = await Game(n).run(browser)
                    print(f"DONE {n} {time.time()-t:.0f}s start={r.get('start_method')} fps={r.get('fps')}", flush=True)
                except Exception as e:
                    print(f"FAIL {n}: {e}", flush=True)
        await asyncio.gather(*(one(n) for n in names))
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main(ARGS.names.split(",")))
