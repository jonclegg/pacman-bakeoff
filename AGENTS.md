# Agent notes for PacBench

Read this first if you are an agent (Claude Code, Grok bot, Codex or any other) working in this repo.

PacBench is the Pac-Man bake-off: models and harnesses build Pac-Man from one fixed prompt, and the gallery scores and compares the results. `README.md` explains the site and the tools.

## When you spot a new model

1. Work out the slug: the vendor's short name in lower case with dots kept (`kimi-k3`, `gpt-6.2-sol`; Anthropic ids keep dashes, as in `claude-opus-5-5`). Check the live list, not a local checkout that may be stale: `curl -s https://wooten-labs.com/pacman-bench/entries/meta.json | grep -c '"slug": "<slug>"'`. A result of 1 means the model is already on the site, so this is a rerun or a re-score, not a new model.
2. Tell Jon what you found, through whatever channel you normally use to reach him: the model name, its API id, the release date, a link and the estimated cost (recent runs cost $1–5). Wait for his yes before running anything, because every run costs money. His yes covers the cost check in step 1.6 of the playbook unless the estimate turns out to be over $25.
3. On his yes, follow `.claude/skills/add-model/SKILL.md` step by step. It covers the fair-cell run, publishing the entry, the `/dev/` preview, scoring and the hand-back. Its harness table says which runner each vendor uses (xAI models use `grok-build`).
   - The playbook was written for Claude Code on Jon's Mac. Runs need that machine: API keys live in `~/.pacbake/secrets/` and AWS SSM (profile `jclegg`), and the runs land in `~/.pacbake/runs/`. If you are not on that Mac, stop after step 2 and hand the work to Jon.
   - Where the playbook says "browser pane", use any real browser you can drive (headless Chromium or Playwright works). Where it says to "give an agent" a brief or to use "blind judges", run a separate fresh model call per reviewer, so no reviewer sees your conclusions. `<scratchpad>` means any temporary directory.
4. The new card goes to the `/dev/` preview only. Never push to `main` and never merge a PR without Jon's yes.

## Where the site lives

Merging to `main` publishes the gallery in two places automatically. No manual upload is needed.

| Site | Published by | Typical wait |
|---|---|---|
| https://wooten-labs.com/pacman-bench/ (the main public site) | `.github/workflows/wooten-labs.yml`: runs the tests, then uploads to S3 and clears the CloudFront cache | about 6 minutes (tests take most of it) |
| https://jonclegg.github.io/pacman-bakeoff/ | `.github/workflows/pages.yml` | about 3 minutes |
| https://jonclegg.github.io/pacman-bakeoff/dev/ (preview) | `.github/workflows/pages.yml`, from the `dev` branch | about 3 minutes |

After a merge, confirm the new slug is live on both production sites:

```bash
curl -s https://wooten-labs.com/pacman-bench/entries/meta.json | grep -c '"slug": "<slug>"'
curl -s https://jonclegg.github.io/pacman-bakeoff/entries/meta.json | grep -c '"slug": "<slug>"'
```

Each should print 1.

If the wooten-labs.com copy is behind, look at the latest "Deploy wooten-labs.com" run:

```bash
gh run list --workflow wooten-labs.yml --limit 3
```

Do not upload to the bucket by hand unless Jon asks.

The `wooten-labs` repo (`~/dev/wooten-labs`) also copies the gallery from `origin/main` whenever that site is redeployed, so both paths publish the same files.

## Rules

- Work on a branch in `.claude/worktrees/<name>`, not on `main`.
- Each change gets an entry in `RELEASE.md` in the same PR: the date, the PR, what changed for visitors, what an operator must do, and what it cost.
