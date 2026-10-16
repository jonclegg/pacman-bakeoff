# Pac-Man bake-off

Models and harnesses recreate Pac-Man from one short prompt. Compare entries by model, harness, cost, time, tokens, and HTML size.

**Live site:** [https://jonclegg.github.io/pacman-bakeoff/](https://jonclegg.github.io/pacman-bakeoff/)

**Dev preview:** the live site URL plus `dev/` (serves the `dev` branch)

Each card opens a playable HTML entry. The gallery has one card per model and effort; when a model was run at more than one effort, each of its cards names its effort under the title. Stats come from harness transcripts where available (wall time, tokens, cost estimates). A dash means that run did not record the number.

Scores (out of 100) come from Opus 5.5's 2026-09-28 re-test of the live games on this site: a 90 s automated play test plus a source and maze audit. The rubric is Controls 20, Ghosts 25, Pac-Man stuck 20, Maze 20, Sound 15. Since 2026-10-13 the v3 rule (`bench/scoring/v3.md`) adds 2 points back for each minor Controls or Sound mark on cards with no major mark. The v4 rule (`bench/scoring/v4.md`) then, on the same cards, deducts up to 22 points for visual differences from the 1980 arcade game (maze, ghosts, Pac-Man, dots, HUD; judged blind from screenshots) and adds up to 8 for verified arcade extras (bonus fruit, attract screen, pixel-art rendering, level-clear flash, intermission), capped at 100. Each entry's `score` and per-check `score_notes` live in `entries/meta.json`. The gallery sorts by score, highest first (or by cost, time, tokens or model release date), and shows the per-check notes under a card's details.

`gpt-6-astra`, `gpt-6-sol`, and `gpt-6-luna` are Codex reruns with API-key auth, not the earlier ChatGPT Plus sessions. `cost_usd` is OpenAI's published Standard rate card applied to each response's captured usage.

`gpt-5.6-sol` and `muse-spark-1.3` are fresh blind Cursor Cloud reruns. Card titles drop the effort suffix; the requested spawn slugs `gpt-5.6-sol-high` and `muse-spark-1.3-high` stay under Run data. A 2026-09-28 rescan of the Ultra usage export still has no events for those agent ids, and the cell transcripts have no token counts, so tokens and cost stay blank. Nearby charges on the orchestrator that spawned them were not copied.

`claude-sonnet-5-5` is an OpenRouter Claude Code run. The card title is `claude-sonnet-5.5`. Requested `anthropic/claude-sonnet-5.5`; OpenRouter served `anthropic/claude-sonnet-5.5-20260928`, which stays under Run data. It is not the first-party `claude-sonnet-5` card.

## Dev preview

`.github/workflows/pages.yml` deploys GitHub Pages on every push to `main` or `dev`. Each deploy publishes `main` at the site root and `dev` under `/dev/`, so the preview never replaces production.

To preview a branch, push it to `dev` and wait for the "Deploy Pages" run to finish:

```sh
git push --force origin my-branch:dev
```

Check the gallery at `/dev/`, then merge the branch to `main` as usual. To reset the preview to production, run `git push --force origin main:dev`.

One-time setup (repo admin):

1. Create the branch: `git push origin main:dev`.
2. Settings → Environments → `github-pages` → Deployment branches: add `dev`.
3. Settings → Pages → Source: **GitHub Actions**.
4. Actions → "Deploy Pages" → Run workflow on `main`.

## Adding a model

In Claude Code, point at the model (name, API id, or announcement link) and ask to add it. The project skill `.claude/skills/add-model/SKILL.md` runs the whole loop: fair-cell run, entry, dev deploy, v2 scoring, analysis, then asks before promoting to `main`.

The pieces, if you run them by hand:

- `bench/run_cell.py` runs one harness and model in a fresh sandboxed cell with `bench/prompts/pacman.md` and writes `~/.pacbake/runs/<run_name>/`.
- `bench/or_proxy.py` pins OpenRouter requests to the vendor's own provider (run with `PACBAKE_OR_BASE_URL`).
- `bench/add_entry.py` reads that run's transcript for time, tokens and cost, copies the HTML to `entries/`, and upserts `entries/meta.json`.
- `bench/playtest/run.py` is the 90 s automated play test. `bench/scoring/audit.md` is the source and maze audit brief. `bench/scoring/v2.md` is the rubric and calibration table. `bench/scoring/v3.md` is the minor Controls/Sound adjustment applied on top of it, and `bench/scoring/v4.md` is the visual-accuracy and arcade-extras layer on top of that. `bench/playtest/screenshots.py` takes the screenshots for the v4 visual check.

## Repo layout

- `index.html`, `arcade.css`, `arcade.js` — gallery UI
- `entries/` — one HTML file per run plus `meta.json`
- `.nojekyll` — serve static assets as-is on GitHub Pages
- `.github/workflows/pages.yml` — deploys `main` to the site root and `dev` to `/dev/`
- `bench/` — runner, entry publisher, play test and scoring docs (not used by the gallery)
- `.claude/skills/add-model/` — the add-a-model playbook
