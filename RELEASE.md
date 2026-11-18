# Release log

Newest first. Each entry: date, PR, what changed for gallery visitors, what an operator must do and what it cost.

## 2026-11-18: add gemini-4-neon (8) (PR TBD)

- **What changed:** new card gemini-4-neon (Gemini 4 Neon, released 2026-11-18), scored 8 on v4 (52nd of 56, level with deepseek-v4-pro). Scoring docs updated; ranks below move down.
- **Operator:** nothing.
- **Cost:** fair cell $3.631 at OpenRouter listed Google Gemini 4 Neon rates (generation total; key usage moved $3.832 including smoke/canary). Scoring used playtest + source audit only (blank canvas; no visual judges).

## 2026-11-18: add tencent-hy4-flash (76) (PR #64)

- **What changed:** a new card, `tencent-hy4-flash` (Tencent Hy4 Flash, released 2026-11-16), scored 76 on v4 (25th of 55). Scoring docs v2/v3/v4 gain its rows and a findings row; ranks below it move down one.
- **Operator:** nothing to do. The card is static (`entries/tencent-hy4-flash.html` plus its `entries/meta.json` record).
- **Cost:** the fair cell cost $0.015 at OpenRouter's listed Tencent rates (generation total; key usage moved $0.025 including smoke/canary). Scoring (audit, playtest, two blind visual judges, bonus probe) used the same OpenRouter key through Claude Code / Cursor agents (anthropic/claude-opus-5.5 class).

## 2026-11-17: DETAILS on the play screen (PR #63)

- **What changed:** while playing a game, a yellow ⓘ DETAILS button in the top bar (or a click on the TIME / COST / SCORE stats) opens a modal with the score breakdown, all run data and the run notes. The run notes were not shown anywhere before. RELEASED moves from the play bar into the modal so the model name keeps room. Esc, ✕ or a click outside closes the modal and leaves the game open.
- **Operator:** nothing to do. Static change to `index.html`, `arcade.js`, `arcade.css`.
- **Cost:** none.
## 2026-11-17: agent notes for new models (PR #62)

- **What changed:** nothing on the site. New `AGENTS.md` tells any agent (including the Grok bot) what to do when it spots a new model: check `entries/meta.json`, ask Jon, then follow the add-model playbook to `/dev/`. It also lists where production is published. The add-model playbook now checks wooten-labs.com after a merge.
- **Operator:** nothing to do.
- **Cost:** none.

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
