# Release log

Newest first. Each entry: date, PR, what changed for gallery visitors, what an operator must do and what it cost.

## 2026-11-17: deploy main to wooten-labs.com/pacman-bench/ (PR #61)

- **What changed:** every merge to `main` now also updates [wooten-labs.com/pacman-bench/](https://wooten-labs.com/pacman-bench/), so it no longer falls behind GitHub Pages. Visitors see the same gallery on both.
- **Operator:** nothing to do after merge. One-time setup is done: IAM role `GitHubActions-PacmanBench` in AWS account 423173602168 (trusts only `repo:jonclegg@5744185/pacman-bakeoff@1391736701:ref:refs/heads/main`, the repo's ID-based token subject; may write under `pacman-bench/` in `wooten-labs-site-423173602168` and invalidate CloudFront `E3NNL0QRWXIH24`). No GitHub secrets.
- **Cost:** about 2 MB of S3 PUTs and one CloudFront invalidation path per deploy: well under a cent each (the first 1,000 invalidation paths a month are free).

## 2026-11-17: add gpt-6.2-astra (92) and gpt-6.2-sol (87) (PR #60)

- **What changed:** two new cards, `gpt-6.2-astra` (GPT-6.2 Astra, 92 on v4, 9th of 54) and `gpt-6.2-sol` (GPT-6.2 Sol, 87, 13th of 54, level with muse-wonder), both released 2026-11-17. Scoring docs v2/v3/v4 gain their rows, a v2 paragraph each and a v4 Later additions bullet each; ranks below them move down.
- **Operator:** nothing to do. The cards are static (`entries/gpt-6.2-astra.html`, `entries/gpt-6.2-sol.html` plus their `entries/meta.json` records).
- **Cost:** the two Codex API-key fair cells cost $2.04 (Astra) and $0.49 (Sol) at OpenAI Standard rates on the OpenAI key. Scoring (four blind audits, two bonus probes, two blind visual judges) cost about $10.94 on the OpenRouter key through Claude Code (anthropic/claude-opus-5.5).

## 2026-11-15: add qwen4-max (75)

- **What changed:** a new card, `qwen4-max` (Qwen4-Max, released 2026-11-15), scored 75 on v4 (23rd of 52). Scoring docs v2/v3/v4 gain its rows; ranks below it move down one.
- **Operator:** nothing to do. The card is static (`entries/qwen4-max.html` plus its `entries/meta.json` record).
- **Cost:** the fair cell cost $4.32 in OpenRouter usage (Alibaba-served `qwen/qwen4-max`). Audits, blind judges and the bonus probe ran on the same OpenRouter key through Claude Code (anthropic/claude-opus-5.5).
