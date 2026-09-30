---
name: add-model
description: Add a new model to the PacBench Pac-Man bake-off end to end — run it in a fair cell, publish the entry, deploy to the dev preview, score it with the v2 method, and write the analysis. Use when the user points at a model (name, API id, announcement or OpenRouter URL) and wants it on the site, or asks to rerun or re-score an entry.
---

# Add a model to the bake-off

The user gives you a model (name, id, or link). You ship a scored card to `/dev/`, then ask to promote it to production. Never push to `main` without the user's yes.

Paths: runner and tools in `bench/`, runs land in `~/.pacbake/runs/<run_name>/`, site data in `entries/`.

## 1. Identify the model

1. Read the link or the vendor's model page. Record: vendor, exact API id, release date, and the published rates per 1M tokens (input, cached input, cache write, output). Cite the page and the date you read it.
2. Check `entries/meta.json`. If the slug exists, this is a rerun or re-score; say which.
3. Check the id is served: `curl -s https://openrouter.ai/api/v1/models` for OpenRouter ids, or the vendor's own model list.
4. Pick the harness. Default to the vendor's own agent CLI; everything else goes through Claude Code on OpenRouter.

| Vendor | `run_cell.py` harness | `add_entry.py --harness` |
|---|---|---|
| Anthropic | `claude-code` (first party). If the org catalog remaps the id, use `claude-code-openrouter` and say so in the note | same |
| OpenAI | `codex-apikey` (key from SSM `/somewhere/openai-api-key`, profile `jclegg`, us-east-1), so cost is the published rate card applied to real usage. Run the canary once before its first real run | `codex` |
| xAI | `grok-build` | `grok-build` |
| Google | Antigravity (`agy`) has no sandboxed lane in `run_cell.py` yet. Ask the user before running it | `antigravity` |
| Open weights and everyone else | `claude-code-openrouter` with the OpenRouter slug | `claude-code-openrouter` |

5. Slug: the vendor's short name, lower case, dots kept (`kimi-k3`, `gpt-6.1-sol`, `claude-opus-5-5` for Anthropic ids). `display_model` is the card title.
6. Tell the user, in one message: model id, harness, and an estimated cost (recent runs used about 5M cached input and 100–160k output tokens). Go ahead unless the estimate is over $25 or the harness has never run the canary, then wait for a yes.

## 2. Work in a worktree

```bash
git fetch origin
git worktree add -b add-<slug> .claude/worktrees/add-<slug> origin/main
```

## 3. Run the cell

```bash
python3 bench/run_cell.py <harness> <model-id> <harness>__<model-id with / as -->
```

- The prompt is `bench/prompts/pacman.md` (sha256 `55c6d2ec…`), the fair-cell spec used by claude-fable-5, gpt-5.6-sol and gpt-6.1-sol. Older cards used the one-line prompt `build a Pac-Man game in a single html page`. Record which prompt ran in the entry note.
- It runs up to an hour. Run it in the background and post a progress line every five minutes: elapsed time, transcript event count, and whether `pacman.html` exists in the cell yet.
- A new harness runs `--prompt bench/prompts/canary.md` first. All four canary probes (sibling dir, real home, `~/dev`, web fetch) must fail before the real run.

When it ends, check `meta.json` (`status: done`, `exit_code: 0`, `pacman_html.exists`) and `git_status.txt` (only `pacman.html` plus the model's own test files). Grep the transcript for web tools or paths outside the cell. A run that peeked is void; say so and stop.

## 4. Publish the entry

```bash
python3 bench/add_entry.py ~/.pacbake/runs/<run_name> --slug <slug> --harness <harness> \
  --display-model <title> --requested <model-id> [--rates IN,CACHED,CACHE_WRITE,OUT] --note "<note>"
```

- `--rates` is required for Codex and Antigravity, whose transcripts carry no cost. Claude Code and Grok Build report their own cost.
- The note says: harness and auth, run date, which prompt, the pricing source and date, and anything odd (model remaps, orphaned runs, fallback metadata). Match the tone of existing notes.
- Check the printed entry: cost and duration non-null, `actual` equals the served model.

## 5. Deploy to dev

Commit, then publish the branch at `/dev/` (this replaces whatever is on dev; `main` is untouched):

```bash
git push --force origin HEAD:dev
gh run watch "$(gh run list --workflow pages.yml --branch dev --limit 1 --json databaseId -q '.[0].databaseId')" --exit-status
```

Confirm with `curl -s https://jonclegg.github.io/pacman-bakeoff/dev/entries/meta.json` that the slug is there, and open `https://jonclegg.github.io/pacman-bakeoff/dev/` in the browser pane to see the card render and the game load.

## 6. Score it (v2 method)

Read `bench/scoring/v2.md` first: the rubric, the method, and the calibration table. A new score has to sit sensibly among those rows.

1. **Live play test** against the dev copy, plus two calibration anchors so a broken harness shows up:
   ```bash
   python3 bench/playtest/run.py <slug>,claude-opus-5-5,gpt-6.1-sol --out <scratchpad>/playtest \
     --base https://jonclegg.github.io/pacman-bakeoff/dev/entries/
   ```
   The anchors should reproduce their v2 behaviour (starts, no stuck events, audio running). If they don't, fix the harness before trusting the new entry.
2. **Source and maze audit.** Give a general-purpose agent `bench/scoring/audit.md` and `entries/<slug>.html`. For a close call near the top of the table, run two blind reviewers and reconcile.
3. **Check every anomaly yourself** in the browser pane: stuck events, frozen ghosts, silent audio, console errors, and the audio code for quality (the harness can't hear).
4. **Assign points.** Controls 20, Ghosts 25, Pac-Man stuck 20, Maze 20, Sound 15. Cap low when the ghosts don't work or Pac-Man can't move. Write `score`, `score_notes` (`controls`, `ghosts`, `stuck`, `maze`, `sound`; each `{mark: ok|minor|major|na, note}`) and, only for a one-line cause like a blank canvas, `score_summary` in `entries/meta.json`.
5. **Record the analysis.** Add the entry's row to the results table in `bench/scoring/v2.md` in rank order, marked *(added YYYY-MM-DD)*, and a short paragraph under "Later additions" if it changes a takeaway.

Commit and push to dev again (step 5). Check the card shows the score and the "How scored?" notes.

## 7. Hand back

Tell the user: the dev link, score and rank, cost and time against the neighbours, the two or three findings that drove the score, and anything you doubted. Then ask: "Ready to promote this to production?" On yes, open a PR from `add-<slug>` to `main`, merge it after the user approves, and remove the worktree.
