# How public benchmarks get OpenAI and Codex costs

Research date: 2026-09-28. This note is for the Pac-Man bake-off. It does not change any `cost_usd` value.

`docs/cost-recovery.md` is not in this repo. The policy at the bottom is the recommendation.

## What this bake-off already does

OpenRouter and other metered harnesses store a dollar figure in `cost_usd`. The three native Codex cards (`gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna`) store `cost_usd: null`. Their notes say the figures are Codex credits, not dollars, and that the ChatGPT dashboard was not checked.

Those credit figures are not a dashboard export. They reconstruct exactly from each card's token counts and the ChatGPT Work / Codex Standard credit card fetched the same day from [learn.chatgpt.com/docs/pricing.md](https://learn.chatgpt.com/docs/pricing.md):

| Model | Credits per 1M input / cached input / output |
| --- | ---: |
| GPT-6 Astra | 250 / 25 / 1,250 |
| GPT-6 Sol | 50 / 5 / 250 |
| GPT-6 Luna | 2.5 / 0.25 / 12.5 |

Formula, with cached tokens subtracted out of `input_tokens`:

```
credits = (input - cached) * input_rate / 1e6
        + cached * cached_rate / 1e6
        + output * output_rate / 1e6
```

The note's smaller number is that sum. The larger number adds `thinking_tokens` at the output credit rate. The words "Output only" in the notes do not match the arithmetic: the smaller number already includes fresh input and cached input, and it leaves reasoning out. `tokens_total` on these cards is `input_tokens + output_tokens` and does not include `thinking_tokens`, so the two note figures are "visible tokens" and "visible tokens plus reasoning priced as output."

## 1. Metered OpenAI API cost is tokens times the public rate card

That is the default everywhere a dollar is attached to an OpenAI model call.

- The [OpenAI API pricing page](https://developers.openai.com/api/docs/pricing) lists USD per 1M tokens for input, cached input, cache writes, and output, with separate short-context, long-context, Batch, Flex, and Fast columns. On 2026-09-28 the Standard short-context row was GPT-6 Astra `$10 / $1 / $12.50 / $50`, GPT-6 Sol `$2 / $0.20 / $2.50 / $10`, GPT-6 Luna `$0.10 / $0.01 / $0.125 / $0.50`.
- [Advanced usage](https://developers.openai.com/api/docs/guides/advanced-usage) says an API call is billed per token and that the response `usage` field is the token count, not a dollar amount.
- The original SWE-bench inference script hard-coded `MODEL_COST_PER_INPUT` and `MODEL_COST_PER_OUTPUT` and multiplied ([commit `0060c01`](https://github.com/SWE-bench/SWE-bench/commit/0060c01db7b2e28cf721a66824825411e2be428d)). SWE-bench+ reports average dollars per instance and per resolved issue for GPT-4 and GPT-4o runs ([arXiv:2410.06992](https://arxiv.org/abs/2410.06992)).
- SWE-agent and mini-SWE-agent call `litellm.cost_calculator.completion_cost`, which looks up a community price table. OpenRouter responses can supply `usage.cost` directly. Unknown models are either a hard error or an explicit zero, not a guessed price ([SWE-agent models docs](https://swe-agent.com/latest/config/models/), [mini-SWE-agent local models](https://mini-swe-agent.com/latest/models/local_models/)).
- [Artificial Analysis methodology](https://artificialanalysis.ai/methodology) defines price as the provider's listed per-token price and cost-per-task as tokens consumed on the eval times those prices, including cache hit and cache write. They restrict "serverless" to endpoints the customer pays per use, not a flat subscription. Blended price assumes a 7:2:1 cache-hit / input / output mix, which is a comparison convention, not a bill.
- HELM (Liang et al., 2022, [arXiv:2211.09110](https://arxiv.org/abs/2211.09110)) reported the commercial API bill for the study (`$38,001`) and the token total. The harness dry-run estimates tokens with a tokenizer. It does not invent a dollar figure from a subscription.
- LiveCodeBench's own site ranks solve rate and does not publish run cost ([livecodebench.github.io](https://livecodebench.github.io/)). Third-party pages that put `$/M` tokens beside a LiveCodeBench score are attaching the list price, not the cost of the eval run.
- LMSYS / Chatbot Arena ranks human preference. Cost is not an input to the score ([LMSYS, Dec 2023](https://www.lmsys.org/blog/2023-12-07-leaderboard/)).

When a vendor bill exists, harnesses prefer it. OpenRouter documents `usage.cost` as the amount charged for that response ([Usage Accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting)). The Platform admin endpoint `GET /v1/organization/costs` returns `amount.value` and `amount.currency` for API organization spend ([Usage Costs API](https://platform.openai.com/docs/api-reference/usage/costs)). That endpoint is Platform billing. It is not the ChatGPT Plus meter.

## 2. ChatGPT Plus, Codex credits, and products that do not bill per token

OpenAI runs two meters.

- **API key.** Codex can be pointed at an API key. The pricing doc says that path pays [API prices](https://learn.chatgpt.com/docs/pricing.md). Dollars then come from the pricing page or from `/v1/organization/costs`.
- **ChatGPT plan (Free, Go, Plus, Pro, Business, Enterprise).** Codex is included usage. After the included allowance, Plus and Pro can buy credits. The same page prices Standard speed in **credits per 1M tokens**, not dollars. It says credit purchase prices and discounts depend on the plan or agreement. It also says Codex credit billing has **no separate cache-write charge**, while API-key usage follows API pricing, which does charge cache writes (1.25× uncached input on GPT-5.6 and later; see [prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)).

The help center describes credits as overflow after included limits, shared across Codex and other agentic features, with a balance separate from the ChatGPT wallet ([Using credits for flexible usage](https://help.openai.com/en/articles/12642688-using-credits-for-flexible-usage-in-chatgpt-personal-plans)). Included Plus usage is not a per-token USD charge. ChatGPT Plus and the API have been separate products for years ([What is ChatGPT Plus?](https://help.openai.com/en/articles/6950777-what-is-chatgpt-plus)).

No OpenAI page found on this pass states "1 credit = $0.04" or any other official exchange rate. Dividing the two public cards does land on $0.04 for the GPT-6 Standard short-context rows (Astra `$10 / 250`, Sol `$2 / 50`, Luna `$0.10 / 2.5`, and the same ratio on cached input and output). Commentators treat that as evidence of list-price parity ([Continuum plan picker](https://continuumcode.ai/tools/codex-plan-picker/)). It is a derivation. It is not the cash price of a turn that was inside the Plus allowance, and it ignores the API-only cache-write charge. Older snippets of the help-center rate card still show different GPT-5.6 Sol numbers (125 / 12.5 / 750 versus 100 / 10 / 500 on the 2026-09-28 pricing doc). The card moves. A frozen multiplier will go stale.

Public agent leaderboards that show dollars next to Codex are estimating the API-equivalent, not reading a Plus invoice.

- Terminal-Bench 2.0 plots USD cost, including Codex CLI rows, on a performance-versus-cost chart ([ICLR 2026 PDF](https://proceedings.iclr.cc/paper_files/paper/2026/file/444a3737adaee10d86ad2ef5f74468e6-Paper-Conference.pdf)). The Harbor maintainer thread shows that number as token totals times the published API rates, and notes that missing `cache_write_tokens` makes it diverge from what OpenAI actually charges on the API ([harbor#2342](https://github.com/harbor-framework/harbor/issues/2342)).
- [ccusage](https://github.com/ccusage/ccusage/blob/main/docs/guide/codex/index.md) reads local Codex session logs and prices them with LiteLLM's API table. Its own docs say `costUSD` is an API-equivalent estimate, not a ChatGPT credit balance. For Fast mode it uses the published API multiplier when one exists (2× for GPT-5.6) and refuses to invent a multiplier when it does not. It explicitly distinguishes that from ChatGPT's 2.5× credit multiplier.
- A one-lab SWE-bench Pro writeup keeps two ledgers: an **economic** cost at public API rates, which is the number on the scoreboard, and a **cash** cost, where Codex and Cursor subscription runs are marginal ~$0 ([COST_BASIS.md](https://github.com/kimjune01/swebench-pro/blob/main/docs/COST_BASIS.md)). The author says the cash number is real and not reproducible.

Snorkel and similar Terminal-Bench boards that print `$3.3k` beside "GPT-6 Astra / Codex" are in the first camp: a dollar total for the sweep, not a credit balance ([Snorkel Terminal-Bench 4.0](https://snorkel.ai/leaderboard/terminal-bench-4-0/)). They do not document a credits-to-USD function.

## 3. What people do when the only meter is credits or a subscription

| Practice | Who | What gets published |
| --- | --- | --- |
| Omit dollars | This bake-off's Codex and Cursor Cloud cards; LiveCodeBench; Arena | Dash or no cost column. Tokens can still be shown. |
| Tokens × public API rate card | SWE-bench script, LiteLLM, Harbor, ccusage, Artificial Analysis, most "$/task" blog tables | A comparable list-price estimate. Label it as list price. It is not the subscription invoice. |
| Vendor `usage.cost` or Costs API | OpenRouter cells; Platform admin costs API | The charged USD for that metered call. |
| Report credits, not dollars | OpenAI's own Codex rate card; this bake-off's Codex notes | The unit the product actually meters. |
| Dual basis | kimjune01 SWE-bench Pro cost note | Scoreboard uses API-equivalent dollars. A separate note records that subscription cash was ~$0. |
| `$0` because it was inside the plan | Sometimes used as the cash basis | Honest only if labeled marginal cash. False as a comparable cost: it ranks every subscription cell as free. |

The failure mode these sources avoid is writing a made-up dollar into the same field as a real invoice.

## 4. Is there a credits-to-USD converter?

No official one.

- OpenAI publishes credits per million tokens, and separately publishes API dollars per million tokens. The pricing doc says the purchase price of a credit depends on the plan.
- ccusage and Harbor do not convert credits. They multiply tokens by API list prices and label the result as an estimate.
- Third-party calculators that say "$0.04 per credit" are doing the division above. They are not an OpenAI API.

There is nothing safe to vendor into this repo that turns a Codex credit balance into `cost_usd`.

## 5. Policy for this bake-off

`cost_usd` means "dollars a meter charged, or a labeled list-price estimate when the card says so." It does not mean "a comparable number we computed because the column looked empty."

**Native Codex / ChatGPT subscription cells (the three GPT-6 cards, and later ones like them):**

- Leave `cost_usd` null. The gallery already renders that as a dash. Do not write `0`.
- Keep the credit figures in `note`. They match the 2026-09-28 Standard credit card. Say they are rate-card credits, not a dashboard charge, and point here.
- Do not multiply those credits by $0.04 and store the product in `cost_usd`. That number was not billed, the exchange rate is not an OpenAI field, and the API card's cache-write price is a different product.
- If someone later reads the ChatGPT usage dashboard for that run, quote the credits it shows. Still leave `cost_usd` null unless the dashboard shows a dollar charge for purchased overflow credits on that run.

**OpenRouter, API-key Codex, and any other metered call:**

- `cost_usd` is the provider's reported cost (`usage.cost`, session cost, or the Costs API amount). That is the number to keep.
- If the provider returns tokens and no dollars, `cost_usd` may be tokens times the provider's published rate card **as of the run date**, and the note must name the card and the date. Missing cache-write or long-context flags stay missing. Do not backfill them.
- Do not reprice an OpenRouter bill with OpenAI's first-party card. The invoice is the invoice.

**Cursor Cloud and any harness with no usage payload:**

- Leave tokens and `cost_usd` null, as the current notes already say. Do not estimate from HTML size or wall clock.

**Sorting.** Cost sort only orders cells that have `cost_usd`. Nulls stay off that ranking. A subscription cell is not cheaper than an OpenRouter cell because its dollar field is empty.
