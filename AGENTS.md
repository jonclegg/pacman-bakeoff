# Agent notes for PacBench

Read this first if you are an agent (Claude Code, Grok bot, Codex or any other) working in this repo.

PacBench is the Pac-Man bake-off: models and harnesses build Pac-Man from one fixed prompt, and the gallery scores and compares the results. `README.md` explains the site and the tools.

## When you spot a new model

1. Check `entries/meta.json`. If the model's slug is already there, it is a rerun or a re-score, not a new model.
2. Tell Jon what you found: the model name, its API id, the release date and a link. Wait for his yes before running anything, because every run costs money.
3. On his yes, follow `.claude/skills/add-model/SKILL.md` step by step. It is plain Markdown, so any agent can follow it. It covers the fair-cell run, publishing the entry, the `/dev/` preview, scoring and the hand-back. Its harness table says which runner each vendor uses (xAI models use `grok-build`).
4. The new card goes to the `/dev/` preview only. Never push to `main` and never merge a PR without Jon's yes.

## Where the site lives

Merging to `main` publishes the gallery in two places automatically. No manual upload is needed.

| Site | Published by | Typical wait |
|---|---|---|
| https://wooten-labs.com/pacman-bench/ (the main public site) | `.github/workflows/wooten-labs.yml`: runs the tests, then uploads to S3 and clears the CloudFront cache | about 3 minutes |
| https://jonclegg.github.io/pacman-bakeoff/ | `.github/workflows/pages.yml` | about 2 minutes |
| https://jonclegg.github.io/pacman-bakeoff/dev/ (preview) | `.github/workflows/pages.yml`, from the `dev` branch | about 2 minutes |

After a merge, confirm the new slug is live on both production sites:

```bash
curl -s https://wooten-labs.com/pacman-bench/entries/meta.json | grep -c '"<slug>"'
curl -s https://jonclegg.github.io/pacman-bakeoff/entries/meta.json | grep -c '"<slug>"'
```

If the wooten-labs.com copy is behind, look at the latest "Deploy wooten-labs.com" run:

```bash
gh run list --workflow wooten-labs.yml --limit 3
```

Do not upload to the bucket by hand unless Jon asks.

The `wooten-labs` repo (`~/dev/wooten-labs`) also copies the gallery from `origin/main` whenever that site is redeployed, so both paths publish the same files.

## Rules

- Work on a branch in `.claude/worktrees/<name>`, not on `main`.
- Each change gets an entry in `RELEASE.md` in the same PR: the date, the PR, what changed for visitors, what an operator must do, and what it cost.
