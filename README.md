# Pac-Man bake-off

Models and harnesses recreate Pac-Man from one short prompt. Compare entries by model, harness, cost, time, tokens, and HTML size.

**Live site:** [https://jonclegg.github.io/pacman-bakeoff/](https://jonclegg.github.io/pacman-bakeoff/)

Each card opens a playable HTML entry. Stats come from harness transcripts where available (wall time, tokens, cost estimates). A dash means that run did not record the number.

`claude-opus-5-5-r2` is a second Opus 5.5 run. It was requested as claude-opus-4-6; the model that ran was claude-opus-5-5. There is no Opus 4.6 entry. The other `claude-opus-5-5` card is a separate run.

`gpt-6-astra`, `gpt-6-sol`, and `gpt-6-luna` are Codex reruns with API-key auth, not the earlier ChatGPT Plus sessions. `cost_usd` is OpenAI's published Standard rate card applied to each response's captured usage.

`gpt-5.6-sol` and `muse-spark-1.3` are fresh blind Cursor Cloud reruns. Their card titles are the spawn slugs `gpt-5.6-sol-high` and `muse-spark-1.3-high`. The Ultra usage export has no events for those agent ids, so tokens and cost stay blank.

`muse-spark-1.3-openrouter` is a separate OpenRouter Claude Code run of `meta/muse-spark-1.3`. It is not the Cursor Cloud card.

`claude-sonnet-5-5` is an OpenRouter Claude Code run. Requested `anthropic/claude-sonnet-5.5`; OpenRouter served `anthropic/claude-sonnet-5.5-20260928`. It is not the first-party `claude-sonnet-5` card.

## Repo layout

- `index.html`, `arcade.css`, `arcade.js` — gallery UI
- `entries/` — one HTML file per run plus `meta.json`
- `.nojekyll` — serve static assets as-is on GitHub Pages
