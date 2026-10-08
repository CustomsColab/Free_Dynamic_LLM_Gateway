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

`registry/models.json` ships as a **seed** (starter list) so the package works before the first refresh.

## How the router decides

1. Filter: chat models, free only, key present, gateway not exhausted, model not cooling, has the needed
   capability (tools/json/vision), meets `min_context`.
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

## Limits to know

* `limits.rpd/rpm` in the registry are approximate published numbers, used only for load spreading; the server's 429 is the truth. Verify your own quotas.
* `capability_source: inferred` means the gateway does not declare tools/JSON support, so it is a heuristic. A model that rejects tools gets a 400 and is skipped for 5 min.
* Gateways that expose no pricing in `/models` (Groq, Gemini, Cerebras, Mistral, NVIDIA) are treated as `free_tier`: free within their rate limits, not unlimited. Token Harbor / Together / Fireworks count as free only when the listed price is 0.
* Free routes may log or train on prompts. Do not send confidential data (GST/departmental material) to them without reading each gateway's terms.
* Not included: streaming, async tools, cross-machine shared ledger (swap `_load_state/_save` for Redis or a DB if you need one).
* GitHub disables scheduled workflows on public repos after 60 days without repo activity; the bot commit each run counts as activity.
