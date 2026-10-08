# freellm: a free, self-healing LLM router backed by a GitHub-hosted registry

Club the free tiers of many OpenAI-compatible gateways (Groq, Cerebras, Gemini, OpenRouter `:free`,
Mistral, NVIDIA NIM, Together, Fireworks, Token Harbor, any custom URL) into one call.

```
GitHub Actions (every 6h)                      Your app(s)
  scripts/refresh_registry.py  -->  registry/models.json  -->  freellm.py
  asks each gateway /models        (size, context, caps,        picks model by TASK, tracks today's
  keeps free models, drops dead     categories, free flag)       rate limits, fails over, runs tools
```

## Two kinds of data (important)

| Data | Where it lives | Why |
|---|---|---|
| Model catalogue: size, context class, capabilities, categories, free flag | `registry/models.json` (public, shared, refreshed by Actions) | Same for everyone |
| **"Rate limit exhausted today: yes/no"** per gateway and per model | `.freellm_state.json` on the machine running your app (live ledger) | Limits are per API key. A public file refreshed every 6h cannot know your quota |

`router.gateway_status()` returns the yes/no flag per gateway; `router.live_registry()` returns the
registry with that overlay (`rate_limit_exhausted_today`, `usable_now`) merged in. Apps on one machine
share the ledger by pointing `FREELLM_STATE` at the same file.

## Reading the registry on GitHub (tables, not JSON)

Every refresh also writes two files that GitHub displays as tables:

* **`registry/MODELS.md`** - open it in the repo and GitHub renders it. It has: a guide to which context class
  (short / medium / long / ultra) you need, a gateway x context-class count, the best 3 picks per task, every free model
  grouped by context class with size, context, tools/JSON/vision/code/reasoning, quality and speed, and the health of the last refresh.
* **`registry/models.csv`** - GitHub shows a table; download it and open in Excel/Sheets to sort and filter (includes paid models, `is_free` column).

`models.json` stays the machine-readable source for your apps.

## Intelligence rating

Each model gets `intelligence_tier` (1-5) and `intelligence_label` from its size: Basic (~1-3B), Fair (~4-12B), Good (~13-30B),
Strong (~32-100B), Top (100B+ / frontier). Models that publish no size (Gemini, Mistral Large...) use a family estimate; reasoning models get a small bonus.
It is a rough proxy, not a benchmark. In an app: `llm.chat(..., min_intelligence=4)` only uses Strong or Top models
(for example for coding or reasoning), while `task="fast"` prefers smaller, quicker ones.

## Choosing long vs short context in your app

You do not have to decide by hand. `llm.chat(...)` estimates the prompt size (about 4 characters per token, plus tools
and the reply budget). If it is above ~6,000 tokens it only considers models whose context window fits it (+15% margin);
small prompts can use the fast short-context models. If nothing fits you get a clear error before any request is spent.
Override: `auto_context=False`, or force with `task="long_doc"` (64K+), `context="long"`, `min_context=100_000`.
Models whose gateway does not report context length show `?` and are skipped for big prompts.

## Registry fields (per model)

`uid, gateway, model_id, display_name, size_b, size_label ("70B"), size_class (tiny <4B | small 4-14B |
medium 15-40B | large 41-100B | xlarge >100B | unknown), context_length, context_class (short <=8k |
medium <=32k | long <=200k | ultra | unknown), long_context (>=64k), context_source (api|hint),
is_free, free_kind (zero_price|free_tier), capabilities {chat,json,tools,vision,coding,reasoning},
capability_source (declared|inferred), categories [general, coding, reasoning, vision, extraction, agent,
long_doc, fast], quality_hint, speed_hint, status (active|missing), first_seen, missing_since`

Gateway block: `base_url, key_env (name only), free_mode, daily_scope, limits {rpm, rpd, approximate}, speed_base`.

## Setup (10 minutes)

1. Create a GitHub repo, upload this folder.
2. Settings > Secrets and variables > Actions: add keys for the gateways you use
   (`GROQ_API_KEY`, `GEMINI_API_KEY`, `CEREBRAS_API_KEY`, `OPENROUTER_API_KEY`, `MISTRAL_API_KEY`,
   `NVIDIA_API_KEY`, `TOGETHER_API_KEY`, `FIREWORKS_API_KEY`, `TOKEN_HARBOR_API_KEY`, `FASTROUTER_API_KEY`; optional `CUSTOM_LLM_BASE_URL` + `CUSTOM_LLM_API_KEY`).
3. Actions tab > "Refresh dynamic LLM registry" > Run workflow. It runs tests, refreshes, commits.
4. In each app: copy `freellm.py`, `pip install httpx`, set `FREELLM_REGISTRY_URL` and the same gateway keys, paste `examples/app_snippet.py`.

(The refresh also creates `registry/MODELS.md` and `registry/models.csv`.) `registry/models.json` ships as a **seed** (starter list) so the package works before the first refresh.

## How the router decides

1. Filter: chat models, free only, key present, gateway not exhausted, model not cooling, has the needed
   capability (tools/json/vision), meets `min_context` (set automatically from prompt size, see above).
2. Score: +100 if the model's categories match the task, + weighted quality/speed hints,
   + up to 30 for remaining daily quota (spreads load across free tiers), minus recent failures.
3. Call best; on failure update the ledger and try the next.

| Response | Ledger action |
|---|---|
| 429 + daily wording / Retry-After > 15 min / remaining=0 with long reset | exhausted until reset (model or whole gateway per `daily_scope`); 3+ models limited => gateway flagged |
| 429 per-minute | model cooldown (Retry-After or 30s); 3 in 60s => gateway cooldown |
| 200 but `x-ratelimit-remaining-requests: 0` | marked early, before the next call wastes a request |
| 404 | model disabled 24h (removed from catalogue) |
| 402 | gateway exhausted until 00:00 UTC |
| 401 | gateway parked 1h (bad key) |
| 400/422 | model 5 min |
| 5xx/timeout | exponential cooldown, max 15 min |

The ledger resets at 00:00 UTC. Some gateways reset on rolling windows; server `Retry-After` wins when present.

## Task presets

`chat | fast | coding | reasoning | extraction (JSON) | vision | long_doc | agent (tools)`.
Override with `need_tools, need_json, need_vision, min_context, context="long", min_size_b, max_size_b,
prefer="quality"|"speed", gateways=[...], exclude=[...]`.

## Refresh logs: which gateways worked, which failed

Every refresh records one line per gateway. You can read it in three places:

1. **GitHub run page:** Actions > the run > "Summary" shows a table (status, HTTP code, latency, models listed, free models, added, removed, error).
2. **`registry/refresh_log.jsonl`:** one JSON line per run, the last 200 runs kept (history).
3. **`registry/models.json` > `last_refresh`:** the latest run only (the app can read this too).

Status values: `ok` (free models found) | `no_free_models` (answered, nothing free) | `empty` | `error` (kept old entries) | `skipped` (no key).
`added` / `removed` list model ids that appeared or disappeared since the previous run (first 10 shown, plus counts).
The job prints a warning if no gateway returned any free models.

## CLI

```
python freellm.py status            # yes/no per gateway
python freellm.py pick --task coding
python freellm.py ask "hello"
```

## Troubleshooting: the bot cannot push (403) / "Read and write permissions" is greyed out

That radio button is greyed when an organization or enterprise policy fixes the default to read-only.
First just run the workflow: it requests `contents: write` itself and usually succeeds. If the push step
still fails with 403, use a personal token instead:

1. GitHub > your profile picture > Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token.
2. Repository access: only this repo. Permissions > Repository permissions > **Contents: Read and write**. Generate and copy it.
3. In the repo: Settings > Secrets and variables > Actions > New repository secret, name `REGISTRY_PUSH_TOKEN`, paste the token.
4. Run the workflow again (the workflow already prefers this secret when present).

Simplest alternative: create the repo under your personal account instead of the organization.

## Limits to know

* `limits.rpd/rpm` in the registry are approximate published numbers, used only for load spreading; the server's 429 is the truth. Verify your own quotas.
* `capability_source: inferred` means the gateway does not declare tools/JSON support, so it is a heuristic. A model that rejects tools gets a 400 and is skipped for 5 min.
* Gateways that expose no pricing in `/models` (Groq, Gemini, Cerebras, Mistral, NVIDIA) are treated as `free_tier`: free within their rate limits, not unlimited. Together / Fireworks / FastRouter count as free only when the listed price is 0. Token Harbor's `/models` returns ids only (no prices), so none of its models can be detected as free; it is useful only as a paid fallback (`allow_paid=True`).
* Free routes may log or train on prompts. Do not send confidential data (GST/departmental material) to them without reading each gateway's terms.
* Not included: streaming, async tools, cross-machine shared ledger (swap `_load_state/_save` for Redis or a DB if you need one).
* GitHub disables scheduled workflows on public repos after 60 days without repo activity; the bot commit each run counts as activity.
