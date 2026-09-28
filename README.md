# Pac-Man bake-off

Models and harnesses recreate Pac-Man from one short prompt. Compare entries by model, harness, cost, time, tokens, and HTML size.

**Live site:** [https://jonclegg.github.io/pacman-bakeoff/](https://jonclegg.github.io/pacman-bakeoff/)

Each card opens a playable HTML entry. Stats come from harness transcripts where available (wall time, tokens, cost estimates). A dash means that run did not record the number.

`claude-opus-5-5-r2` is a second Opus 5.5 run. It was requested as claude-opus-4-6; the model that ran was claude-opus-5-5. There is no Opus 4.6 entry. The other `claude-opus-5-5` card is a separate run.

## Repo layout

- `index.html`, `arcade.css`, `arcade.js` — gallery UI
- `entries/` — one HTML file per run plus `meta.json`
- `.nojekyll` — serve static assets as-is on GitHub Pages
