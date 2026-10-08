"""Render registry/models.json as tables that are easy to read on GitHub.

    python scripts/render_tables.py                 # regenerate from registry/models.json

Writes next to the registry:
  MODELS.md    GitHub shows it as formatted tables (free + active models only)
  models.csv   GitHub shows it as a table; open in Excel/Sheets to sort and filter (all models)

Called automatically by refresh_registry.py after every refresh.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import freellm  # noqa: E402

CLASS_ORDER = ["ultra", "long", "medium", "short", "unknown"]
CLASS_GUIDE = {
    "ultra":   ("over 200K", "~150K+ words", "whole books, huge codebases, dozens of documents at once",
                "Few models (mostly Gemini). Slowest, and free token-per-minute limits bite first"),
    "long":    ("32K - 200K", "~25K-150K words", "long reports, contracts, notices, big code files, many RAG chunks",
                "Task `long_doc` picks from here. Send only what you need: quality drops near the limit"),
    "medium":  ("8K - 32K", "~6K-25K words", "RAG answers with a few chunks, one document, code review",
                "Good default for most apps"),
    "short":   ("up to 8K", "up to ~6K words", "chat, classification, SQL/JSON generation, short Q&A",
                "Fastest and cheapest on quota. Use task `fast`"),
    "unknown": ("not reported", "?", "treat as short until tested",
                "The gateway does not report context length and no safe default is known"),
}
TASK_USE = {
    "chat": "general questions and writing", "fast": "quick, cheap, short calls",
    "coding": "write / fix code", "reasoning": "multi-step logic, maths, planning",
    "extraction": "JSON, SQL, ontology / structured output", "vision": "images and screenshots",
    "long_doc": "documents over ~50 pages (needs 64K+ context)", "agent": "function calling / tools",
}


def fmt_ctx(ctx, src: str = "api") -> str:
    if not ctx:
        return "?"
    if ctx >= 1_000_000:
        s = f"{ctx / 1_048_576:.0f}M" if ctx % 1024 == 0 else f"{ctx / 1e6:.1f}M"
    elif ctx % 1024 == 0:
        s = f"{ctx // 1024}K"
    else:
        s = f"{round(ctx / 1000)}K"
    return s + ("≈" if src == "hint" else "")


def mark(m: dict, cap: str) -> str:
    if not m["capabilities"].get(cap):
        return "–"
    return "✅" if m.get("capability_source") == "declared" else "✅~"


def tier_of(m: dict) -> int:
    return m.get("intelligence_tier") or freellm.intelligence_tier(m.get("quality_hint", 0))


def stars(m: dict) -> str:
    t = tier_of(m)
    return f"{'★' * t}{'☆' * (5 - t)} {freellm.INTELLIGENCE_LABELS[t]} ({m.get('quality_hint', 0)})"


def esc(s: str) -> str:
    return str(s).replace("|", "\\|")


def top_picks(models: list[dict], n: int = 3) -> dict[str, list[dict]]:
    """Static ranking per task (same scoring idea as the router, minus live quota state)."""
    out = {}
    for task, spec in freellm.TASKS.items():
        wq, ws = freellm._WEIGHTS[spec.get("prefer", "balanced")]
        rows = []
        for m in models:
            c = m["capabilities"]
            if (spec.get("need_tools") and not c["tools"]) or (spec.get("need_json") and not c["json"]) \
                    or (spec.get("need_vision") and not c["vision"]):
                continue
            mc = spec.get("min_context")
            if mc and (not m.get("context_length") or m["context_length"] < mc):
                continue
            score = (100 if spec["cat"] in m["categories"] else 0) + wq * m["quality_hint"] + ws * m["speed_hint"]
            rows.append((score, m))
        rows.sort(key=lambda r: -r[0])
        out[task] = [m for _, m in rows[:n]]
    return out


def render_markdown(registry: dict) -> str:
    models = [m for m in registry.get("models", []) if m.get("is_free") and m.get("status", "active") == "active"]
    gateways = sorted({m["gateway"] for m in models})
    by_class = {c: [m for m in models if m["context_class"] == c] for c in CLASS_ORDER}
    L: list[str] = []
    a = L.append
    a("# Free LLM models: decision tables")
    a("")
    a(f"Updated **{registry.get('updated_at', '?')}** | source: **{registry.get('source', '?')}** | "
      f"**{len(models)}** free models on **{len(gateways)}** gateways")
    a("")
    a("> Generated file. Do not edit by hand: it is rebuilt after every registry refresh. "
      "Spreadsheet version: [models.csv](models.csv).")
    a("")
    a("## 1. Which context size do I need?")
    a("")
    a("| Class | Tokens | About | Use it for | Notes | Models |")
    a("|---|---|---|---|---|---|")
    for c in CLASS_ORDER:
        rng, words, use, note = CLASS_GUIDE[c]
        a(f"| **{c}** | {rng} | {words} | {use} | {note} | {len(by_class[c])} |")
    a("")
    a("Rule of thumb: 1 token is about 4 characters, or 0.75 English words. Your app can leave this decision to "
      "the router: it estimates the prompt size and skips models whose context is too small "
      "(`auto_context`, on by default).")
    a("")
    a("## 2. At a glance: free models per gateway and context class")
    a("")
    a("| Gateway | ultra | long | medium | short | unknown | Total |")
    a("|---|---:|---:|---:|---:|---:|---:|")
    for g in gateways:
        counts = [sum(1 for m in by_class[c] if m["gateway"] == g) for c in CLASS_ORDER]
        a(f"| {g} | " + " | ".join(str(x) if x else "–" for x in counts) + f" | **{sum(counts)}** |")
    a("")
    a("Free models by **intelligence** and context class (pick the row you need, then the context you need):")
    a("")
    a("| Intelligence | ultra | long | medium | short | unknown | Total |")
    a("|---|---:|---:|---:|---:|---:|---:|")
    for t in (5, 4, 3, 2, 1):
        counts = [sum(1 for m in by_class[c] if tier_of(m) == t) for c in CLASS_ORDER]
        label = f"{'★' * t}{'☆' * (5 - t)} {freellm.INTELLIGENCE_LABELS[t]}"
        a(f"| {label} | " + " | ".join(str(x) if x else "–" for x in counts) + f" | **{sum(counts)}** |")
    a("")
    a("## 3. Best picks per task")
    a("")
    a("Static ranking (quality, speed, capabilities). Live quota and rate-limit state is applied by the router at call time.")
    a("")
    a("| Task | Use when | #1 | #2 | #3 |")
    a("|---|---|---|---|---|")
    picks = top_picks(models)
    for task, rows in picks.items():
        cells = [f"`{esc(m['uid'])}` ({m['size_label']}, {fmt_ctx(m['context_length'], m['context_source'])}, "
                 f"{freellm.INTELLIGENCE_LABELS[tier_of(m)]})"
                 for m in rows]
        cells += ["–"] * (3 - len(cells))
        a(f"| **{task}** | {TASK_USE[task]} | " + " | ".join(cells) + " |")
    a("")
    a("## 4. All free models, grouped by context class")
    a("")
    a("Legend: ✅ declared by the gateway | ✅~ inferred from the name (not declared) | – not supported / unknown | "
      "≈ context length is a built-in estimate because the gateway does not report it. "
      "**Intelligence** is a 1-5 rating derived from model size (parameters), with family estimates for models "
      "that publish no size (Gemini, Mistral Large...) and a small bonus for reasoning models; the number in brackets is the 0-100 score. "
      "Tiers: Basic (~1-3B), Fair (~4-12B), Good (~13-30B), Strong (~32-100B), Top (100B+ / frontier). "
      "Size is only a rough proxy: newer small models can beat older big ones, and for mixture-of-experts models "
      "the size shown is the total, not what runs per token. Speed is a 0-100 heuristic. Neither is a benchmark.")
    for c in CLASS_ORDER:
        rows = sorted(by_class[c], key=lambda m: (-m["quality_hint"], m["uid"]))
        if not rows:
            continue
        rng = CLASS_GUIDE[c][0]
        a("")
        a(f"### {c.capitalize()} context ({rng}), {len(rows)} models")
        a("")
        a("| Gateway | Model | Size | Context | Tools | JSON | Vision | Code | Reasoning | Intelligence | Speed | Free type | Best for |")
        a("|---|---|---:|---:|:-:|:-:|:-:|:-:|:-:|---|---:|---|---|")
        for m in rows:
            best = ", ".join(x for x in m["categories"] if x != "general") or "general"
            ftype = "free tier" if m["free_kind"] == "free_tier" else "price 0"
            a(f"| {m['gateway']} | `{esc(m['model_id'])}` | {m['size_label']} | "
              f"{fmt_ctx(m['context_length'], m['context_source'])} | {mark(m, 'tools')} | {mark(m, 'json')} | "
              f"{mark(m, 'vision')} | {mark(m, 'coding')} | {mark(m, 'reasoning')} | {stars(m)} | "
              f"{m['speed_hint']} | {ftype} | {best} |")
    a("")
    last = registry.get("last_refresh") or {}
    if last.get("gateways"):
        a("## 5. Last refresh: gateway health")
        a("")
        a("| Gateway | Status | HTTP | Free models | Added | Removed | Error |")
        a("|---|---|---:|---:|---:|---:|---|")
        for g, v in last["gateways"].items():
            a(f"| {g} | {v['status']} | {v['http_status'] or '–'} | "
              f"{v['free_models'] if v['free_models'] is not None else '–'} | {v.get('added_count', '–')} | "
              f"{v.get('removed_count', '–')} | {esc((v.get('error') or '')[:70])} |")
        a("")
        a("Full history: [refresh_log.jsonl](refresh_log.jsonl).")
        a("")
    return "\n".join(L)


CSV_COLS = ["gateway", "model_id", "size_b", "size_class", "context_length", "context_class", "long_context",
            "is_free", "free_kind", "tools", "json", "vision", "coding", "reasoning", "categories",
            "intelligence_tier", "intelligence_label", "quality_hint", "speed_hint", "capability_source", "context_source", "status", "first_seen"]


def write_csv(registry: dict, path: Path) -> None:
    models = sorted(registry.get("models", []),
                    key=lambda m: (not m.get("is_free"), freellm_class_rank(m), -m.get("quality_hint", 0), m["uid"]))
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_COLS)
        for m in models:
            c = m["capabilities"]
            w.writerow([m["gateway"], m["model_id"], m.get("size_b") or "", m["size_class"],
                        m.get("context_length") or "", m["context_class"], m["long_context"],
                        m["is_free"], m["free_kind"], c["tools"], c["json"], c["vision"], c["coding"],
                        c["reasoning"], " ".join(m["categories"]), tier_of(m),
                        freellm.INTELLIGENCE_LABELS[tier_of(m)], m["quality_hint"], m["speed_hint"],
                        m.get("capability_source", ""), m.get("context_source", ""),
                        m.get("status", "active"), m.get("first_seen", "")])


def freellm_class_rank(m: dict) -> int:
    c = m.get("context_class", "unknown")
    return CLASS_ORDER.index(c) if c in CLASS_ORDER else len(CLASS_ORDER)


def write_tables(registry: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "MODELS.md").write_text(render_markdown(registry) + "\n", "utf-8")
    write_csv(registry, out_dir / "models.csv")


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("registry/models.json")
    registry = json.loads(src.read_text("utf-8"))
    write_tables(registry, src.parent)
    print(f"Wrote {src.parent / 'MODELS.md'} and {src.parent / 'models.csv'}")


if __name__ == "__main__":
    main()
