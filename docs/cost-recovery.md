# Plan: recover bake-off tokens and cost

Planning only. Do not write `cost_usd` into `entries/meta.json` from this note. The dollar figures in the Codex section are a worked example from `codex-final-usage.json`, labeled as estimates, and they are not a backfill.

The gallery is not the bug. `arcade.js` prints `—` when a field is null (`show`), sorts null costs as missing, and the strip shows `TOTAL` only when `output_tokens` is null and `tokens_total` is set. Working harnesses (Grok Build, Claude Code, OpenRouter / Claude Code) already copy a harness-reported `cost_usd`. This repo has no runner; harvest lives on the Mac under `/Users/Shared/pacbake`.

## What is blank

| Group | Entries | Tokens today | Cost today |
| --- | --- | --- | --- |
| Codex | gpt-6-astra, gpt-6-sol, gpt-6-luna | `tokens_total` only (the CLI footer) | null |
| Cursor Cloud | cursor-auto, gpt-5.6-terra, gpt-5.6-sol, gpt-5.6-luna, muse-spark-1.3 | null | null |
| Antigravity | gemini-3.7-flash, gemini-3.8-flash | input, output, thinking filled | null. Draft PR #1 is an optional public-rate estimate |
| Grok Bot | grok-bot | null | null |

## Rank

1. **First — Codex tokens.** Rollouts on disk already have the split. Replace the footer number. Gate dollars on one usage-dashboard check (below).
2. **First, optional — Antigravity dollars.** Tokens are already on the card. Apply the public Gemini formula only after the full transcript’s `cache_read_tokens` sum is known. Leave draft PR #1 unmerged until that check.
3. **Later — Cursor Cloud.** Tokens are recoverable from the Cloud Agents usage API once each `bc-` id is found. Dollars only from Cursor’s own `chargedCents` / `getUsage().cost`. No OpenAI list price.
4. **Can’t — this Grok Bot entry.** In-chat, no meter. Leave `—`.

## Codex

### Where the numbers are

`run.sh` runs `codex exec` with `CODEX_HOME=~/.pacbake/homes/codex-chatgpt` and writes stdout to `transcript.jsonl` and stderr to `stderr.log`. The stderr footer is one line, `tokens used`, then a count. That count was copied to run `meta.json` as `tokens_used_approx` and then to the site as `tokens_total`.

The split is not in that footer. It is on the last `payload.thread_token_usage` and `payload.info.total_token_usage` in the rollout. Those two objects match in the extracted finals. Fields: `input_tokens`, `cached_input_tokens`, `cache_write_input_tokens`, `output_tokens`, `reasoning_output_tokens`, `total_tokens`.

| Model | Session | Rollout file under `~/.pacbake/homes/codex-chatgpt/sessions/2026/09/27/` |
| --- | --- | --- |
| gpt-6-astra | `01a0e494-6da7-7763-93bd-d88e36603481` (run meta) | `rollout-2026-09-27T15-35-27-01a0e494-6da7-7763-93bd-d88e36603481.jsonl` |
| gpt-6-sol | `01a0e49c-d737-7d20-b4b8-a9379f14d8ff` (run meta) | `rollout-2026-09-27T15-44-39-01a0e49c-d737-7d20-b4b8-a9379f14d8ff.jsonl` |
| gpt-6-luna | run meta `session_id` is null. Filename id `01a0e4a3-d465-7681-af98-9434b5760ff8` | `rollout-2026-09-27T15-52-17-01a0e4a3-d465-7681-af98-9434b5760ff8.jsonl` |

Luna’s start time in run meta is `Sun Sep 27 15:52:16 CDT 2026`. The rollout timestamp is `15-52-17`. Join on that file when `session_id` is null, then write the id back.

### Which total is honest

`thread_token_usage` is a running sum of per-turn usage. `input_tokens` includes cached input. `cached_input_tokens` and `cache_write_input_tokens` are subsets, not extra tokens. `total_tokens = input_tokens + output_tokens`. `reasoning_output_tokens` is in neither `output_tokens` nor `total_tokens`.

The CLI footer is a third number:

```
uncached = input_tokens - cached_input_tokens - cache_write_input_tokens
tokens used = uncached + output_tokens
```

Checked against `codex-final-usage.json` and the site:

| Model | Uncached input | Output | Footer = site `tokens_total` | Thread `total_tokens` | Cached input | Reasoning |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| astra | 29,349 | 12,919 | 42,268 | 246,428 | 204,160 | 1,414 |
| sol | 39,539 | 21,237 | 60,776 | 481,384 | 420,608 | 6,031 |
| luna | 20,802 | 7,299 | 28,101 | 72,133 | 44,032 | 2,114 |

42,268 is not the thread total and it is not a pricing bucket. It drops every cached input token and every reasoning token. For astra that drops 204,160 cached tokens. Do not price 42,268 or 246,428 at a single rate.

Card fields to write, matching Grok / OpenRouter shape:

- `input_tokens` = rollout `input_tokens` (includes cached)
- `cached_input_tokens` = rollout `cached_input_tokens` (new field; `arcade.js` ignores unknown keys, so the card will not show it until a later display change)
- `output_tokens` = rollout `output_tokens`
- `thinking_tokens` = rollout `reasoning_output_tokens`
- `tokens_total` = rollout `total_tokens` (input + output, reasoning excluded)

Once `output_tokens` is set, the strip label flips from `TOTAL` to `OUT` (`stripToken` in `arcade.js`). Astra’s strip changes from 42,268 to 12,919. That matches every other harness, which shows output on the strip. The detail row `TOTAL` keeps the thread total.

### How to extract

Sketch, not a publisher. On the Mac, for one session:

```bash
python3 - << 'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
last = None
for line in path.open():
    obj = json.loads(line)
    usage = (obj.get("payload") or {}).get("thread_token_usage")
    if usage:
        last = usage
info = None
for line in path.open():
    obj = json.loads(line)
    info = ((obj.get("payload") or {}).get("info") or {}).get("total_token_usage") or info
assert last == info, (last, info)
print(json.dumps(last, indent=2))
PY
# pass the rollout path
```

Assert the printed object equals the matching entry in `codex-final-usage.json` before touching the site. Also assert `uncached + output_tokens` equals the stderr footer (`42,268` / `60,776` / `28,101`).

Per-turn check before any long-context multiplier: walk `payload.usage.input_tokens` (each turn, not the running total). The 272k band applies to one request. Astra’s summed input is 233,509 and luna’s is 64,834, so no turn can be over 272k. Sol’s sum is 481,384, so a late turn might be. If every sol turn is under 272,000, standard rates on the summed buckets are exact because the rates are linear. If any turn is over, price that turn at the long-context band and sum turns. Do not apply 2x to the 481,384 sum.

### How to price

Two rate cards. These runs used `CODEX_HOME=.../codex-chatgpt`, not an API-key home. Confirm auth mode without printing secrets (`codex login status` in that `CODEX_HOME`, or the auth file’s mode field).

**ChatGPT Codex (this home’s likely meter).** [Codex pricing](https://developers.openai.com/codex/pricing), Standard speed, credits per 1M tokens. “Codex credit billing has no separate cache-write charge. API-key usage follows API pricing.” These three rollouts have `cache_write_input_tokens = 0`, so the write waiver does not move the number. `run.sh` sets `model_reasoning_effort=high` and does not enable fast mode, so not the 2.5x fast multiplier.

| Model | Input | Cached input | Output |
| --- | ---: | ---: | ---: |
| gpt-6-astra | 250 | 25 | 1,250 |
| gpt-6-sol | 50 | 5 | 250 |
| gpt-6-luna | 2.5 | 0.25 | 12.5 |

```
credits = uncached/1e6 * input_rate + cached/1e6 * cached_rate + output/1e6 * output_rate
```

Credits are not dollars. Included plan usage is not an extra invoice. Credit purchase price depends on the plan. Do not divide credits by 25 and call it `cost_usd`. The API card is numerically 25 credits per API-list dollar; that is not what a ChatGPT credit costs.

**API-key mode only.** [gpt-6-astra](https://developers.openai.com/api/docs/models/gpt-6-astra), [gpt-6-sol](https://developers.openai.com/api/docs/models/gpt-6-sol), [gpt-6-luna](https://developers.openai.com/api/docs/models/gpt-6-luna), USD per 1M, standard, prompts at or under 272k input:

| Model | Input | Cached input | Cache writes | Output |
| --- | ---: | ---: | ---: | ---: |
| gpt-6-astra | 10 | 1 | 12.50 | 50 |
| gpt-6-sol | 2 | 0.20 | 2.50 | 10 |
| gpt-6-luna | 0.10 | 0.01 | 0.125 | 0.50 |

Cache writes are 1.25x uncached input and are not an extra fee on top of input. Ordinary input is `input_tokens - cached_input_tokens - cache_write_input_tokens`.

**Reasoning gate (do this before writing `cost_usd`).** OpenAI bills reasoning tokens as output, and this rollout schema stores them outside `output_tokens`. The CLI footer also excludes them. So there are two candidates: bill `output_tokens` only, or bill `output_tokens + reasoning_output_tokens` at the output rate. Pick the one that matches a single session on the Codex usage dashboard. Until that match, leave `cost_usd` null.

Worked example from `codex-final-usage.json` (estimates, not for `meta.json`):

| Model | Credits, output only | Credits, output + reasoning | API-list USD, output only | API-list USD, output + reasoning |
| --- | ---: | ---: | ---: | ---: |
| astra | 28.59000000 | 30.35750000 | 1.14360000 | 1.21430000 |
| sol | 9.38924000 | 10.89699000 | 0.37556960 | 0.43587960 |
| luna | 0.15425050 | 0.18067550 | 0.00617002 | 0.00722702 |

What to store:

- Always store the token split above. That part is evidence, not an estimate.
- Store `cost_usd` only when the dashboard shows a USD charge for that session (enterprise USD rate card or a metered API key).
- If the session drew ChatGPT credits inside the included allowance, leave `cost_usd` null and put the credit total in the note, for example `Codex credits: 30.3575 (included in plan)`.
- If Jon wants a comparable list-price column anyway, that is the same honesty class as Gemini PR #1: label the note `API-list estimate`, and only after the reasoning gate.

### Forward harvest

After `codex exec` exits, resolve the rollout from `session_id` (parse it from the CLI if run meta does not have it; luna shows the footer can exist while `session_id` is null). Write the last `thread_token_usage`, assert it equals the last `info.total_token_usage`, assert `uncached + output_tokens` equals the stderr footer, then publish the split. Do not publish the footer as `tokens_total`.

## Antigravity (Gemini)

### Where the tokens are

`agy -p ... --model gemini-3.7-flash-high --effort high --output-format stream-json` writes `transcript.jsonl`. Each completed model step is `event=step_update`, `state=DONE`, `step_type=agent_response`, with `usage`: `input_tokens`, `output_tokens`, `thinking_tokens`, `cache_read_tokens`, `total_tokens`.

Those usage objects are per turn, not a running total. In the pack prefix the input counts are 13,702 then 14,289 then 14,577, which is growing context, not a cumulative sum. Sum `DONE` `agent_response` usage. Tool steps in the prefix have no `usage`.

The pack’s transcript copies are prefixes (11 and 14 lines). The Mac files are the real source (`ls` shows `transcript.jsonl` at about 55KB for 3.7). `stderr.log` in the pack is empty. `gemini-results.json` has `"cost": null` for both. The site numbers (3.7: input 208,799, output 38,055, thinking 10,937; 3.8: input 494,199, output 68,521, thinking 33,907) are whatever the publisher summed. Re-sum the full file and require an exact match before pricing.

`-high` in the model id is the effort flag in `run.sh`, not a separate Gemini SKU.

### Pricing (optional)

Source: [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing). `gemini-3.7-flash` and `gemini-3.8-flash`, paid tier, through 2026-12-31: input $0.75 / 1M, output $3.75 / 1M including thinking tokens, context cache read $0.075 / 1M. Standard rates double on 2027-01-01. These runs are 2026-09-27, so the intro card applies if they were billed as paid API.

Draft PR #1 uses:

```
cost_usd = input/1e6 * 0.75 + (output + thinking)/1e6 * 3.75
```

Arithmetic checks: 3.7 = 0.34031925, 3.8 = 0.75475425. Adopt that only when the full-transcript sum of `cache_read_tokens` is 0 and the input/output/thinking sums match the card. If `cache_read_tokens` is non-zero, treat it as a subset of `input_tokens` unless a turn shows otherwise, and price cache reads at $0.075 and the remainder at $0.75. Thinking stays at the output rate. Label the note as a public-rate estimate. `gemini-results.json` does not show an invoice.

Antigravity may be plan-included. Same rule as Codex: tokens are real; `cost_usd` is an estimate unless a Google bill charges this conversation (`conversation_id` is on the transcript `init` event; 3.7’s prefix id is `800e18c5-9b72-483f-8a07-b8a666599492`).

### Forward harvest

Sum the usage objects at the end of `run.sh`. Persist `cache_read_tokens`. Leave `cost_usd` unset unless the rate card above was applied and the note says it is an estimate.

## Cursor Cloud

### Where tokens are, and where they are not

Nothing in this repo or the pack has Cursor token logs. Phase 1 Cursor cards have null duration and null model actual/requested. muse-spark-1.3 has duration 84,492 ms and the note `Cursor Cloud new_repo cell`. The footer in `index.html` already says Cursor Cloud cells do not expose local token logs.

This VM’s cloud-agent list only returns agents for the pacman-bakeoff environment. It does not see the original bake-off runs. Do not invent usage from that list.

On the Mac, `yallware` branch names from the pack’s path scan:

- `cursor/publish-gpt-5.6-sol-pacman-32b7`
- `cursor/publish-gpt-5.6-terra-pacman-02c1`

Search those branches, their PR bodies, and commit messages for `bc-` ids. Also search the Cursor usage dashboard for the run window. muse-spark, cursor-auto, and gpt-5.6-luna need the same search; only sol and terra have known branch names.

### Extract

Cloud Agents API, [Get Agent Usage](https://cursor.com/docs/cloud-agent/api/endpoints):

```bash
curl --request GET \
  --url "https://api.cursor.com/v1/agents/${BC_ID}/usage" \
  -u "$CURSOR_API_KEY:"
```

Response `usage` fields: `inputTokens`, `outputTokens`, `cacheWriteTokens`, `cacheReadTokens`, `totalTokens`. On this API, `totalTokens` is the sum of those four. `inputTokens` does not include cache reads. Do not subtract cache from input the way Codex requires.

Map onto the card:

- `input_tokens` = `inputTokens` (uncached input only, per this API)
- `cached_input_tokens` = `cacheReadTokens`
- add `cache_write_tokens` = `cacheWriteTokens` if you want the fourth bucket
- `output_tokens` = `outputTokens`
- `tokens_total` = `totalTokens`
- `thinking_tokens` stays null unless a separate reasoning field shows up. Do not invent it.

A transcript dump is a cross-check, not the bill. Fields worth grepping: `usage`, `tokenUsage`, `inputTokens`, `outputTokens`, `cacheReadTokens`, `cacheWriteTokens`, `chargedCents`. Zeros mean the run recorded no usage, not “use a list price.”

### Pricing

This endpoint returns tokens, not dollars. Dollars come from team usage events `chargedCents` (filter `cloudAgentId` to the `bc-` id) or the SDK `Agent.getUsage().cost`. `chargedCents` is 0 for plan-included, BYOK, and credit-grant usage, and `cost` is absent until the charge settles.

If `chargedCents` is present and non-zero, `cost_usd = chargedCents / 100`. If it is 0 or absent, store the tokens and leave `cost_usd` null. Do not price Cursor Cloud with the OpenAI GPT-5.6 card, and do not price `muse-spark-1.3` from a public rate. There isn’t a harness invoice in the pack.

### What stays blank

If the `bc-` id is gone or the usage API returns all zeros, that card stays `—`. No estimate from HTML size or wall clock.

### Forward harvest

When a Cloud agent run is published, save the `bc-` id on the run meta and call `/v1/agents/{id}/usage` before publishing `entries/meta.json`. Copy `chargedCents` only when it is a real charge.

## Grok Bot

`entries/meta.json` note: `in-chat from short prompt; no peeking`. Duration 39,000 ms. Every token field and `cost_usd` are null. The pack has no grok-bot transcript, session id, or usage object. Grok chat does not write a pacbake usage file. This entry stays `—`.

Grok Build already stores `cost_usd` from that harness. A future metered run has to go through a harness that returns usage (Grok Build, or the xAI API usage object). Do not backfill grok-bot from a Grok Build rate.

## Working harnesses — do not recompute

Claude Code run meta for opus-5-5 has `cost_usd_approx: 1.9933716` and `session_id: a1e33310-4a13-4238-83ba-6488f9a02eeb`. The site `cost_usd` for `claude-opus-5-5` is that same number. The publisher copies the harness figure.

Several Claude cards have tiny `input_tokens` (opus-4-6 is 24, opus-4-8 is 4) next to multi-dollar costs. Those input fields are not the billed input. A formula dry-run against the card will not match, and it should not. The check is: the session result’s `total_cost_usd` equals the card. Leave those costs alone.

## Tests

1. **Codex identity.** From `codex-final-usage.json`, `input - cached - cache_write + output` equals site `tokens_total` (42,268 / 60,776 / 28,101) and `input + output` equals `total_tokens` (246,428 / 481,384 / 72,133).
2. **Codex parser.** On the Mac, the last `thread_token_usage` in each rollout equals `final_thread_token_usage` and equals `final_info_total_token_usage`.
3. **Codex footer checksum.** Stderr `tokens used` equals test 1’s footer number, and the published `tokens_total` becomes the thread total, not the footer.
4. **Sol long-context.** Every per-turn `payload.usage.input_tokens` is either under 272,000 or that turn is priced on the long-context band. Astra and luna cannot fail this; their sums are under 272k.
5. **Reasoning gate.** One dashboard session credit total equals either the output-only credit column or the output-plus-reasoning column. Do not write `cost_usd` before this passes.
6. **Claude copy, not a formula.** Session `a1e33310-4a13-4238-83ba-6488f9a02eeb` result `total_cost_usd` equals 1.9933716. Recomputing from the card’s `input_tokens` is expected to fail.
7. **Gemini sum.** Full `transcript.jsonl` sum of `DONE` `agent_response` usage equals the card’s input, output, and thinking. Record the `cache_read_tokens` sum. PR #1’s formula is allowed only when that cache sum is 0.
8. **Cursor dump.** For one recovered `bc-` id, `GET /v1/agents/{id}/usage` returns non-zero `totalTokens`, and `inputTokens + outputTokens + cacheWriteTokens + cacheReadTokens` equals `totalTokens`. `cost_usd` is set only when `chargedCents > 0`.
9. **Grok Bot absence.** No usage file under the grok-bot run. Card stays null.

## Risks

- Publishing 42,268 as `tokens_total` understates astra about 6x versus the thread total and hides the cache split that pricing needs.
- Writing the API-list USD figures above into `cost_usd` invents an invoice. ChatGPT Codex bills credits, and included usage may be $0 extra.
- Billing reasoning twice, or not at all, is still open until test 5.
- Applying the 272k multiplier to sol’s summed 481,384 input would overcharge. The band is per request.
- Cursor list-price substitution (OpenAI GPT-5.6 rates, or any muse-spark rate) invents spend. `chargedCents == 0` is “included,” not “missing, so estimate.”
- Gemini PR #1 overcharges if `cache_read_tokens` is non-zero, and it is not an Antigravity invoice.
- Claude card `input_tokens` cannot validate a cost formula.
- Grok Bot cannot be recovered. A made-up token count would be fiction.

## Out of scope

Do not edit `entries/*.html`. Do not change `entries/meta.json` in the planning change. Do not merge a number from this document without the test that belongs to it.
