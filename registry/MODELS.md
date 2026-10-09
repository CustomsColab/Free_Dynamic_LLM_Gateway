# Free LLM models: decision tables

Updated **2026-10-09T22:41:29Z** | source: **live** | table format v2 | **193** free models on **7** gateways

> Generated file. Do not edit by hand: it is rebuilt after every registry refresh. Grouped, colour-coded decision table: [models.csv](models.csv) (view on GitHub) and [models.xlsx](models.xlsx) (download, real colours + filters).

## 1. Which context size do I need?

| Class | Tokens | About | Use it for | Notes | Models |
|---|---|---|---|---|---|
| **ultra** | over 200K | ~150K+ words | whole books, huge codebases, dozens of documents at once | Few models (mostly Gemini). Slowest, and free token-per-minute limits bite first | 79 |
| **long** | 32K - 200K | ~25K-150K words | long reports, contracts, notices, big code files, many RAG chunks | Task `long_doc` picks from here. Send only what you need: quality drops near the limit | 17 |
| **medium** | 8K - 32K | ~6K-25K words | RAG answers with a few chunks, one document, code review | Good default for most apps | 4 |
| **short** | up to 8K | up to ~6K words | chat, classification, SQL/JSON generation, short Q&A | Fastest and cheapest on quota. Use task `fast` | 10 |
| **unknown** | not reported | ? | treat as short until tested | The gateway does not report context length and no safe default is known | 83 |

Rule of thumb: 1 token is about 4 characters, or 0.75 English words. Your app can leave this decision to the router: it estimates the prompt size and skips models whose context is too small (`auto_context`, on by default).

## 2. At a glance: free models per gateway and context class

| Gateway | ultra | long | medium | short | unknown | Total |
|---|---:|---:|---:|---:|---:|---:|
| cerebras | – | 2 | 1 | – | – | **3** |
| fastrouter | 5 | 7 | 1 | 9 | 1 | **23** |
| gemini | 35 | – | – | – | 13 | **48** |
| groq | – | 3 | – | 1 | – | **4** |
| mistral | 23 | 2 | 2 | – | – | **27** |
| nvidia | – | – | – | – | 69 | **69** |
| openrouter | 16 | 3 | – | – | – | **19** |

Free models by **intelligence** and context class (pick the row you need, then the context you need):

| Intelligence | ultra | long | medium | short | unknown | Total |
|---|---:|---:|---:|---:|---:|---:|
| ★★★★★ Top | 9 | 5 | – | – | 9 | **23** |
| ★★★★☆ Strong | 26 | 2 | 2 | – | 13 | **43** |
| ★★★☆☆ Good | 20 | 3 | – | – | 12 | **35** |
| ★★☆☆☆ Fair | 2 | 1 | – | 1 | 15 | **19** |
| ★☆☆☆☆ Basic | 22 | 6 | 2 | 9 | 34 | **73** |

## 3. Best picks per task

Static ranking (quality, speed, capabilities). Live quota and rate-limit state is applied by the router at call time.

| Task | Use when | #1 | #2 | #3 |
|---|---|---|---|---|
| **chat** | general questions and writing | `cerebras/gpt-oss-120b` (120B, 128K≈, Top) | `cerebras/qwen-3-32b` (32B, 32K≈, Strong) | `groq/openai/gpt-oss-120b` (120B, 128K, Top) |
| **fast** | quick, cheap, short calls | `cerebras/llama3.1-8b` (8B, 128K≈, Fair) | `groq/allam-2-7b` (7B, 4K, Fair) | `mistral/ministral-3b-2512` (3B, 128K, Basic) |
| **coding** | write / fix code | `nvidia/ibm/granite-34b-code-instruct` (34B, ?, Strong) | `mistral/codestral-2508` (unknown, 250K, Good) | `mistral/codestral-latest` (unknown, 250K, Good) |
| **reasoning** | multi-step logic, maths, planning | `cerebras/gpt-oss-120b` (120B, 128K≈, Top) | `groq/openai/gpt-oss-120b` (120B, 128K, Top) | `fastrouter/nvidia/nemotron-3-super:free` (120B, 256K, Top) |
| **extraction** | JSON, SQL, ontology / structured output | `cerebras/gpt-oss-120b` (120B, 128K≈, Top) | `cerebras/qwen-3-32b` (32B, 32K≈, Strong) | `groq/openai/gpt-oss-120b` (120B, 128K, Top) |
| **vision** | images and screenshots | `gemini/gemini-2.5-pro` (unknown, 1M≈, Top) | `gemini/gemini-3-pro-image` (unknown, 1M≈, Top) | `gemini/gemini-3-pro-image-preview` (unknown, 1M≈, Top) |
| **long_doc** | documents over ~50 pages (needs 64K+ context) | `cerebras/gpt-oss-120b` (120B, 128K≈, Top) | `groq/openai/gpt-oss-120b` (120B, 128K, Top) | `groq/qwen/qwen3.8-27b` (27B, 128K, Strong) |
| **agent** | function calling / tools | `cerebras/gpt-oss-120b` (120B, 128K≈, Top) | `groq/openai/gpt-oss-120b` (120B, 128K, Top) | `fastrouter/nvidia/nemotron-3-super:free` (120B, 256K, Top) |

## 4. All free models, grouped by context class

Legend: ✅ declared by the gateway | ✅~ inferred from the name (not declared) | – not supported / unknown | ≈ context length is a built-in estimate because the gateway does not report it. **Intelligence** is a 1-5 rating derived from model size (parameters), with family estimates for models that publish no size (Gemini, Mistral Large...) and a small bonus for reasoning models; the number in brackets is the 0-100 score. Tiers: Basic (~1-3B), Fair (~4-12B), Good (~13-30B), Strong (~32-100B), Top (100B+ / frontier). Size is only a rough proxy: newer small models can beat older big ones, and for mixture-of-experts models the size shown is the total, not what runs per token. Speed is a 0-100 heuristic. Neither is a benchmark.

### Ultra context (over 200K), 79 models

| Gateway | Model | Size | Context | Tools | JSON | Vision | Code | Reasoning | Intelligence | Speed | Free type | Best for |
|---|---|---:|---:|:-:|:-:|:-:|:-:|:-:|---|---:|---|---|
| openrouter | `nvidia/nemotron-3-ultra-550b-a55b:free` | 550B | 1.0M | ✅ | – | – | – | ✅ | ★★★★★ Top (100) | 5 | price 0 | reasoning, agent, long_doc |
| fastrouter | `nvidia/nemotron-3-super:free` | 120B | 256K | ✅ | ✅ | – | – | ✅ | ★★★★★ Top (99) | 19 | price 0 | reasoning, extraction, agent, long_doc |
| openrouter | `nvidia/nemotron-3-super-120b-a12b:free` | 120B | 256K | ✅ | ✅ | – | – | ✅ | ★★★★★ Top (99) | 9 | price 0 | reasoning, extraction, agent, long_doc |
| gemini | `gemini-2.5-pro` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | ✅~ | ★★★★★ Top (95) | 49 | free tier | reasoning, vision, extraction, agent, long_doc |
| gemini | `gemini-3-pro-image` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★★ Top (90) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-3-pro-image-preview` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★★ Top (90) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-3.1-pro-preview` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★★ Top (90) | 49 | free tier | vision, extraction, agent, long_doc |
| gemini | `gemini-3.1-pro-preview-customtools` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★★ Top (90) | 49 | free tier | vision, extraction, agent, long_doc |
| gemini | `gemini-pro-latest` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★★ Top (90) | 49 | free tier | vision, extraction, agent, long_doc |
| mistral | `mistral-medium` | unknown | 256K | ✅ | ✅ | ✅ | – | – | ★★★★☆ Strong (82) | 44 | free tier | vision, extraction, agent, long_doc |
| mistral | `mistral-medium-2604` | unknown | 256K | ✅ | ✅ | ✅ | – | – | ★★★★☆ Strong (82) | 44 | free tier | vision, extraction, agent, long_doc |
| mistral | `mistral-medium-3` | unknown | 256K | ✅ | ✅ | ✅ | – | – | ★★★★☆ Strong (82) | 44 | free tier | vision, extraction, agent, long_doc |
| mistral | `mistral-medium-3-5` | unknown | 256K | ✅ | ✅ | ✅ | – | – | ★★★★☆ Strong (82) | 44 | free tier | vision, extraction, agent, long_doc |
| mistral | `mistral-medium-3.5` | unknown | 256K | ✅ | ✅ | ✅ | – | – | ★★★★☆ Strong (82) | 44 | free tier | vision, extraction, agent, long_doc |
| mistral | `mistral-medium-latest` | unknown | 256K | ✅ | ✅ | ✅ | – | – | ★★★★☆ Strong (82) | 44 | free tier | vision, extraction, agent, long_doc |
| gemini | `gemini-2.5-flash` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | ✅~ | ★★★★☆ Strong (80) | 49 | free tier | reasoning, vision, extraction, agent, long_doc, fast |
| gemini | `gemini-2.5-flash-image` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | ✅~ | ★★★★☆ Strong (80) | 49 | free tier | reasoning, vision, extraction, agent, long_doc, fast |
| gemini | `gemini-2.5-flash-native-audio-latest` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | ✅~ | ★★★★☆ Strong (80) | 49 | free tier | reasoning, vision, extraction, agent, long_doc, fast |
| gemini | `gemini-2.5-flash-native-audio-preview-09-2025` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | ✅~ | ★★★★☆ Strong (80) | 49 | free tier | reasoning, vision, extraction, agent, long_doc, fast |
| gemini | `gemini-2.5-flash-native-audio-preview-12-2025` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | ✅~ | ★★★★☆ Strong (80) | 49 | free tier | reasoning, vision, extraction, agent, long_doc, fast |
| fastrouter | `nvidia/nemotron-3-nano-30b:free` | 30B | 1M | ✅ | ✅ | – | – | ✅ | ★★★★☆ Strong (79) | 35 | price 0 | reasoning, extraction, agent, long_doc, fast |
| openrouter | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | 30B | 250K | ✅ | – | ✅ | – | ✅ | ★★★★☆ Strong (79) | 25 | price 0 | reasoning, vision, agent, long_doc, fast |
| gemini | `gemini-2.5-computer-use-preview-10-2025` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | ✅~ | ★★★★☆ Strong (75) | 49 | free tier | reasoning, vision, extraction, agent, long_doc |
| gemini | `gemini-3-flash-preview` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★☆ Strong (75) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-3.1-flash-image` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★☆ Strong (75) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-3.1-flash-image-preview` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★☆ Strong (75) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-3.1-flash-live-preview` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★☆ Strong (75) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-3.5-flash` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★☆ Strong (75) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-3.6-flash` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★☆ Strong (75) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-3.7-flash` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★☆ Strong (75) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-3.8-flash` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★☆ Strong (75) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-3.8-live-extended-thinking` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | ✅~ | ★★★★☆ Strong (75) | 49 | free tier | reasoning, vision, extraction, agent, long_doc |
| gemini | `gemini-flash-latest` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★☆ Strong (75) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-omni-1.1-flash` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★☆ Strong (75) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-omni-flash-preview` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★★☆ Strong (75) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| openrouter | `google/gemma-4-31b-it:free` | 31B | 256K | ✅ | ✅ | ✅ | – | – | ★★★☆☆ Good (75) | 24 | price 0 | vision, extraction, agent, long_doc |
| fastrouter | `google/gemma4-26b:free` | 26B | 256K | ✅ | ✅ | ✅ | – | – | ★★★☆☆ Good (72) | 36 | price 0 | vision, extraction, agent, long_doc |
| mistral | `codestral-2508` | unknown | 250K | ✅ | ✅ | – | ✅ | – | ★★★☆☆ Good (72) | 44 | free tier | coding, extraction, agent, long_doc |
| mistral | `codestral-latest` | unknown | 250K | ✅ | ✅ | – | ✅ | – | ★★★☆☆ Good (72) | 44 | free tier | coding, extraction, agent, long_doc |
| openrouter | `google/gemma-4-26b-a4b-it:free` | 26B | 256K | ✅ | ✅ | ✅ | – | – | ★★★☆☆ Good (72) | 26 | price 0 | vision, extraction, agent, long_doc |
| gemini | `gemini-3.5-live-translate-preview` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★☆☆ Good (70) | 49 | free tier | vision, extraction, agent, long_doc |
| gemini | `gemini-3.8-live` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★☆☆ Good (70) | 49 | free tier | vision, extraction, agent, long_doc |
| gemini | `gemini-nano-banana-2.1` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★☆☆ Good (70) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-robotics-er-2-preview` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★☆☆ Good (70) | 49 | free tier | vision, extraction, agent, long_doc |
| gemini | `gemini-robotics-er-2-streaming-preview` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★☆☆ Good (70) | 49 | free tier | vision, extraction, agent, long_doc |
| gemini | `gemini-2.5-flash-lite` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | ✅~ | ★★★☆☆ Good (65) | 49 | free tier | reasoning, vision, extraction, agent, long_doc, fast |
| mistral | `ministral-14b-2512` | 14B | 256K | ✅ | ✅ | ✅ | – | – | ★★★☆☆ Good (63) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| mistral | `ministral-14b-latest` | 14B | 256K | ✅ | ✅ | ✅ | – | – | ★★★☆☆ Good (63) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| mistral | `mistral-small-2603` | unknown | 256K | ✅ | ✅ | ✅ | – | – | ★★★☆☆ Good (62) | 44 | free tier | vision, extraction, agent, long_doc, fast |
| mistral | `mistral-small-latest` | unknown | 256K | ✅ | ✅ | ✅ | – | – | ★★★☆☆ Good (62) | 44 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-3.1-flash-lite` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★☆☆ Good (60) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-3.1-flash-lite-image` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★☆☆ Good (60) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-3.1-flash-lite-preview` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★☆☆ Good (60) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-3.5-flash-lite` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★☆☆ Good (60) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| gemini | `gemini-flash-lite-latest` | unknown | 1M≈ | ✅~ | ✅~ | ✅~ | – | – | ★★★☆☆ Good (60) | 49 | free tier | vision, extraction, agent, long_doc, fast |
| mistral | `ministral-8b-2512` | 8B | 256K | ✅ | ✅ | ✅ | – | – | ★★☆☆☆ Fair (55) | 55 | free tier | vision, extraction, agent, long_doc, fast |
| mistral | `ministral-8b-latest` | 8B | 256K | ✅ | ✅ | ✅ | – | – | ★★☆☆☆ Fair (55) | 55 | free tier | vision, extraction, agent, long_doc, fast |
| mistral | `magistral-medium-latest` | unknown | 256K | ✅ | ✅ | ✅ | – | ✅ | ★☆☆☆☆ Basic (40) | 44 | free tier | reasoning, vision, extraction, agent, long_doc |
| mistral | `magistral-small-latest` | unknown | 256K | ✅ | ✅ | ✅ | – | ✅ | ★☆☆☆☆ Basic (40) | 44 | free tier | reasoning, vision, extraction, agent, long_doc, fast |
| openrouter | `nvidia/nemotron-3.5-lightning:free` | unknown | 1.0M | ✅ | – | – | – | ✅ | ★☆☆☆☆ Basic (40) | 29 | price 0 | reasoning, agent, long_doc |
| openrouter | `thinkingmachines/inkling-small:free` | unknown | 1M | ✅ | – | ✅ | – | ✅ | ★☆☆☆☆ Basic (40) | 29 | price 0 | reasoning, vision, agent, long_doc, fast |
| openrouter | `thinkingmachines/inkling:free` | unknown | 1M | ✅ | – | ✅ | – | ✅ | ★☆☆☆☆ Basic (40) | 29 | price 0 | reasoning, vision, agent, long_doc |
| fastrouter | `fastrouter/auto` | unknown | 1.0M | – | – | ✅ | – | – | ★☆☆☆☆ Basic (35) | 39 | price 0 | vision, long_doc |
| fastrouter | `wanx/wan-v2-6` | unknown | 400K | – | – | ✅ | – | – | ★☆☆☆☆ Basic (35) | 39 | price 0 | vision, long_doc |
| mistral | `labs-leanstral-1-5` | unknown | 256K | ✅ | ✅ | ✅ | – | – | ★☆☆☆☆ Basic (35) | 44 | free tier | vision, extraction, agent, long_doc |
| mistral | `labs-leanstral-1-5-1` | unknown | 256K | ✅ | ✅ | ✅ | – | – | ★☆☆☆☆ Basic (35) | 44 | free tier | vision, extraction, agent, long_doc |
| mistral | `mistral-code-fim-latest` | unknown | 250K | ✅ | ✅ | – | ✅ | – | ★☆☆☆☆ Basic (35) | 44 | free tier | coding, extraction, agent, long_doc |
| mistral | `mistral-code-latest` | unknown | 250K | ✅ | ✅ | – | ✅ | – | ★☆☆☆☆ Basic (35) | 44 | free tier | coding, extraction, agent, long_doc |
| mistral | `mistral-vibe-cli-fast` | unknown | 256K | ✅ | ✅ | ✅ | – | – | ★☆☆☆☆ Basic (35) | 44 | free tier | vision, extraction, agent, long_doc, fast |
| mistral | `mistral-vibe-cli-latest` | unknown | 256K | ✅ | ✅ | ✅ | – | – | ★☆☆☆☆ Basic (35) | 44 | free tier | vision, extraction, agent, long_doc |
| mistral | `mistral-vibe-cli-with-tools` | unknown | 256K | ✅ | ✅ | ✅ | – | – | ★☆☆☆☆ Basic (35) | 44 | free tier | vision, extraction, agent, long_doc |
| openrouter | `apodex/apodex-1.1-mini:free` | unknown | 256K | ✅ | ✅ | – | – | – | ★☆☆☆☆ Basic (35) | 29 | price 0 | extraction, agent, long_doc, fast |
| openrouter | `cohere/north-mini-code:free` | unknown | 250K | ✅ | – | – | ✅ | – | ★☆☆☆☆ Basic (35) | 29 | price 0 | coding, agent, long_doc, fast |
| openrouter | `dots-studio/dots-3-note-preview:free` | unknown | 500K | ✅ | ✅ | ✅ | – | – | ★☆☆☆☆ Basic (35) | 29 | price 0 | vision, extraction, agent, long_doc |
| openrouter | `google/lyria-3-clip-preview` | unknown | 1M | – | ✅ | ✅ | – | – | ★☆☆☆☆ Basic (35) | 29 | price 0 | vision, extraction, long_doc |
| openrouter | `google/lyria-3-pro-preview` | unknown | 1M | – | ✅ | ✅ | – | – | ★☆☆☆☆ Basic (35) | 29 | price 0 | vision, extraction, long_doc |
| openrouter | `inclusionai/ling-3.1-flash` | unknown | 256K | ✅ | – | – | – | – | ★☆☆☆☆ Basic (35) | 29 | price 0 | agent, long_doc, fast |
| openrouter | `poolside/laguna-s-2.1:free` | unknown | 256K | ✅ | – | – | – | – | ★☆☆☆☆ Basic (35) | 29 | price 0 | agent, long_doc |
| openrouter | `poolside/laguna-xs-2.1:free` | unknown | 256K | ✅ | – | – | – | – | ★☆☆☆☆ Basic (35) | 29 | price 0 | agent, long_doc |

### Long context (32K - 200K), 17 models

| Gateway | Model | Size | Context | Tools | JSON | Vision | Code | Reasoning | Intelligence | Speed | Free type | Best for |
|---|---|---:|---:|:-:|:-:|:-:|:-:|:-:|---|---:|---|---|
| cerebras | `gpt-oss-120b` | 120B | 128K≈ | ✅~ | ✅~ | – | – | ✅~ | ★★★★★ Top (99) | 59 | free tier | reasoning, extraction, agent, long_doc |
| fastrouter | `openai/gpt-oss-120b:free` | 120B | 128K | ✅ | ✅ | – | – | ✅ | ★★★★★ Top (99) | 19 | price 0 | reasoning, extraction, agent, long_doc |
| groq | `openai/gpt-oss-120b` | 120B | 128K | ✅~ | ✅~ | – | – | ✅~ | ★★★★★ Top (99) | 54 | free tier | reasoning, extraction, agent, long_doc |
| fastrouter | `sarvam/sarvam-105b:free` | 105B | 125K | ✅ | – | – | – | – | ★★★★★ Top (92) | 20 | price 0 | agent, long_doc |
| fastrouter | `google/gemini-3-pro-image-preview` | unknown | 64K | – | ✅ | ✅ | – | – | ★★★★★ Top (90) | 39 | price 0 | vision, extraction, long_doc, fast |
| groq | `qwen/qwen3.8-27b` | 27B | 128K | ✅~ | ✅~ | – | – | ✅~ | ★★★★☆ Strong (78) | 71 | free tier | reasoning, extraction, agent, long_doc |
| fastrouter | `google/gemini-3.1-flash-image-preview` | unknown | 64K | – | ✅ | ✅ | – | – | ★★★★☆ Strong (75) | 39 | price 0 | vision, extraction, long_doc, fast |
| fastrouter | `openai/gpt-oss-20b:free` | 20B | 128K | ✅ | ✅ | – | – | ✅ | ★★★☆☆ Good (73) | 39 | price 0 | reasoning, extraction, agent, long_doc |
| groq | `openai/gpt-oss-20b` | 20B | 128K | ✅~ | ✅~ | – | – | ✅~ | ★★★☆☆ Good (73) | 74 | free tier | reasoning, extraction, agent, long_doc |
| fastrouter | `google/gemma-4-26b-a4b-it` | 26B | 128K | ✅ | – | ✅ | – | – | ★★★☆☆ Good (72) | 36 | price 0 | vision, agent, long_doc |
| cerebras | `llama3.1-8b` | 8B | 128K≈ | ✅~ | ✅~ | – | – | – | ★★☆☆☆ Fair (55) | 90 | free tier | extraction, agent, long_doc, fast |
| mistral | `ministral-3b-2512` | 3B | 128K | ✅ | ✅ | ✅ | – | – | ★☆☆☆☆ Basic (41) | 66 | free tier | vision, long_doc, fast |
| mistral | `ministral-3b-latest` | 3B | 128K | ✅ | ✅ | ✅ | – | – | ★☆☆☆☆ Basic (41) | 66 | free tier | vision, long_doc, fast |
| openrouter | `nvidia/nemotron-3.5-content-safety:free` | unknown | 125K | – | – | ✅ | – | ✅ | ★☆☆☆☆ Basic (40) | 29 | price 0 | reasoning, vision, long_doc |
| openrouter | `liquid/lfm-2.5-2.6b:free` | 2.6B | 64K | ✅ | ✅ | – | – | – | ★☆☆☆☆ Basic (39) | 53 | price 0 | long_doc, fast |
| fastrouter | `openai/gpt-live-1` | unknown | 125K | – | – | – | – | – | ★☆☆☆☆ Basic (35) | 39 | price 0 | long_doc |
| openrouter | `openrouter/free` | unknown | 200K | ✅ | ✅ | ✅ | – | – | ★☆☆☆☆ Basic (35) | 29 | price 0 | vision, extraction, agent, long_doc |

### Medium context (8K - 32K), 4 models

| Gateway | Model | Size | Context | Tools | JSON | Vision | Code | Reasoning | Intelligence | Speed | Free type | Best for |
|---|---|---:|---:|:-:|:-:|:-:|:-:|:-:|---|---:|---|---|
| cerebras | `qwen-3-32b` | 32B | 32K≈ | ✅~ | ✅~ | – | – | ✅~ | ★★★★☆ Strong (80) | 74 | free tier | reasoning, extraction, agent |
| fastrouter | `google/gemini-2.5-flash-image` | unknown | 32K | – | ✅ | ✅ | – | ✅ | ★★★★☆ Strong (80) | 39 | price 0 | reasoning, vision, extraction, fast |
| mistral | `voxtral-small-2507` | unknown | 32K | ✅ | ✅ | – | – | – | ★☆☆☆☆ Basic (35) | 44 | free tier | extraction, agent, fast |
| mistral | `voxtral-small-latest` | unknown | 32K | ✅ | ✅ | – | – | – | ★☆☆☆☆ Basic (35) | 44 | free tier | extraction, agent, fast |

### Short context (up to 8K), 10 models

| Gateway | Model | Size | Context | Tools | JSON | Vision | Code | Reasoning | Intelligence | Speed | Free type | Best for |
|---|---|---:|---:|:-:|:-:|:-:|:-:|:-:|---|---:|---|---|
| groq | `allam-2-7b` | 7B | 4K | ✅~ | ✅~ | – | – | – | ★★☆☆☆ Fair (53) | 87 | free tier | extraction, agent, fast |
| fastrouter | `alibaba/happyhorse-1.1` | unknown | 4K | – | – | ✅ | – | – | ★☆☆☆☆ Basic (35) | 39 | price 0 | vision |
| fastrouter | `bytedance/seedream-4.0` | unknown | 4K | – | – | – | – | – | ★☆☆☆☆ Basic (35) | 39 | price 0 | general |
| fastrouter | `bytedance/seedream-4.5` | unknown | 4K | – | – | – | – | – | ★☆☆☆☆ Basic (35) | 39 | price 0 | general |
| fastrouter | `deepgram/nova-3` | unknown | 4K | – | ✅ | – | – | – | ★☆☆☆☆ Basic (35) | 39 | price 0 | extraction |
| fastrouter | `leonardo-ai/lucid-origin` | unknown | 4K | – | – | – | – | – | ★☆☆☆☆ Basic (35) | 39 | price 0 | general |
| fastrouter | `leonardo-ai/lucid-realism` | unknown | 4K | – | – | – | – | – | ★☆☆☆☆ Basic (35) | 39 | price 0 | general |
| fastrouter | `leonardo-ai/phoenix` | unknown | 4K | – | – | – | – | – | ★☆☆☆☆ Basic (35) | 39 | price 0 | general |
| fastrouter | `wanx/wan-v2-7` | unknown | 4K | – | – | ✅ | – | – | ★☆☆☆☆ Basic (35) | 39 | price 0 | vision |
| fastrouter | `wanx/wan-v3-0` | unknown | 4K | – | – | ✅ | – | – | ★☆☆☆☆ Basic (35) | 39 | price 0 | vision |

### Unknown context (not reported), 83 models

| Gateway | Model | Size | Context | Tools | JSON | Vision | Code | Reasoning | Intelligence | Speed | Free type | Best for |
|---|---|---:|---:|:-:|:-:|:-:|:-:|:-:|---|---:|---|---|
| nvidia | `nvidia/llama-3.1-nemotron-ultra-253b-v1` | 253B | ? | ✅~ | ✅~ | – | – | ✅~ | ★★★★★ Top (100) | 5 | free tier | reasoning, extraction, agent |
| nvidia | `nvidia/nemotron-3-ultra-550b-a55b` | 550B | ? | ✅~ | ✅~ | – | – | ✅~ | ★★★★★ Top (100) | 5 | free tier | reasoning, extraction, agent |
| nvidia | `nvidia/nemotron-4-340b-instruct` | 340B | ? | ✅~ | ✅~ | – | – | ✅~ | ★★★★★ Top (100) | 5 | free tier | reasoning, extraction, agent |
| nvidia | `nvidia/nemotron-4-340b-reward` | 340B | ? | ✅~ | ✅~ | – | – | ✅~ | ★★★★★ Top (100) | 5 | free tier | reasoning, extraction, agent |
| nvidia | `nvidia/nemotron-3-super-120b-a12b` | 120B | ? | ✅~ | ✅~ | – | – | ✅~ | ★★★★★ Top (99) | 14 | free tier | reasoning, extraction, agent |
| nvidia | `mistralai/mixtral-8x22b-v0.1` | 176B | ? | ✅~ | ✅~ | – | – | – | ★★★★★ Top (95) | 9 | free tier | extraction, agent |
| nvidia | `writer/palmyra-creative-122b` | 122B | ? | ✅~ | ✅~ | – | – | – | ★★★★★ Top (94) | 14 | free tier | extraction, agent |
| nvidia | `nvidia/llama-3.1-nemotron-70b-instruct` | 70B | ? | ✅~ | ✅~ | – | – | ✅~ | ★★★★★ Top (91) | 20 | free tier | reasoning, extraction, agent |
| nvidia | `meta/llama-3.2-90b-vision-instruct` | 90B | ? | ✅~ | ✅~ | ✅~ | – | – | ★★★★★ Top (90) | 17 | free tier | vision, extraction, agent |
| nvidia | `nvidia/llama-3.1-nemotron-51b-instruct` | 51B | ? | ✅~ | ✅~ | – | – | ✅~ | ★★★★☆ Strong (87) | 24 | free tier | reasoning, extraction, agent |
| nvidia | `meta/codellama-70b` | 70B | ? | ✅~ | ✅~ | – | – | – | ★★★★☆ Strong (86) | 20 | free tier | extraction, agent |
| nvidia | `meta/llama2-70b` | 70B | ? | ✅~ | ✅~ | – | – | – | ★★★★☆ Strong (86) | 20 | free tier | extraction, agent |
| nvidia | `nvidia/llama3-chatqa-1.5-70b` | 70B | ? | ✅~ | ✅~ | – | – | – | ★★★★☆ Strong (86) | 20 | free tier | extraction, agent |
| nvidia | `writer/palmyra-fin-70b-32k` | 70B | ? | ✅~ | ✅~ | – | – | – | ★★★★☆ Strong (86) | 20 | free tier | extraction, agent |
| nvidia | `writer/palmyra-med-70b` | 70B | ? | ✅~ | ✅~ | – | – | – | ★★★★☆ Strong (86) | 20 | free tier | extraction, agent |
| nvidia | `writer/palmyra-med-70b-32k` | 70B | ? | ✅~ | ✅~ | – | – | – | ★★★★☆ Strong (86) | 20 | free tier | extraction, agent |
| nvidia | `mistralai/mistral-large` | unknown | ? | ✅~ | ✅~ | – | – | – | ★★★★☆ Strong (82) | 34 | free tier | extraction, agent |
| nvidia | `mistralai/mistral-large-2-instruct` | unknown | ? | ✅~ | ✅~ | – | – | – | ★★★★☆ Strong (82) | 34 | free tier | extraction, agent |
| nvidia | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | 30B | ? | ✅~ | ✅~ | – | – | ✅~ | ★★★★☆ Strong (79) | 30 | free tier | reasoning, extraction, agent, fast |
| nvidia | `nvidia/nemotron-3.5-lightning-30b-a3b` | 30B | ? | ✅~ | ✅~ | – | – | ✅~ | ★★★★☆ Strong (79) | 30 | free tier | reasoning, extraction, agent |
| nvidia | `nvidia/nemotron-nano-3-30b-a3b` | 30B | ? | ✅~ | ✅~ | – | – | ✅~ | ★★★★☆ Strong (79) | 30 | free tier | reasoning, extraction, agent, fast |
| nvidia | `ibm/granite-34b-code-instruct` | 34B | ? | ✅~ | ✅~ | – | ✅~ | – | ★★★★☆ Strong (76) | 28 | free tier | coding, extraction, agent |
| gemini | `gemma-4-31b-it` | 31B | ? | ✅~ | ✅~ | – | – | – | ★★★☆☆ Good (75) | 44 | free tier | extraction, agent |
| nvidia | `google/gemma-4-31b-it` | 31B | ? | ✅~ | ✅~ | – | – | – | ★★★☆☆ Good (75) | 29 | free tier | extraction, agent |
| nvidia | `nvidia/ising-calibration-1.5-31b` | 31B | ? | ✅~ | ✅~ | – | – | – | ★★★☆☆ Good (75) | 29 | free tier | extraction, agent |
| nvidia | `meta/muse-glimmer-30b` | 30B | ? | ✅~ | ✅~ | – | – | – | ★★★☆☆ Good (74) | 30 | free tier | extraction, agent |
| nvidia | `openai/gpt-oss-20b` | 20B | ? | ✅~ | ✅~ | – | – | ✅~ | ★★★☆☆ Good (73) | 34 | free tier | reasoning, extraction, agent |
| gemini | `gemma-4-26b-a4b-it` | 26B | ? | ✅~ | ✅~ | – | – | – | ★★★☆☆ Good (72) | 46 | free tier | extraction, agent |
| nvidia | `google/diffusiongemma-26b-a4b-it` | 26B | ? | ✅~ | ✅~ | – | – | – | ★★★☆☆ Good (72) | 31 | free tier | extraction, agent |
| nvidia | `mistralai/codestral-22b-instruct-v0.1` | 22B | ? | ✅~ | ✅~ | – | ✅~ | – | ★★★☆☆ Good (70) | 33 | free tier | coding, extraction, agent |
| nvidia | `nvidia/neva-22b` | 22B | ? | ✅~ | ✅~ | – | – | – | ★★★☆☆ Good (70) | 33 | free tier | extraction, agent |
| nvidia | `bigcode/starcoder2-15b` | 15B | ? | ✅~ | ✅~ | – | – | – | ★★★☆☆ Good (64) | 38 | free tier | extraction, agent |
| nvidia | `google/gemma-3-12b-it` | 12B | ? | ✅~ | ✅~ | ✅~ | – | – | ★★★☆☆ Good (61) | 40 | free tier | vision, extraction, agent, fast |
| nvidia | `nv-mistralai/mistral-nemo-12b-instruct` | 12B | ? | ✅~ | ✅~ | – | – | – | ★★★☆☆ Good (61) | 40 | free tier | extraction, agent, fast |
| nvidia | `meta/llama-3.2-11b-vision-instruct` | 11B | ? | ✅~ | ✅~ | ✅~ | – | – | ★★☆☆☆ Fair (60) | 41 | free tier | vision, extraction, agent, fast |
| nvidia | `adept/fuyu-8b` | 8B | ? | ✅~ | ✅~ | – | – | – | ★★☆☆☆ Fair (55) | 45 | free tier | extraction, agent, fast |
| nvidia | `ibm/granite-3.0-8b-instruct` | 8B | ? | ✅~ | ✅~ | – | – | – | ★★☆☆☆ Fair (55) | 45 | free tier | extraction, agent, fast |
| nvidia | `ibm/granite-8b-code-instruct` | 8B | ? | ✅~ | ✅~ | – | ✅~ | – | ★★☆☆☆ Fair (55) | 45 | free tier | coding, extraction, agent, fast |
| nvidia | `nvidia/cosmos-reason2-8b` | 8B | ? | ✅~ | ✅~ | – | – | – | ★★☆☆☆ Fair (55) | 45 | free tier | extraction, agent, fast |
| nvidia | `nvidia/mistral-nemo-minitron-8b-8k-instruct` | 8B | ? | ✅~ | ✅~ | – | – | – | ★★☆☆☆ Fair (55) | 45 | free tier | extraction, agent, fast |
| nvidia | `aisingapore/sea-lion-7b-instruct` | 7B | ? | ✅~ | ✅~ | – | – | – | ★★☆☆☆ Fair (53) | 47 | free tier | extraction, agent, fast |
| nvidia | `google/codegemma-1.1-7b` | 7B | ? | ✅~ | ✅~ | – | – | – | ★★☆☆☆ Fair (53) | 47 | free tier | extraction, agent, fast |
| nvidia | `google/codegemma-7b` | 7B | ? | ✅~ | ✅~ | – | – | – | ★★☆☆☆ Fair (53) | 47 | free tier | extraction, agent, fast |
| nvidia | `mistralai/mistral-7b-instruct-v0.3` | 7B | ? | ✅~ | ✅~ | – | – | – | ★★☆☆☆ Fair (53) | 47 | free tier | extraction, agent, fast |
| nvidia | `zyphra/zamba2-7b-instruct` | 7B | ? | ✅~ | ✅~ | – | – | – | ★★☆☆☆ Fair (53) | 47 | free tier | extraction, agent, fast |
| nvidia | `deepseek-ai/deepseek-coder-6.7b-instruct` | 6.7B | ? | – | ✅~ | – | ✅~ | – | ★★☆☆☆ Fair (52) | 47 | free tier | coding, fast |
| nvidia | `google/gemma-3-4b-it` | 4B | ? | – | ✅~ | ✅~ | – | – | ★★☆☆☆ Fair (45) | 53 | free tier | vision, fast |
| nvidia | `nvidia/riva-translate-4b-instruct` | 4B | ? | – | ✅~ | – | – | – | ★★☆☆☆ Fair (45) | 53 | free tier | fast |
| nvidia | `nvidia/riva-translate-4b-instruct-v2` | 4B | ? | – | ✅~ | – | – | – | ★★☆☆☆ Fair (45) | 53 | free tier | fast |
| nvidia | `ibm/granite-3.0-3b-a800m-instruct` | 3B | ? | – | ✅~ | – | – | – | ★☆☆☆☆ Basic (41) | 56 | free tier | fast |
| nvidia | `nvidia/nemotron-3.5-content-safety` | unknown | ? | ✅~ | ✅~ | – | – | ✅~ | ★☆☆☆☆ Basic (40) | 34 | free tier | reasoning, extraction, agent |
| nvidia | `nvidia/nemotron-parse` | unknown | ? | ✅~ | ✅~ | – | – | ✅~ | ★☆☆☆☆ Basic (40) | 34 | free tier | reasoning, extraction, agent |
| nvidia | `nvidia/nemotron-parse-2.0` | unknown | ? | ✅~ | ✅~ | – | – | ✅~ | ★☆☆☆☆ Basic (40) | 34 | free tier | reasoning, extraction, agent |
| fastrouter | `ace-step/prompt-to-audio` | unknown | ? | – | – | – | – | – | ★☆☆☆☆ Basic (35) | 39 | price 0 | general |
| gemini | `antigravity-preview-05-2026` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 49 | free tier | extraction, agent |
| gemini | `antigravity-preview-09-2026` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 49 | free tier | extraction, agent |
| gemini | `antigravity-preview-latest` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 49 | free tier | extraction, agent |
| gemini | `deep-research-max-preview-04-2026` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 49 | free tier | extraction, agent |
| gemini | `deep-research-preview-04-2026` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 49 | free tier | extraction, agent |
| gemini | `deep-research-pro-preview-12-2025` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 49 | free tier | extraction, agent |
| gemini | `lyria-3-clip-preview` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 49 | free tier | extraction, agent |
| gemini | `lyria-3-pro-preview` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 49 | free tier | extraction, agent |
| gemini | `lyria-3.5` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 49 | free tier | extraction, agent |
| gemini | `lyria-realtime-exp` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 49 | free tier | extraction, agent |
| gemini | `nano-banana-pro-preview` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 49 | free tier | extraction, agent, fast |
| nvidia | `01-ai/yi-large` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 34 | free tier | extraction, agent |
| nvidia | `ai21labs/jamba-1.5-large-instruct` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 34 | free tier | extraction, agent |
| nvidia | `databricks/dbrx-instruct` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 34 | free tier | extraction, agent |
| nvidia | `deepseek-ai/deepseek-v4.1-flash` | unknown | ? | ✅~ | ✅~ | – | ✅~ | – | ★☆☆☆☆ Basic (35) | 34 | free tier | coding, extraction, agent, fast |
| nvidia | `google/deplot` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 34 | free tier | extraction, agent |
| nvidia | `google/gemma-2b` | 2B | ? | – | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 61 | free tier | fast |
| nvidia | `google/recurrentgemma-2b` | 2B | ? | – | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 61 | free tier | fast |
| nvidia | `microsoft/kosmos-2` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 34 | free tier | extraction, agent |
| nvidia | `microsoft/phi-3-vision-128k-instruct` | unknown | ? | ✅~ | ✅~ | ✅~ | – | – | ★☆☆☆☆ Basic (35) | 34 | free tier | vision, extraction, agent |
| nvidia | `microsoft/phi-3.5-moe-instruct` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 34 | free tier | extraction, agent |
| nvidia | `moonshotai/kimi-k2.6` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 34 | free tier | extraction, agent |
| nvidia | `moonshotai/kimi-k3` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 34 | free tier | extraction, agent |
| nvidia | `nvidia/ai-synthetic-video-detector` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 34 | free tier | extraction, agent |
| nvidia | `nvidia/nvclip` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 34 | free tier | extraction, agent |
| nvidia | `nvidia/vila` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 34 | free tier | extraction, agent |
| nvidia | `poolside/laguna-xs-2.1` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 34 | free tier | extraction, agent |
| nvidia | `z-ai/glm-5.3` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 34 | free tier | extraction, agent |
| nvidia | `z-ai/glm-5.3-flash` | unknown | ? | ✅~ | ✅~ | – | – | – | ★☆☆☆☆ Basic (35) | 34 | free tier | extraction, agent, fast |

## 5. Last refresh: gateway health

| Gateway | Status | HTTP | Free models | Added | Removed | Error |
|---|---|---:|---:|---:|---:|---|
| openrouter | ok | 200 | 19 | 0 | 0 |  |
| groq | ok | 200 | 4 | 0 | 0 |  |
| cerebras | skipped | – | – | – | – | API key not configured |
| gemini | ok | 200 | 48 | 0 | 0 |  |
| mistral | ok | 200 | 27 | 0 | 0 |  |
| nvidia | ok | 200 | 69 | 0 | 0 |  |
| together | error | 401 | – | – | – | Client error '401 Unauthorized' for url 'https://api.together.xyz/v1/m |
| fireworks | skipped | – | – | – | – | API key not configured |
| tokenharbor | no_free_models | 200 | 0 | 0 | 0 |  |
| fastrouter | ok | 200 | 23 | 0 | 0 |  |

Full history: [refresh_log.jsonl](refresh_log.jsonl).

