# Source and maze audit (v2 method)

Hand this file and one entry's HTML to a reviewer agent. It is the second half of the v2 re-test; the first half is `bench/playtest/run.py`. `bench/scoring/v2.md` has the rubric and the calibration table every new score must fit.

Work in a scratch directory. Do not edit the entry. Report numbers, not impressions.

## 1. Load the game headless

Run the entry's script in Node (`vm` with stub `document`, `canvas` 2D context, `requestAnimationFrame`, `performance.now`, `AudioContext`, `localStorage`, key events). Drive frames yourself so you control time. If the script throws on load, record the error and the frame it happens on; that is a critical finding.

## 2. Maze

Pull the runtime grid (after any init code runs), not the source literal. Using the game's own passability function (`walkable()`, `isWall()`, or equivalent) with its tunnel-wrap and ghost-door rules:

- BFS from Pac-Man's spawn tile. Report reachable pellets / total pellets and power pellets.
- Dead ends: walkable tiles with exactly one walkable neighbour (the tunnel ends count as connected if they wrap).
- Spawn validity: Pac-Man and each ghost start on a walkable tile.
- Ghost house: has a door ghosts can leave by; Pac-Man cannot enter it.
- Off-grid leaks: any way to leave the grid other than the tunnel.
- Symmetry (left/right) and dimensions (classic is 28×31, 240 dots + 4 energizers = 244).

## 3. Freeze test

Step the real game loop at 30, 60, 120, 144, 165 and 240 fps for 60 simulated seconds each, holding a direction scheme that changes every 0.5 s. Record per-fps: does each ghost keep moving, does Pac-Man keep moving, does any entity sit still longer than 3 s outside the house or frightened pauses. The common bug is "if within `speed` of the tile centre, snap to centre", which can land back in the window every frame. Also note if speed is in pixels per frame (2× speed at 120 Hz).

## 4. Code review

- **Controls:** arrows and WASD, `preventDefault` on arrows/Space (no page scroll), input buffering / cornering, instant reverse, start, pause, restart, mute, touch or swipe.
- **Ghosts:** four distinct targeting rules (Blinky direct, Pinky 4 ahead incl. the up-quirk, Inky vector, Clyde 8-tile retreat), scatter/chase waves, house release (dot counters or timers), frightened mode (flee, blink, eatable, score chain), eaten eyes return to the house and revive, no re-eat within the same power-up, Cruise Elroy, tunnel slowdown.
- **Sound:** which events make sound (intro, waka, siren, power, eat ghost, death, extra life, fruit), whether the siren is continuous, mute, AudioContext created or resumed inside a user gesture (Safari), master gain.
- **Other:** level progression, lives, game over, high score, fruit, console errors.

## 5. Report

Return, per rubric check (Controls 20, Ghosts 25, Pac-Man stuck 20, Maze 20, Sound 15): a mark (`ok`, `minor`, `major`) and a short note in the house style of `entries/meta.json` `score_notes` (for example `"classic 28×31, 0 dead ends, 0/244 unreachable"`). List every critical bug with the evidence (line, fps, tile). Do not assign the final score; the orchestrator does that against the calibration table.
