# Pac-Man bake-off

Models and harnesses recreate Pac-Man from one short prompt. Compare entries by model, harness, cost, time, tokens, and HTML size.

**Live site:** [https://jonclegg.github.io/pacman-bakeoff/](https://jonclegg.github.io/pacman-bakeoff/)

Each card opens a playable HTML entry. The gallery has one card per model. Stats come from harness transcripts where available (wall time, tokens, cost estimates). A dash means that run did not record the number.

`gpt-6-astra`, `gpt-6-sol`, and `gpt-6-luna` are Codex reruns with API-key auth, not the earlier ChatGPT Plus sessions. `cost_usd` is OpenAI's published Standard rate card applied to each response's captured usage.

`gpt-5.6-sol` and `muse-spark-1.3` are fresh blind Cursor Cloud reruns. Their card titles are the spawn slugs `gpt-5.6-sol-high` and `muse-spark-1.3-high`. A 2026-09-28 rescan of the Ultra usage export still has no events for those agent ids, and the cell transcripts have no token counts, so tokens and cost stay blank. Nearby charges on the orchestrator that spawned them were not copied.

`claude-sonnet-5-5` is an OpenRouter Claude Code run. Requested `anthropic/claude-sonnet-5.5`; OpenRouter served `anthropic/claude-sonnet-5.5-20260928`. It is not the first-party `claude-sonnet-5` card.

## Repo layout

- `index.html`, `arcade.css`, `arcade.js` — gallery UI
- `entries/` — one HTML file per run plus `meta.json`
- `.nojekyll` — serve static assets as-is on GitHub Pages
