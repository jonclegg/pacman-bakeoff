# Pac-Man bake-off

Models and harnesses recreate Pac-Man from one short prompt. Compare entries by model, harness, cost, time, tokens, and HTML size.

**Live site:** [https://jonclegg.github.io/pacman-bakeoff/](https://jonclegg.github.io/pacman-bakeoff/)

Each card opens a playable HTML entry. Stats come from harness transcripts where available (wall time, tokens, cost estimates). A dash means that run did not record the number.

Cost is filled only when the harness recorded a dollar estimate, or when all billable token buckets and published rates are known. For the Antigravity Gemini entries, the estimate is:

```
cost_usd = (input_tokens / 1_000_000 * 0.75) + ((output_tokens + thinking_tokens) / 1_000_000 * 3.75)
```

Those are the published Gemini 3.7/3.8 Flash introductory rates in USD per 1M tokens, with thinking tokens billed as output tokens.

## Repo layout

- `index.html`, `arcade.css`, `arcade.js` — gallery UI
- `entries/` — one HTML file per run plus `meta.json`
- `.nojekyll` — serve static assets as-is on GitHub Pages
