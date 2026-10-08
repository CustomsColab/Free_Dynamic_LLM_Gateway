"""freellm.py - drop-in, quota-aware router over many free OpenAI-compatible LLM gateways.

Copy this ONE file into your app. It:
  * reads a registry (registry/models.json from your GitHub repo) of live free models,
  * picks the best model for a task (coding, extraction, long_doc, agent, vision, ...),
  * remembers which gateways / models are rate-limited TODAY and skips them,
  * falls over to the next free gateway automatically,
  * runs OpenAI-style function calling (tools) with a ready loop.

Env:
  FREELLM_REGISTRY_URL   raw.githubusercontent.com URL of registry/models.json
  FREELLM_REGISTRY_PATH  local registry file (alternative / extra fallback)
  FREELLM_STATE          ledger file (default .freellm_state.json) - share it between apps
  <GATEWAY>_API_KEY      one per gateway you use (see GATEWAYS below)

CLI:  python freellm.py status | pick --task coding | ask "hello"
"""
from __future__ import annotations

import asyncio
import inspect
import json
import math
import os
import re
import sys
import threading
import time
import typing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import httpx

__all__ = ["FreeLLM", "LLMResult", "tool", "ask", "get_llm", "AllModelsFailed"]

# --------------------------------------------------------------------------- #
# 1. Gateway configuration (shared by the refresh script and the app)
# --------------------------------------------------------------------------- #
# free_mode:   "price"     -> a model is free only if its listed input AND output price are 0
#              "free_tier" -> gateway has a rate-limited free plan; every chat model counts
# daily_scope: does a "requests per day" limit apply to the whole "gateway" or per "model"?
# limits:      APPROXIMATE published free-tier numbers - used only for load spreading.
#              The server's 429 / rate-limit headers are the real source of truth.
# speed_base:  rough relative inference speed of the gateway's hardware (0-100)
GATEWAYS: dict[str, dict] = {
    "openrouter": dict(base_url="https://openrouter.ai/api/v1", key_env="OPENROUTER_API_KEY",
                       free_mode="price", daily_scope="gateway", tools_default=False, speed_base=40,
                       limits=dict(rpm=20, rpd=50, approximate=True)),
    "groq":       dict(base_url="https://api.groq.com/openai/v1", key_env="GROQ_API_KEY",
                       free_mode="free_tier", daily_scope="model", tools_default=True, speed_base=85,
                       limits=dict(rpm=30, rpd=1000, approximate=True)),
    "cerebras":   dict(base_url="https://api.cerebras.ai/v1", key_env="CEREBRAS_API_KEY",
                       free_mode="free_tier", daily_scope="model", tools_default=True, speed_base=90,
                       limits=dict(rpm=30, rpd=14400, approximate=True)),
    "gemini":     dict(base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                       key_env="GEMINI_API_KEY", free_mode="free_tier", daily_scope="model",
                       tools_default=True, speed_base=60,
                       limits=dict(rpm=10, rpd=250, approximate=True)),
    "mistral":    dict(base_url="https://api.mistral.ai/v1", key_env="MISTRAL_API_KEY",
                       free_mode="free_tier", daily_scope="gateway", tools_default=True, speed_base=55,
                       limits=dict(rpm=60, rpd=None, approximate=True)),
    "nvidia":     dict(base_url="https://integrate.api.nvidia.com/v1", key_env="NVIDIA_API_KEY",
                       free_mode="free_tier", daily_scope="gateway", tools_default=True, speed_base=45,
                       limits=dict(rpm=40, rpd=None, approximate=True)),
    "together":   dict(base_url="https://api.together.xyz/v1", key_env="TOGETHER_API_KEY",
                       free_mode="price", daily_scope="gateway", tools_default=True, speed_base=55,
                       limits=dict(rpm=60, rpd=None, approximate=True)),
    "fireworks":  dict(base_url="https://api.fireworks.ai/inference/v1", key_env="FIREWORKS_API_KEY",
                       free_mode="price", daily_scope="gateway", tools_default=True, speed_base=65,
                       limits=dict(rpm=60, rpd=None, approximate=True)),
    # Token Harbor's own docs: GET https://tokenharbor.ai/v1/models (keys look like thk_live_...).
    # Its /models returns ids only - no prices - so none of its models can be detected as free.
    "tokenharbor": dict(base_url="https://tokenharbor.ai/v1", key_env="TOKEN_HARBOR_API_KEY",
                        free_mode="price", daily_scope="gateway", tools_default=False, speed_base=40,
                        limits=dict(rpm=None, rpd=None, approximate=True)),
    # FastRouter gives free starting CREDITS, not free models: only zero-priced models count as free.
    # To also spend those credits, create FreeLLM(allow_paid=True).
    "fastrouter": dict(base_url="https://api.fastrouter.ai/api/v1", key_env="FASTROUTER_API_KEY",
                       free_mode="price", daily_scope="gateway", tools_default=False, speed_base=50,
                       limits=dict(rpm=None, rpd=None, approximate=True)),
}


def all_gateways() -> dict[str, dict]:
    """Built-in gateways plus an optional 'custom' one from env (any OpenAI-compatible URL)."""
    gws = {k: dict(v) for k, v in GATEWAYS.items()}
    if os.getenv("CUSTOM_LLM_BASE_URL"):
        gws["custom"] = dict(base_url=os.environ["CUSTOM_LLM_BASE_URL"].rstrip("/"),
                             key_env="CUSTOM_LLM_API_KEY", free_mode="free_tier",
                             daily_scope="gateway", tools_default=True, speed_base=50,
                             limits=dict(rpm=None, rpd=None, approximate=True))
    return gws


# --------------------------------------------------------------------------- #
# 2. Registry enrichment: size, context, capabilities, categories
# --------------------------------------------------------------------------- #
NON_CHAT = ("embed", "whisper", "tts", "guard", "moderat", "rerank", "transcri", "imagen",
            "veo", "orpheus", "playai", "aqa", "dall-e", "stable-diffusion", "flux")
FAST_WORDS = {"instant", "flash", "lite", "mini", "turbo", "nano", "small", "haiku", "fast"}
# Used ONLY when the gateway does not report context. Deliberately tiny: free tiers often cap context
# below the model's native window (e.g. Cerebras), so guessing elsewhere would mislead.
CONTEXT_HINTS = [("gemini", r"gemini", 1_048_576)]   # (gateway, name pattern, tokens)
# Rough quality prior for models whose name carries no size ("7B"). Heuristics, not benchmarks.
FAMILY_QUALITY = [
    (r"gemini.*pro", 90), (r"gemini.*flash-lite", 60), (r"gemini.*flash", 75), (r"gemini", 70),
    (r"mistral-(large|medium)", 82), (r"mistral-small|ministral", 62), (r"codestral|devstral", 72),
    (r"qwen3-coder", 85),
]


def tokens(text: str) -> set[str]:
    return set(re.split(r"[^a-z0-9.]+", text.lower())) - {""}


def parse_size_b(text: str) -> Optional[float]:
    """'llama-3.3-70b' -> 70.0 ; 'mixtral-8x7b' -> 56.0 ; 'qwen3-30b-a3b' -> 30.0 ; unknown -> None."""
    t = text.lower()
    m = re.search(r"(?<![a-z0-9.])(\d+)x(\d+(?:\.\d+)?)b(?![a-z])", t)
    if m:
        return float(m.group(1)) * float(m.group(2))
    m = re.search(r"(?<![a-z0-9.])(\d+(?:\.\d+)?)b(?![a-z])", t)
    return float(m.group(1)) if m else None


def size_label(b: Optional[float]) -> str:
    if b is None:
        return "unknown"
    return f"{b:g}B"


def size_class(b: Optional[float]) -> str:
    if b is None:
        return "unknown"
    if b < 4:
        return "tiny"      # <4B
    if b <= 14:
        return "small"     # 4-14B  (7B, 8B, 9B ...)
    if b <= 40:
        return "medium"    # 15-40B (27B, 32B ...)
    if b <= 100:
        return "large"     # 41-100B (70B ...)
    return "xlarge"        # >100B


INTELLIGENCE_LABELS = {1: "Basic", 2: "Fair", 3: "Good", 4: "Strong", 5: "Top"}


def intelligence_tier(score: float) -> int:
    """1-5 tier from the 0-100 quality score (itself derived from model size).
    <45 Basic (~1-3B) | 45-59 Fair (~4-12B) | 60-74 Good (~13-30B) | 75-87 Strong (~32-100B) | 88+ Top (100B+ / frontier)."""
    return 1 if score < 45 else 2 if score < 60 else 3 if score < 75 else 4 if score < 88 else 5


def context_class(ctx: Optional[int]) -> str:
    if not ctx:
        return "unknown"
    if ctx <= 8_192:
        return "short"
    if ctx <= 32_768:
        return "medium"
    if ctx <= 200_000:
        return "long"
    return "ultra"


def _num(v: Any) -> Optional[float]:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def _int(v: Any) -> Optional[int]:
    try:
        return None if v is None else int(v)
    except (TypeError, ValueError):
        return None


def _price(row: dict, names: tuple[str, ...]) -> Optional[float]:
    pricing = row.get("pricing") or {}
    if isinstance(pricing, dict):
        for n in names:
            if n in pricing:
                return _num(pricing[n])
    return None


def normalize_row(gateway: str, cfg: dict, row: dict) -> Optional[dict]:
    """Turn one raw /models row into a registry entry (or None if it is not a chat model)."""
    raw_id = row.get("id") or row.get("name")
    if not raw_id or not isinstance(raw_id, str):
        return None
    model_id = raw_id[len("models/"):] if raw_id.startswith("models/") else raw_id
    low = model_id.lower()
    if any(w in low for w in NON_CHAT):
        return None
    rtype = str(row.get("type") or "").lower()
    if rtype in ("embedding", "embeddings", "image", "rerank", "audio", "moderation",
                 "transcribe", "video", "tts", "stt"):
        return None  # e.g. Together: embedding / image / rerank   (Mistral says "base": keep)
    declared_caps = row.get("capabilities") if isinstance(row.get("capabilities"), dict) else None
    if declared_caps is not None and "completion_chat" in declared_caps and not declared_caps["completion_chat"]:
        return None  # Mistral: embeddings / moderation / OCR models

    display = row.get("display_name") or row.get("name") or model_id
    text = f"{low} {str(display).lower()}"
    toks = tokens(text)
    size_b = parse_size_b(low) or parse_size_b(str(display))

    ctx = _int(row.get("context_length") or row.get("context_window")
               or row.get("max_context_length") or row.get("inputTokenLimit"))
    ctx_src = "api"
    if not ctx:
        ctx, ctx_src = None, "unknown"
        for gw, pat, val in CONTEXT_HINTS:
            if gw == gateway and re.search(pat, low):
                ctx, ctx_src = val, "hint"
                break

    # ---- free? -------------------------------------------------------------
    in_p = _price(row, ("prompt", "input"))
    out_p = _price(row, ("completion", "output"))
    if cfg.get("free_mode") == "free_tier":
        is_free, free_kind = True, "free_tier"
    else:
        is_free = (in_p == 0 and out_p == 0) or (gateway == "openrouter" and low.endswith(":free"))
        free_kind = "zero_price" if is_free else "paid"

    # ---- capabilities (declared when the API says so, otherwise inferred) ----
    declared = row.get("supported_parameters")
    arch = row.get("architecture") or {}
    modalities = arch.get("input_modalities") or []
    cap_src = "declared" if (declared is not None or "supports_tools" in row
                             or (declared_caps is not None and "function_calling" in declared_caps)) else "inferred"
    td = bool(cfg.get("tools_default")) and (size_b is None or size_b >= 7) and "r1" not in toks
    if declared is not None:
        tools = "tools" in declared or "tool_choice" in declared
        js = "response_format" in declared or "structured_outputs" in declared
    elif "supports_tools" in row:
        tools, js = bool(row["supports_tools"]), bool(row["supports_tools"])
    elif declared_caps is not None and "function_calling" in declared_caps:   # Mistral
        tools, js = bool(declared_caps["function_calling"]), True
    else:
        tools, js = td, bool(cfg.get("tools_default"))
    vision = ("image" in modalities or bool(row.get("supports_image_input"))
              or bool(declared_caps and declared_caps.get("vision"))
              or bool(toks & {"vision", "vl", "multimodal", "llava", "pixtral", "vlm"})
              or "gemini" in low or "llama-4" in low
              or ("gemma-3" in low and (size_b or 0) >= 4))
    coding = bool(toks & {"coder", "code", "codestral", "devstral", "coding"}) or "deepseek" in low
    reasoning = (bool(toks & {"r1", "reasoning", "reasoner", "think", "thinking", "qwq", "magistral"})
                 or "gpt-oss" in low or "qwen3" in low.replace("-", "") or "gemini-2.5" in low
                 or "nemotron" in low)
    caps = {"chat": True, "json": js, "tools": tools, "vision": vision,
            "coding": coding, "reasoning": reasoning}

    big_enough = size_b is None or size_b >= 7
    cats = ["general"]
    if coding:
        cats.append("coding")
    if reasoning:
        cats.append("reasoning")
    if vision:
        cats.append("vision")
    if js and big_enough:
        cats.append("extraction")
    if tools and big_enough:
        cats.append("agent")
    if ctx and ctx >= 64_000:
        cats.append("long_doc")
    if (size_b is not None and size_b <= 14) or toks & FAST_WORDS:
        cats.append("fast")

    if size_b is not None:
        q = min(95.0, 25 + 10 * math.log2(max(size_b, 1)))
    else:
        q = next((v for pat, v in FAMILY_QUALITY if re.search(pat, low)), 35)
        q = float(q)
    q += 5 if reasoning else 0
    sp = float(cfg.get("speed_base", 50)) - 8 * math.log2(max(size_b or 20, 1) / 8)

    return {
        "uid": f"{gateway}/{model_id}",
        "gateway": gateway,
        "model_id": model_id,
        "display_name": str(display),
        "kind": "chat",
        "size_b": size_b,
        "size_label": size_label(size_b),
        "size_class": size_class(size_b),
        "context_length": ctx,
        "context_class": context_class(ctx),
        "long_context": bool(ctx and ctx >= 64_000),
        "context_source": ctx_src,
        "is_free": is_free,
        "free_kind": free_kind,
        "input_price": in_p,
        "output_price": out_p,
        "capabilities": caps,
        "capability_source": cap_src,
        "categories": cats,
        "quality_hint": round(min(100.0, q)),
        "intelligence_tier": intelligence_tier(min(100.0, q)),
        "intelligence_label": INTELLIGENCE_LABELS[intelligence_tier(min(100.0, q))],
        "speed_hint": round(max(5.0, min(100.0, sp))),
        "status": "active",
        "available": True,
    }


# Starter list: used as the built-in fallback and to create the seed registry.
# Model catalogues change constantly - the scheduled refresh replaces these with live data.
SEED_MODELS: list[tuple[str, str, dict]] = [
    ("groq", "llama-3.3-70b-versatile", {"context_window": 131072}),
    ("groq", "llama-3.1-8b-instant", {"context_window": 131072}),
    ("groq", "openai/gpt-oss-120b", {"context_window": 131072}),
    ("groq", "openai/gpt-oss-20b", {"context_window": 131072}),
    ("groq", "qwen/qwen3-32b", {"context_window": 131072}),
    ("cerebras", "llama3.1-8b", {}),
    ("cerebras", "gpt-oss-120b", {}),
    ("cerebras", "qwen-3-32b", {}),
    ("gemini", "gemini-2.5-flash", {}),
    ("gemini", "gemini-2.5-flash-lite", {}),
    ("gemini", "gemini-2.5-pro", {}),
    ("openrouter", "meta-llama/llama-3.3-70b-instruct:free",
     {"context_length": 131072, "supported_parameters": ["tools", "tool_choice", "response_format"],
      "pricing": {"prompt": "0", "completion": "0"}}),
    ("openrouter", "qwen/qwen3-coder:free",
     {"context_length": 262144, "supported_parameters": ["tools", "tool_choice"],
      "pricing": {"prompt": "0", "completion": "0"}}),
    ("openrouter", "google/gemma-3-27b-it:free",
     {"context_length": 96000, "architecture": {"input_modalities": ["text", "image"]},
      "supported_parameters": ["response_format"], "pricing": {"prompt": "0", "completion": "0"}}),
    ("openrouter", "openai/gpt-oss-20b:free",
     {"context_length": 131072, "supported_parameters": ["tools", "tool_choice", "response_format"],
      "pricing": {"prompt": "0", "completion": "0"}}),
    ("mistral", "mistral-small-latest", {"context_length": 131072}),
    ("mistral", "mistral-large-latest", {"context_length": 131072}),
    ("nvidia", "meta/llama-3.3-70b-instruct", {}),
    ("nvidia", "meta/llama-3.1-8b-instruct", {}),
]


def seed_registry() -> dict:
    gws = all_gateways()
    models = []
    for g, mid, extra in SEED_MODELS:
        m = normalize_row(g, gws[g], {"id": mid, **extra})
        if m:
            m["source"] = "seed"
            models.append(m)
    return {"schema_version": 2, "source": "seed", "updated_at": _iso(time.time()),
            "gateways": public_gateways(gws), "models": models, "errors": []}


def public_gateways(gws: dict) -> dict:
    """Gateway block for the registry (no secrets - only the NAME of the env var)."""
    out = {}
    for name, c in gws.items():
        out[name] = {k: c[k] for k in ("base_url", "key_env", "free_mode", "daily_scope",
                                       "tools_default", "speed_base", "limits")}
        out[name]["rate_limit_exhausted_today"] = False  # live value comes from router.gateway_status()
    return out


# --------------------------------------------------------------------------- #
# 3. Time / rate-limit parsing helpers
# --------------------------------------------------------------------------- #
def _iso(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _day(epoch: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(epoch))


def next_utc_midnight(epoch: float) -> float:
    return (math.floor(epoch / 86400) + 1) * 86400


def parse_duration(v: Any) -> Optional[float]:
    """'30' -> 30 ; '2m59.56s' -> 179.56 ; '1h2m' -> 3720 ; '250ms' -> 0.25 ; else None."""
    if v is None:
        return None
    s = str(v).strip().lower()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        pass
    total, found = 0.0, False
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)(ms|h|m|s)", s):
        found = True
        total += float(num) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit]
    return total if found else None


DAILY_RE = re.compile(r"per.?day|perday|daily|free-models-per-day|\brpd\b|requests per day", re.I)


# --------------------------------------------------------------------------- #
# 4. Tool (function-calling) helpers
# --------------------------------------------------------------------------- #
_PYTYPES = {int: "integer", float: "number", bool: "boolean", str: "string", list: "array", dict: "object"}


def _json_type(tp: Any) -> dict:
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin is typing.Union:
        non_none = [a for a in args if a is not type(None)]
        return _json_type(non_none[0]) if non_none else {"type": "string"}
    if origin is typing.Literal:
        return {"type": "string", "enum": list(args)}
    if origin in (list, set, tuple):
        return {"type": "array", "items": _json_type(args[0]) if args else {}}
    if origin is dict:
        return {"type": "object"}
    return {"type": _PYTYPES.get(tp, "string")}


def tool(fn: Optional[Callable] = None, *, name: Optional[str] = None, description: Optional[str] = None):
    """Decorator: turns a typed Python function into an OpenAI tool schema (fn.schema)."""
    def wrap(f: Callable) -> Callable:
        sig = inspect.signature(f)
        try:
            hints = typing.get_type_hints(f)
        except Exception:
            hints = {}
        doc = inspect.getdoc(f) or ""
        arg_docs = dict(re.findall(r"^[ \t]*(\w+)[ \t]*(?:\([^)]*\))?:[ \t]*(\S.*)$", doc, re.M))
        props, required = {}, []
        for pname, p in sig.parameters.items():
            if pname in ("self", "cls") or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                continue
            prop = _json_type(hints.get(pname, str))
            if pname in arg_docs:
                prop["description"] = arg_docs[pname].strip()
            props[pname] = prop
            if p.default is inspect.Parameter.empty:
                required.append(pname)
        f.schema = {"type": "function", "function": {
            "name": name or f.__name__,
            "description": description or (doc.split("\n\n")[0].split("\nArgs:")[0].strip() or f.__name__),
            "parameters": {"type": "object", "properties": props, "required": required}}}
        f.tool_name = name or f.__name__
        return f
    return wrap(fn) if fn else wrap


# --------------------------------------------------------------------------- #
# 5. Results / errors
# --------------------------------------------------------------------------- #
@dataclass
class LLMResult:
    text: str
    message: dict
    gateway: str
    model_id: str
    usage: dict = field(default_factory=dict)
    attempts: list = field(default_factory=list)   # [(uid, "reason"), ...] for failed tries
    steps: list = field(default_factory=list)      # tool executions in run()

    @property
    def tool_calls(self) -> list:
        return self.message.get("tool_calls") or []

    def __str__(self) -> str:
        return self.text


class AllModelsFailed(RuntimeError):
    def __init__(self, attempts: list):
        self.attempts = attempts
        super().__init__("All candidate free models failed or are rate-limited: " +
                         "; ".join(f"{u}: {r}" for u, r in attempts[-8:]) if attempts else
                         "No usable free model (check API keys / registry / today's quotas)")


class _CallFailed(Exception):
    pass


# --------------------------------------------------------------------------- #
# 6. The router
# --------------------------------------------------------------------------- #
TASKS: dict[str, dict] = {
    "chat":       dict(cat="general"),
    "fast":       dict(cat="fast", prefer="speed"),
    "coding":     dict(cat="coding", prefer="quality"),
    "reasoning":  dict(cat="reasoning", prefer="quality"),
    "extraction": dict(cat="extraction", need_json=True),   # SQL / ontology / structured output
    "vision":     dict(cat="vision", need_vision=True),
    "long_doc":   dict(cat="long_doc", min_context=64_000),
    "agent":      dict(cat="agent", need_tools=True, prefer="quality"),
}
_WEIGHTS = {"balanced": (0.5, 0.5), "quality": (0.9, 0.1), "speed": (0.1, 0.9)}
AUTO_CONTEXT_MIN_TOKENS = 6_000   # above this, chat() filters out models with too small a context window


class FreeLLM:
    def __init__(self, registry: Optional[dict] = None, registry_url: Optional[str] = None,
                 registry_path: Optional[str] = None, cache_path: str = "freellm_registry_cache.json",
                 cache_ttl: int = 1800, state_path: Optional[str] = None, allow_paid: bool = False,
                 timeout: float = 60.0, clock: Callable[[], float] = time.time,
                 transport: Optional[httpx.BaseTransport] = None, max_attempts: int = 6,
                 strict_local_limits: bool = False, verbose: bool = False):
        self._given = registry
        self.registry_url = registry_url or os.getenv("FREELLM_REGISTRY_URL")
        self.registry_path = registry_path or os.getenv("FREELLM_REGISTRY_PATH")
        self.cache_path = Path(cache_path)
        self.cache_ttl = cache_ttl
        self.state_path = Path(state_path or os.getenv("FREELLM_STATE", ".freellm_state.json"))
        self.allow_paid = allow_paid
        self.timeout = timeout
        self.now = clock
        self.max_attempts = max_attempts
        self.strict_local_limits = strict_local_limits
        self.verbose = verbose
        self._client = httpx.Client(transport=transport, timeout=timeout)
        self._lock = threading.RLock()
        self._reg: dict = {}
        self._reg_loaded = 0.0
        self._state = self._load_state()

    # ---- registry ---------------------------------------------------------
    def _load_registry(self) -> dict:
        if self._given is not None:
            return self._given
        t = self.now()
        if self.cache_path.exists() and t - self.cache_path.stat().st_mtime < self.cache_ttl:
            try:
                return json.loads(self.cache_path.read_text("utf-8"))
            except Exception:
                pass
        if self.registry_url:
            try:
                r = self._client.get(self.registry_url, timeout=15)
                r.raise_for_status()
                reg = r.json()
                self.cache_path.write_text(json.dumps(reg), "utf-8")
                return reg
            except Exception as e:
                self._log(f"registry fetch failed: {e}")
        for p in (self.cache_path, self.registry_path):
            if p and Path(p).exists():
                try:
                    return json.loads(Path(p).read_text("utf-8"))
                except Exception:
                    continue
        return seed_registry()

    @property
    def registry(self) -> dict:
        with self._lock:
            if not self._reg or self.now() - self._reg_loaded > self.cache_ttl:
                self._reg = self._load_registry()
                self._reg_loaded = self.now()
            return self._reg

    def refresh_registry(self) -> None:
        self._reg = {}

    def _gw(self, name: str) -> dict:
        base = all_gateways().get(name, {})
        over = (self.registry.get("gateways") or {}).get(name, {})
        merged = {**base, **{k: v for k, v in over.items() if k != "rate_limit_exhausted_today"}}
        return merged

    def _key(self, gateway: str) -> str:
        env = self._gw(gateway).get("key_env") or ""
        return os.getenv(env, "") if env else ""

    # ---- state ledger -----------------------------------------------------
    def _load_state(self) -> dict:
        st = {"day": _day(self.now()), "gateways": {}, "models": {}}
        try:
            if self.state_path.exists():
                st.update(json.loads(self.state_path.read_text("utf-8")))
        except Exception:
            pass
        return st

    def _save(self) -> None:
        try:
            tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
            tmp.write_text(json.dumps(self._state), "utf-8")
            os.replace(tmp, self.state_path)
        except Exception:
            pass

    def _roll_day(self) -> None:
        today = _day(self.now())
        if self._state.get("day") != today:
            self._state = {"day": today, "gateways": {}, "models": {}}
            self._save()

    def _g(self, gateway: str) -> dict:
        return self._state["gateways"].setdefault(
            gateway, {"used": 0, "exhausted_until": 0, "reason": "", "recent_429": []})

    def _m(self, uid: str) -> dict:
        return self._state["models"].setdefault(
            uid, {"used": 0, "cooldown_until": 0, "exhausted_until": 0, "reason": "", "fails": 0})

    def _gateway_blocked(self, gateway: str) -> Optional[str]:
        g = self._state["gateways"].get(gateway)
        if g and g["exhausted_until"] > self.now():
            return g["reason"] or "exhausted"
        return None

    def _model_blocked(self, uid: str) -> Optional[str]:
        m = self._state["models"].get(uid)
        if not m:
            return None
        t = self.now()
        if m["exhausted_until"] > t:
            return m["reason"] or "daily limit"
        if m["cooldown_until"] > t:
            return m["reason"] or "cooling down"
        return None

    def _remaining_fraction(self, gateway: str, uid: str) -> float:
        rpd = (self._gw(gateway).get("limits") or {}).get("rpd")
        if not rpd:
            return 1.0
        scope = self._gw(gateway).get("daily_scope", "model")
        used = self._g(gateway)["used"] if scope == "gateway" else self._m(uid)["used"]
        return max(0.0, 1.0 - used / rpd)

    # ---- selection --------------------------------------------------------
    def candidates(self, task: str = "chat", *, need_tools: Optional[bool] = None,
                   need_json: Optional[bool] = None, need_vision: Optional[bool] = None,
                   min_context: Optional[int] = None, context: Optional[str] = None,
                   min_size_b: Optional[float] = None, max_size_b: Optional[float] = None,
                   min_intelligence: Optional[int] = None, prefer: Optional[str] = None, gateways: Optional[list] = None,
                   exclude: Optional[list] = None, explain: bool = False) -> list[dict]:
        """Ranked list of usable models for a task. Skips exhausted/cooling gateways and models."""
        with self._lock:
            self._roll_day()
            spec = TASKS.get(task, TASKS["chat"])
            need_tools = spec.get("need_tools", False) if need_tools is None else need_tools
            need_json = spec.get("need_json", False) if need_json is None else need_json
            need_vision = spec.get("need_vision", False) if need_vision is None else need_vision
            needs = [x for x in (min_context, spec.get("min_context")) if x]   # task floor is never lowered
            min_context = max(needs) if needs else None
            if context == "long":
                min_context = max(min_context or 0, 64_000)
            wq, ws = _WEIGHTS[prefer or spec.get("prefer", "balanced")]
            out = []
            for m in self.registry.get("models", []):
                if m.get("kind", "chat") != "chat" or m.get("status", "active") != "active":
                    continue
                if not m.get("available", True) or (not m.get("is_free") and not self.allow_paid):
                    continue
                g, uid = m["gateway"], m["uid"]
                if gateways and g not in gateways:
                    continue
                if exclude and (g in exclude or uid in exclude):
                    continue
                if not self._key(g):
                    continue
                if self._gateway_blocked(g) or self._model_blocked(uid):
                    continue
                if self.strict_local_limits and self._remaining_fraction(g, uid) <= 0:
                    continue
                caps = m.get("capabilities", {})
                if (need_tools and not caps.get("tools")) or (need_json and not caps.get("json")) \
                        or (need_vision and not caps.get("vision")):
                    continue
                ctx = m.get("context_length")
                if min_context and (not ctx or ctx < min_context):
                    continue
                sb = m.get("size_b")
                if min_size_b and (sb is None or sb < min_size_b):
                    continue
                if max_size_b and sb is not None and sb > max_size_b:
                    continue
                if min_intelligence and m.get("intelligence_tier", intelligence_tier(m.get("quality_hint", 0))) \
                        < min_intelligence:
                    continue
                score = 100.0 if spec.get("cat") in m.get("categories", []) else 0.0
                score += wq * m.get("quality_hint", 40) + ws * m.get("speed_hint", 40)
                score += 30 * self._remaining_fraction(g, uid)          # spread load across free quotas
                score -= 15 * min(self._m(uid)["fails"], 3)             # recent trouble
                score += min((ctx or 0) / 100_000, 5)
                row = dict(m)
                row["score"] = round(score, 1)
                out.append(row)
            out.sort(key=lambda r: r["score"], reverse=True)
            return out

    # ---- calling ----------------------------------------------------------
    @staticmethod
    def estimate_tokens(messages: list, tools: Optional[list] = None, max_tokens: Optional[int] = None) -> int:
        """Cheap size estimate (about 4 characters per token) of prompt + tools + reply budget."""
        chars = 0
        for m in messages:
            c = m.get("content") if isinstance(m, dict) else m
            if isinstance(c, str):
                chars += len(c)
            elif isinstance(c, list):
                chars += sum(len(p["text"]) for p in c if isinstance(p, dict) and isinstance(p.get("text"), str))
            if isinstance(m, dict) and m.get("tool_calls"):
                chars += len(json.dumps(m["tool_calls"]))
        if tools:
            chars += len(json.dumps(tools))
        return chars // 4 + (max_tokens or 1024)

    def chat(self, messages: list | str, *, task: str = "chat", tools: Optional[list] = None,
             tool_choice: Any = None, response_format: Optional[dict] = None,
             temperature: Optional[float] = None, max_tokens: Optional[int] = None,
             extra: Optional[dict] = None, auto_context: bool = True, **filters) -> LLMResult:
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        if tools:
            filters.setdefault("need_tools", True)
        if response_format:
            filters.setdefault("need_json", True)
        need = self.estimate_tokens(messages, tools, max_tokens)
        auto_set = False
        if auto_context and not filters.get("min_context") and need > AUTO_CONTEXT_MIN_TOKENS:
            # big prompt: only consider models whose context window can hold it (+15% margin)
            filters["min_context"] = int(need * 1.15)
            auto_set = True
        cands = self.candidates(task, **filters)
        if not cands and auto_set:
            raise AllModelsFailed([("(router)", f"prompt needs ~{need:,} tokens of context but no usable free model "
                                                f"has {filters['min_context']:,}+ (models with unknown context are "
                                                f"skipped for big prompts). Shorten the input or pass auto_context=False")])
        attempts: list = []
        tried = 0
        for m in cands:
            if tried >= self.max_attempts:
                break
            with self._lock:
                if self._gateway_blocked(m["gateway"]) or self._model_blocked(m["uid"]):
                    continue  # got blocked by an earlier failure in this very loop
            tried += 1
            body: dict = {"model": m["model_id"], "messages": messages}
            if tools:
                body["tools"] = tools
                if tool_choice is not None:
                    body["tool_choice"] = tool_choice
            if response_format:
                body["response_format"] = response_format
            if temperature is not None:
                body["temperature"] = temperature
            if max_tokens is not None:
                body["max_tokens"] = max_tokens
            if extra:
                body.update(extra)
            try:
                return self._call(m, body, attempts)
            except _CallFailed as e:
                attempts.append((m["uid"], str(e)))
                self._log(f"failed {m['uid']}: {e}")
        raise AllModelsFailed(attempts)

    def _call(self, m: dict, body: dict, attempts: list) -> LLMResult:
        g, uid = m["gateway"], m["uid"]
        cfg = self._gw(g)
        url = f"{cfg['base_url'].rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self._key(g)}", "Content-Type": "application/json"}
        with self._lock:
            self._g(g)["used"] += 1
            self._m(uid)["used"] += 1
            self._save()
        try:
            r = self._client.post(url, json=body, headers=headers)
        except httpx.HTTPError as e:
            self._on_error(m, 599, {}, f"network: {e}")
            raise _CallFailed(f"network error: {type(e).__name__}")
        status, text = r.status_code, r.text
        data: Any = None
        if status == 200:
            try:
                data = r.json()
            except Exception:
                status, text = 502, "invalid JSON from gateway"
        if status == 200 and isinstance(data, dict) and not data.get("choices"):
            err = data.get("error") or {}
            code = err.get("code") if isinstance(err, dict) else None
            status = code if isinstance(code, int) and code >= 400 else 502
            text = json.dumps(data)[:500]
        if status != 200:
            self._on_error(m, status, dict(r.headers), text)
            raise _CallFailed(f"HTTP {status}")
        self._on_success(m, dict(r.headers))
        msg = data["choices"][0].get("message") or {}
        return LLMResult(text=msg.get("content") or "", message=msg, gateway=g,
                         model_id=m["model_id"], usage=data.get("usage") or {}, attempts=list(attempts))

    # ---- state transitions -----------------------------------------------
    def _on_success(self, m: dict, headers: dict) -> None:
        with self._lock:
            self._m(m["uid"])["fails"] = 0
            h = {k.lower(): v for k, v in headers.items()}
            rem = h.get("x-ratelimit-remaining-requests-day") or h.get("x-ratelimit-remaining-requests")
            if rem is not None and str(rem).strip() == "0":     # last request in the window - stop early
                reset = parse_duration(h.get("x-ratelimit-reset-requests-day")
                                       or h.get("x-ratelimit-reset-requests"))
                if reset and reset > 900:
                    self._exhaust(m, min(self.now() + reset, self.now() + 86400), "daily quota used up (headers)")
                else:
                    self._m(m["uid"]).update(cooldown_until=self.now() + (reset or 30),
                                             reason="per-minute window used up")
            self._save()

    def _exhaust(self, m: dict, until: float, reason: str) -> None:
        g, uid = m["gateway"], m["uid"]
        scope = self._gw(g).get("daily_scope", "model")
        if scope == "gateway":
            self._g(g).update(exhausted_until=until, reason=reason)
        else:
            self._m(uid).update(exhausted_until=until, reason=reason)
            limited = [k for k, v in self._state["models"].items()
                       if k.startswith(g + "/") and v["exhausted_until"] > self.now()]
            if len(limited) >= 3:   # several models daily-limited -> assume the whole key is spent
                self._g(g).update(exhausted_until=until, reason="auto: 3+ models hit daily limit")

    def _on_error(self, m: dict, status: int, headers: dict, text: str) -> None:
        with self._lock:
            t, g, uid = self.now(), m["gateway"], m["uid"]
            h = {k.lower(): v for k, v in headers.items()}
            ms = self._m(uid)
            ms["fails"] += 1
            snippet = re.sub(r"\s+", " ", text)[:120]
            if status == 429:
                ra = parse_duration(h.get("retry-after"))
                reset = parse_duration(h.get("x-ratelimit-reset-requests"))
                xr = _num(h.get("x-ratelimit-reset"))          # OpenRouter: epoch milliseconds
                if xr and xr > 1e12:
                    reset = max(0.0, xr / 1000 - t)
                wait = ra or reset
                rem = str(h.get("x-ratelimit-remaining-requests", "")).strip()
                daily = bool(DAILY_RE.search(text)) or bool(wait and wait > 900) \
                    or (rem == "0" and bool(reset and reset > 900))
                if daily:
                    until = min(t + wait, t + 86400) if wait and wait > 900 else next_utc_midnight(t)
                    self._exhaust(m, until, f"daily limit (429)")
                else:
                    gs = self._g(g)
                    gs["recent_429"] = [x for x in gs["recent_429"] if t - x < 60] + [t]
                    ms.update(cooldown_until=t + (wait or 30), reason="per-minute limit (429)")
                    if len(gs["recent_429"]) >= 3:
                        gs.update(exhausted_until=t + max(wait or 0, 60), reason="burst of 429s")
            elif status == 401:
                self._g(g).update(exhausted_until=t + 3600, reason="auth failed (check API key)")
            elif status == 402:
                self._g(g).update(exhausted_until=next_utc_midnight(t), reason="credits/payment required")
            elif status == 404:
                ms.update(cooldown_until=t + 86400, reason="model not found (removed?)")
            elif status in (400, 422):
                ms.update(cooldown_until=t + 300, reason=f"bad request: {snippet}")
            else:
                ms.update(cooldown_until=t + min(900, 30 * 2 ** min(ms["fails"], 5)), reason=f"HTTP {status}")
            self._save()

    # ---- function calling loop -------------------------------------------
    def run(self, messages: list | str, tools: list[Callable], *, task: str = "agent",
            max_steps: int = 6, system: Optional[str] = None, **kw) -> LLMResult:
        """Chat + automatic tool execution. `tools` are functions decorated with @tool."""
        msgs = [{"role": "user", "content": messages}] if isinstance(messages, str) else list(messages)
        if system:
            msgs.insert(0, {"role": "system", "content": system})
        tmap = {getattr(f, "tool_name", f.__name__): f for f in tools}
        schemas = [f.schema for f in tools]
        steps: list = []
        res: Optional[LLMResult] = None
        for _ in range(max_steps):
            res = self.chat(msgs, task=task, tools=schemas, tool_choice="auto", **kw)
            calls = res.tool_calls
            if not calls:
                res.steps = steps
                return res
            msgs.append({"role": "assistant", "content": res.message.get("content") or "", "tool_calls": calls})
            for c in calls:
                fn = c.get("function", {})
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                    out = tmap[name](**args) if name in tmap else {"error": f"unknown tool {name}"}
                except Exception as e:  # tell the model, let it recover
                    out = {"error": f"{type(e).__name__}: {e}"}
                content = out if isinstance(out, str) else json.dumps(out, default=str)
                steps.append({"tool": name, "arguments": fn.get("arguments"), "result": content[:500]})
                msgs.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": content[:20000]})
        assert res is not None
        res.steps = steps
        res.text = res.text or "(stopped: max tool steps reached)"
        return res

    async def achat(self, *a, **kw) -> LLMResult:
        return await asyncio.to_thread(self.chat, *a, **kw)

    async def arun(self, *a, **kw) -> LLMResult:
        return await asyncio.to_thread(self.run, *a, **kw)

    # ---- visibility -------------------------------------------------------
    def gateway_status(self) -> dict:
        """Per-gateway YES/NO 'rate limit exhausted today', plus counts and reset time."""
        with self._lock:
            self._roll_day()
            names = list((self.registry.get("gateways") or all_gateways()).keys())
            out = {}
            for g in names:
                models = [m for m in self.registry.get("models", [])
                          if m["gateway"] == g and m.get("is_free") and m.get("status", "active") == "active"]
                usable = [m for m in models if not self._model_blocked(m["uid"])]
                gs = self._g(g)
                blocked = self._gateway_blocked(g)
                exhausted = bool(blocked) or (bool(models) and not usable)
                until = gs["exhausted_until"] if blocked else max(
                    [self._m(m["uid"])["exhausted_until"] for m in models] or [0])
                out[g] = {
                    "configured": bool(self._key(g)),
                    "rate_limit_exhausted_today": ("yes" if exhausted else "no") if self._key(g) else "n/a (no key)",
                    "reason": blocked or ("all free models limited" if exhausted else ""),
                    "resets_at_utc": _iso(until) if exhausted and until > self.now() else None,
                    "requests_today": gs["used"],
                    "free_models": len(models), "usable_now": len(usable)}
            return out

    def live_registry(self) -> dict:
        """The registry with today's live overlay: gateway yes/no flag + usable_now per model."""
        reg = json.loads(json.dumps(self.registry))
        st = self.gateway_status()
        for g, v in (reg.get("gateways") or {}).items():
            v["rate_limit_exhausted_today"] = st.get(g, {}).get("rate_limit_exhausted_today", "n/a")
        for m in reg.get("models", []):
            m["usable_now"] = bool(self._key(m["gateway"])) and not self._gateway_blocked(m["gateway"]) \
                and not self._model_blocked(m["uid"])
        return reg

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[freellm] {msg}", file=sys.stderr)


# --------------------------------------------------------------------------- #
# 7. Module-level shortcuts + CLI
# --------------------------------------------------------------------------- #
_default: Optional[FreeLLM] = None


def get_llm(**kw) -> FreeLLM:
    global _default
    if _default is None or kw:
        _default = FreeLLM(**kw)
    return _default


def ask(prompt: str, *, task: str = "chat", system: Optional[str] = None, **kw) -> str:
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    return get_llm().chat(msgs, task=task, **kw).text


def _cli(argv: list[str]) -> None:
    llm = FreeLLM(verbose=True)
    cmd = argv[0] if argv else "status"
    if cmd == "status":
        for g, v in llm.gateway_status().items():
            print(f"{g:12} exhausted_today={v['rate_limit_exhausted_today']:12} "
                  f"used={v['requests_today']:<5} usable={v['usable_now']}/{v['free_models']}  {v['reason']}")
    elif cmd == "pick":
        task = argv[argv.index("--task") + 1] if "--task" in argv else "chat"
        for r in llm.candidates(task)[:10]:
            print(f"{r['score']:6} {r['uid']:55} {r['size_label']:>6} {r['context_class']:8} {r['categories']}")
    elif cmd == "ask":
        print(ask(" ".join(argv[1:]) or "Say hello in five words."))
    else:
        print(__doc__)


if __name__ == "__main__":
    _cli(sys.argv[1:])
