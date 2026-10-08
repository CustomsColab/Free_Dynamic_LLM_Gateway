import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import freellm  # noqa: E402
from freellm import FreeLLM, AllModelsFailed, tool  # noqa: E402

HOST_TO_GW = {"api.groq.com": "groq", "api.cerebras.ai": "cerebras", "openrouter.ai": "openrouter"}


def ok(text="hi", tool_calls=None, headers=None):
    msg = {"role": "assistant", "content": text}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return httpx.Response(200, json={"choices": [{"message": msg}], "usage": {"total_tokens": 5}},
                          headers=headers or {})


class Env:
    """Fake clock + scripted gateways."""

    def __init__(self):
        self.t = 1_800_000_000.0  # fixed 'now'
        self.calls: list[tuple[str, str]] = []
        self.script: dict[str, list] = {}   # gateway -> list of responses/callables (last one repeats)

    def handler(self, request: httpx.Request) -> httpx.Response:
        gw = HOST_TO_GW[request.url.host]
        model = json.loads(request.content)["model"]
        self.calls.append((gw, model))
        queue = self.script.get(gw, [ok()])
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        return item(request) if callable(item) else item

    def llm(self, registry=None, **kw) -> FreeLLM:
        d = tempfile.mkdtemp()
        return FreeLLM(registry=registry or make_registry(), state_path=f"{d}/state.json",
                       clock=lambda: self.t, transport=httpx.MockTransport(self.handler), **kw)


def make_registry():
    gws = freellm.all_gateways()
    rows = [
        ("groq", {"id": "llama-3.3-70b-versatile", "context_window": 131072}),
        ("groq", {"id": "llama-3.1-8b-instant", "context_window": 131072}),
        ("groq", {"id": "qwen-2.5-coder-32b", "context_window": 32768}),
        ("cerebras", {"id": "gpt-oss-120b", "context_window": 131072}),
        ("openrouter", {"id": "meta/some-8b:free", "context_length": 4096,
                        "pricing": {"prompt": "0", "completion": "0"}}),
        ("openrouter", {"id": "vendor/paid-70b", "context_length": 65536,
                        "pricing": {"prompt": "0.001", "completion": "0.002"}}),
        ("groq", {"id": "whisper-large-v3"}),
    ]
    models = [m for g, r in rows if (m := freellm.normalize_row(g, gws[g], r))]
    return {"schema_version": 2, "gateways": freellm.public_gateways(gws), "models": models}


class TestEnrichment(unittest.TestCase):
    def test_size_parsing(self):
        p = freellm.parse_size_b
        self.assertEqual(p("llama-3.3-70b-versatile"), 70)
        self.assertEqual(p("mixtral-8x7b-instruct"), 56)
        self.assertEqual(p("qwen3-30b-a3b"), 30)
        self.assertEqual(p("gpt-oss-120b"), 120)
        self.assertEqual(p("gemma-3-27b-it:free"), 27)
        self.assertEqual(p("Llama-3.1-8B-Instant"), 8)
        self.assertIsNone(p("gemini-2.5-flash"))
        self.assertIsNone(p("gemma-3n-e4b-it"))

    def test_classes(self):
        self.assertEqual(freellm.size_class(7), "small")
        self.assertEqual(freellm.size_class(70), "large")
        self.assertEqual(freellm.size_class(None), "unknown")
        self.assertEqual(freellm.context_class(4096), "short")
        self.assertEqual(freellm.context_class(131072), "long")
        self.assertEqual(freellm.context_class(1_000_000), "ultra")

    def test_free_detection_and_filtering(self):
        by = {m["uid"]: m for m in make_registry()["models"]}
        self.assertTrue(by["openrouter/meta/some-8b:free"]["is_free"])
        self.assertFalse(by["openrouter/vendor/paid-70b"]["is_free"])
        self.assertTrue(by["groq/llama-3.3-70b-versatile"]["is_free"])          # free_tier gateway
        self.assertNotIn("groq/whisper-large-v3", by)                           # non-chat dropped
        m = by["groq/llama-3.3-70b-versatile"]
        self.assertEqual((m["size_label"], m["size_class"], m["context_class"], m["long_context"]),
                         ("70B", "large", "long", True))
        self.assertEqual(by["openrouter/meta/some-8b:free"]["context_class"], "short")
        self.assertIn("coding", by["groq/qwen-2.5-coder-32b"]["categories"])

    def test_gemini_prefix_stripped(self):
        m = freellm.normalize_row("gemini", freellm.GATEWAYS["gemini"], {"id": "models/gemini-2.5-flash"})
        self.assertEqual(m["model_id"], "gemini-2.5-flash")
        self.assertEqual(m["context_source"], "hint")


class TestRouting(unittest.TestCase):
    def setUp(self):
        os.environ.update(GROQ_API_KEY="k", CEREBRAS_API_KEY="k", OPENROUTER_API_KEY="k")
        self.env = Env()

    def test_task_selection(self):
        llm = self.env.llm()
        self.assertEqual(llm.candidates("coding")[0]["model_id"], "qwen-2.5-coder-32b")
        self.assertEqual(llm.candidates("fast")[0]["model_id"], "llama-3.1-8b-instant")
        long_doc = llm.candidates("long_doc")
        self.assertTrue(all(m["context_length"] >= 64000 for m in long_doc))
        self.assertNotIn("openrouter/vendor/paid-70b", [m["uid"] for m in llm.candidates("chat")])  # paid excluded

    def test_missing_key_skips_gateway(self):
        del os.environ["CEREBRAS_API_KEY"]
        try:
            llm = self.env.llm()
            self.assertNotIn("cerebras", {m["gateway"] for m in llm.candidates("chat")})
        finally:
            os.environ["CEREBRAS_API_KEY"] = "k"

    def test_daily_429_exhausts_and_skips_without_calling(self):
        # openrouter's daily limit is gateway-wide: one 429 must park the whole gateway
        self.env.script["openrouter"] = [httpx.Response(429, text="free-models-per-day limit exceeded")]
        llm = self.env.llm(registry=only(make_registry(), "openrouter", "cerebras"))
        res = llm.chat("hi", task="fast")                      # openrouter 8B ranks first for 'fast'
        self.assertEqual([g for g, _ in self.env.calls], ["openrouter", "cerebras"])
        self.assertEqual(res.gateway, "cerebras")
        self.assertEqual(llm.gateway_status()["openrouter"]["rate_limit_exhausted_today"], "yes")
        self.env.calls.clear()
        llm.chat("again", task="fast")
        self.assertEqual([g for g, _ in self.env.calls], ["cerebras"])   # zero calls wasted on openrouter

    def test_fallback_and_gateway_yes_flag(self):
        # groq daily-limited on every model -> router moves on to cerebras, status says yes for groq
        self.env.script["groq"] = [httpx.Response(429, text="Rate limit reached ... requests per day (RPD)",
                                                  headers={"retry-after": "7200"})]
        llm = self.env.llm()
        # task="fast" ranks groq's 8B first, so groq is tried first and must fail over
        res = llm.chat("hi", task="fast", gateways=["groq", "cerebras"])
        self.assertEqual(res.gateway, "cerebras")
        self.assertTrue(any(u.startswith("groq/") for u, _ in res.attempts))
        # only the 8B is known-limited so far: lazy discovery, status still "no"
        self.assertEqual(llm.gateway_status()["groq"]["rate_limit_exhausted_today"], "no")
        with self.assertRaises(AllModelsFailed):          # force-try the rest of groq
            llm.chat("hi", gateways=["groq"])
        self.assertEqual(llm.gateway_status()["groq"]["rate_limit_exhausted_today"], "yes")
        self.assertEqual(llm.gateway_status()["cerebras"]["rate_limit_exhausted_today"], "no")
        self.env.calls.clear()
        llm.chat("hi")
        self.assertNotIn("groq", [g for g, _ in self.env.calls])

    def test_minute_429_is_short_cooldown(self):
        self.env.script["groq"] = [httpx.Response(429, text="rate limit", headers={"retry-after": "10"}), ok()]
        llm = self.env.llm(registry=only(make_registry(), "groq"))
        first = llm.candidates("fast")[0]["uid"]
        res = llm.chat("hi", task="fast")
        self.assertNotEqual(f"groq/{res.model_id}", first)          # moved to another groq model
        self.assertEqual(llm.gateway_status()["groq"]["rate_limit_exhausted_today"], "no")
        self.assertNotIn(first, [m["uid"] for m in llm.candidates("fast")])
        self.env.t += 11
        self.assertIn(first, [m["uid"] for m in llm.candidates("fast")])  # cooldown expired

    def test_404_disables_model_for_a_day(self):
        self.env.script["groq"] = [httpx.Response(404, text="model not found"), ok()]
        llm = self.env.llm(registry=only(make_registry(), "groq"))
        first = llm.candidates("chat")[0]["uid"]
        llm.chat("hi")
        self.env.t += 3600 * 5
        self.assertNotIn(first, [m["uid"] for m in llm.candidates("chat")])

    def test_header_remaining_zero_marks_exhausted(self):
        self.env.script["groq"] = [ok(headers={"x-ratelimit-remaining-requests": "0",
                                               "x-ratelimit-reset-requests": "3h"})]
        llm = self.env.llm(registry=only(make_registry(), "groq"))
        first = llm.candidates("chat")[0]["uid"]
        llm.chat("hi")
        self.assertNotIn(first, [m["uid"] for m in llm.candidates("chat")])

    def test_day_rollover_resets(self):
        self.env.script["groq"] = [httpx.Response(402, text="payment required")]
        llm = self.env.llm(registry=only(make_registry(), "groq"))
        with self.assertRaises(AllModelsFailed):
            llm.chat("hi")
        self.assertEqual(llm.gateway_status()["groq"]["rate_limit_exhausted_today"], "yes")
        self.env.t += 86400 + 5
        self.assertEqual(llm.gateway_status()["groq"]["rate_limit_exhausted_today"], "no")
        self.assertTrue(llm.candidates("chat"))

    def test_state_persists_between_instances(self):
        self.env.script["groq"] = [httpx.Response(402, text="payment required")]
        d = tempfile.mkdtemp()
        mk = lambda: FreeLLM(registry=only(make_registry(), "groq"), state_path=f"{d}/s.json",
                             clock=lambda: self.env.t, transport=httpx.MockTransport(self.env.handler))
        a = mk()
        with self.assertRaises(AllModelsFailed):
            a.chat("hi")
        self.assertEqual(mk().candidates("chat"), [])

    def test_all_fail_raises_with_attempts(self):
        self.env.script["groq"] = [httpx.Response(500, text="boom")]
        llm = self.env.llm(registry=only(make_registry(), "groq"))
        with self.assertRaises(AllModelsFailed) as cm:
            llm.chat("hi")
        self.assertTrue(cm.exception.attempts)


def only(reg, *gateways):
    return {**reg, "models": [m for m in reg["models"] if m["gateway"] in gateways]}


class TestTools(unittest.TestCase):
    def setUp(self):
        os.environ.update(GROQ_API_KEY="k", CEREBRAS_API_KEY="k", OPENROUTER_API_KEY="k")
        self.env = Env()

    def test_schema_generation(self):
        @tool
        def get_gst_rate(hsn_code: str, intra_state: bool = True, qty: Optional[int] = None):
            """Look up the GST rate for an HSN code.

            Args:
                hsn_code: 4 to 8 digit HSN code
                intra_state: true for CGST+SGST
            """
        p = get_gst_rate.schema["function"]
        self.assertEqual(p["name"], "get_gst_rate")
        self.assertEqual(p["description"], "Look up the GST rate for an HSN code.")
        self.assertEqual(p["parameters"]["required"], ["hsn_code"])
        self.assertEqual(p["parameters"]["properties"]["intra_state"]["type"], "boolean")
        self.assertEqual(p["parameters"]["properties"]["qty"]["type"], "integer")
        self.assertEqual(p["parameters"]["properties"]["hsn_code"]["description"], "4 to 8 digit HSN code")

    def test_tool_loop(self):
        seen = {}

        @tool
        def add(a: int, b: int) -> int:
            """Add two numbers."""
            seen["args"] = (a, b)
            return a + b

        def respond(request):
            body = json.loads(request.content)
            if any(m["role"] == "tool" for m in body["messages"]):
                tool_msg = [m for m in body["messages"] if m["role"] == "tool"][0]
                return ok(f"answer={tool_msg['content']}")
            assert body["tools"][0]["function"]["name"] == "add"
            return ok("", tool_calls=[{"id": "c1", "type": "function",
                                       "function": {"name": "add", "arguments": '{"a": 2, "b": 3}'}}])

        self.env.script["groq"] = [respond]
        llm = self.env.llm(registry=only(make_registry(), "groq"))
        res = llm.run("what is 2+3?", [add])
        self.assertEqual(seen["args"], (2, 3))
        self.assertEqual(res.text, "answer=5")
        self.assertEqual(res.steps[0]["tool"], "add")

    def test_tool_error_is_reported_to_model(self):
        @tool
        def boom(x: int) -> int:
            """Fail."""
            raise ValueError("nope")

        def respond(request):
            msgs = json.loads(request.content)["messages"]
            t = [m for m in msgs if m["role"] == "tool"]
            if t:
                return ok("saw:" + t[0]["content"])
            return ok("", tool_calls=[{"id": "c", "type": "function",
                                       "function": {"name": "boom", "arguments": '{"x": 1}'}}])

        self.env.script["groq"] = [respond]
        llm = self.env.llm(registry=only(make_registry(), "groq"))
        self.assertIn("ValueError", llm.run("go", [boom]).text)

    def test_tools_require_tool_capable_models(self):
        reg = make_registry()
        for m in reg["models"]:
            if m["uid"] == "groq/llama-3.1-8b-instant":
                m["capabilities"]["tools"] = False
        llm = self.env.llm(registry=reg)
        self.assertNotIn("groq/llama-3.1-8b-instant", [m["uid"] for m in llm.candidates("agent")])


class TestRefreshMerge(unittest.TestCase):
    def test_merge_keeps_failed_gateway_and_marks_missing(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
        import refresh_registry as rr
        reg = make_registry()["models"]
        now = 1_800_000_000.0
        fresh = {"groq": [m for m in reg if m["gateway"] == "groq" and m["model_id"] != "llama-3.1-8b-instant"]}
        merged = {m["uid"]: m for m in rr.merge(reg, fresh, now)}
        self.assertEqual(merged["groq/llama-3.1-8b-instant"]["status"], "missing")
        self.assertFalse(merged["groq/llama-3.1-8b-instant"]["available"])
        self.assertEqual(merged["cerebras/gpt-oss-120b"]["status"], "active")   # gateway not refreshed -> kept
        later = rr.merge(list(merged.values()), fresh, now + 5 * 86400)
        self.assertNotIn("groq/llama-3.1-8b-instant", [m["uid"] for m in later])  # pruned after 3 days


class TestRefreshLog(unittest.TestCase):
    def test_record_log_and_table(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
        import refresh_registry as rr
        reg = make_registry()["models"]
        groq = [m for m in reg if m["gateway"] == "groq"]
        results = [
            {"gateway": "groq", "models": groq[:-1], "listed": 9, "http_status": 200, "latency_ms": 120,
             "status": "ok", "error": None},
            {"gateway": "gemini", "models": None, "listed": 0, "http_status": 401, "latency_ms": 80,
             "status": "error", "error": "401 Unauthorized"},
            {"gateway": "mistral", "models": None, "listed": 0, "http_status": None, "latency_ms": None,
             "status": "skipped", "error": "API key not configured"},
        ]
        rec = rr.build_record(results, reg, 1_800_000_000.0)
        self.assertEqual((rec["ok"], rec["failed"], rec["skipped"]), (1, 1, 1))
        self.assertEqual(rec["gateways"]["groq"]["removed_count"], 1)
        self.assertEqual(rec["gateways"]["groq"]["added_count"], 0)
        self.assertEqual(rec["gateways"]["gemini"]["http_status"], 401)
        self.assertIn("gemini", rr.render_table(rec))
        self.assertIn("| groq |", rr.render_table(rec, markdown=True))
        d = tempfile.mkdtemp()
        log = Path(d) / "log.jsonl"
        for _ in range(5):
            rr.append_log(log, rec, keep=3)
        lines = log.read_text().splitlines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(json.loads(lines[-1])["failed"], 1)


if __name__ == "__main__":
    unittest.main()
