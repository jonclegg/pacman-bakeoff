# Pac-Man bake-off

Models and harnesses recreate Pac-Man from one short prompt. Compare entries by model, harness, cost, time, tokens, and HTML size.

**Live site:** [https://jonclegg.github.io/pacman-bakeoff/](https://jonclegg.github.io/pacman-bakeoff/)

Each card opens a playable HTML entry. Stats come from harness transcripts where available (wall time, tokens, cost estimates). A dash means that run did not record the number.

## Repo layout

- `index.html`, `arcade.css`, `arcade.js` — gallery UI
- `entries/` — one HTML file per run plus `meta.json`
- `.nojekyll` — serve static assets as-is on GitHub Pages
