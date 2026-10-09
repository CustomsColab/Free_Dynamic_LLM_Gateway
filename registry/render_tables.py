"""Render registry/models.json as tables that are easy to read on GitHub.

    python scripts/render_tables.py                 # regenerate from registry/models.json

Writes next to the registry:
  MODELS.md    GitHub shows it as formatted tables (free + active models only)
  models.csv   GitHub shows it as a table: free models only, same model clubbed across gateways,
               ordered by intelligence, vision specialists below, emoji colour markers
  models.xlsx  same table with real cell colours and filters (needs openpyxl)

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
      "Grouped, colour-coded decision table: [models.csv](models.csv) (view on GitHub) and [models.xlsx](models.xlsx) (download, real colours + filters).")
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


# --------------------------------------------------------------------------- #
# Decision table: models.csv (plain, emoji colour markers) + models.xlsx (real colours)
#   * free + active models only
#   * the same model offered by several gateways is clubbed into one group (adjacent rows)
#   * groups ordered by intelligence (highest first), then context, then name
#   * vision-specialist models are listed in a separate block BELOW the main table
# --------------------------------------------------------------------------- #
import re  # noqa: E402

TIER_EMOJI = {5: "🟣", 4: "🟢", 3: "🔵", 2: "🟡", 1: "🔴"}
CTX_EMOJI = {"ultra": "🔵", "long": "🟢", "medium": "🟡", "short": "🟠", "unknown": "⚪"}
CTX_LABEL = {"ultra": "Ultra (>200K)", "long": "Long (32K-200K)", "medium": "Medium (8K-32K)",
             "short": "Short (<=8K)", "unknown": "Unknown"}
TIER_FILL = {5: "D5B8EA", 4: "C6EFCE", 3: "DDEBF7", 2: "FFF2CC", 1: "F8CBAD"}
CTX_FILL = {"ultra": "A9D6F5", "long": "C6EFCE", "medium": "FFF2CC", "short": "F8CBAD", "unknown": "D9D9D9"}

# Names containing one of these tokens are treated as vision-SPECIALISTS (listed below the main table).
# General multimodal models (Gemini, Gemma 3, Pixtral, Llama 4...) are NOT matched: they stay on top.
VISION_SPECIALIST_TOKENS = {"vl", "vlm", "vision", "llava", "paligemma", "florence", "neva", "vila", "kosmos",
                            "ocr", "cogvlm", "internvl", "molmo", "fuyu", "idefics", "image"}
# Words dropped when deciding that two gateways serve "the same model".
_DROP_WORDS = {"instruct", "it", "versatile", "instant", "latest", "fp8", "bf16", "awq", "int4", "free"}

COLUMNS = ["Rank", "Model", "Intelligence", "Tier (1-5)", "Size", "Gateway", "Gateway model id",
           "Context class", "Context (tokens)", "Modality", "Tools", "JSON", "Reasoning", "Coding",
           "Speed (0-100)", "Free type", "Best for", "Gateways in group"]
COL_IDX = {name: i for i, name in enumerate(COLUMNS)}


def canonical_key(model_id: str) -> str:
    """Key under which the same model on different gateways collapses together.
    'openai/gpt-oss-120b:free' == 'gpt-oss-120b';  'llama3.1-8b' == 'meta/llama-3.1-8b-instruct' == 'llama-3.1-8b-instant';
    'qwen-3-32b' == 'qwen/qwen3-32b'.  'flash' and 'flash-lite' stay different."""
    s = model_id.lower().split(":")[0].rsplit("/", 1)[-1]
    parts = [p for p in re.split(r"[-_]", s) if p and p not in _DROP_WORDS]
    return "".join(re.sub(r"[^a-z0-9]", "", p) for p in parts)


def clean_name(model_id: str) -> str:
    return model_id.split(":")[0].rsplit("/", 1)[-1]


def is_vision_specialist(model_id: str) -> bool:
    return bool(set(re.split(r"[^a-z0-9]+", model_id.lower())) & VISION_SPECIALIST_TOKENS)


def yes(m: dict, cap: str) -> str:
    if not m["capabilities"].get(cap):
        return "No"
    return "Yes" if m.get("capability_source") == "declared" else "Yes~"


def build_groups(registry: dict) -> tuple[list[dict], list[dict]]:
    """Return (main_groups, vision_groups), each already sorted; every group has its rows ready."""
    models = [m for m in registry.get("models", []) if m.get("is_free") and m.get("status", "active") == "active"]
    by_key: dict[str, list[dict]] = {}
    for m in models:
        by_key.setdefault(canonical_key(m["model_id"]), []).append(m)
    groups = []
    for key, ms in by_key.items():
        names = [clean_name(m["model_id"]) for m in ms]
        vendor_named = [clean_name(m["model_id"]) for m in ms if "/" in m["model_id"]]   # 'meta/llama-...' = official spelling
        display = sorted(set(names), key=lambda n: (-(2 * vendor_named.count(n) + names.count(n)), len(n), n))[0]
        sizes = [m["size_b"] for m in ms if m.get("size_b")]
        groups.append({
            "key": key, "display": display, "models": ms,
            "tier": max(tier_of(m) for m in ms),
            "quality": max(m.get("quality_hint", 0) for m in ms),
            "ctx_max": max((m.get("context_length") or 0) for m in ms),
            "size": f"{max(sizes):g}B" if sizes else "unknown",
            "vision_only": any(is_vision_specialist(m["model_id"]) for m in ms),
        })
    order = lambda g: (-g["tier"], -g["quality"], -g["ctx_max"], g["display"])
    main = sorted((g for g in groups if not g["vision_only"]), key=order)
    vis = sorted((g for g in groups if g["vision_only"]), key=order)
    for g in main + vis:
        g["models"].sort(key=lambda m: (-(m.get("context_length") or 0), -m.get("speed_hint", 0), m["gateway"]))
    return main, vis


def group_rows(groups: list[dict]) -> list[list]:
    """Flat list of table rows (plain values, no emoji). Each row also carries its group index at the end."""
    rows = []
    for rank, g in enumerate(groups, 1):
        for m in g["models"]:
            modality = ("Vision specialist" if g["vision_only"]
                        else "Text + Vision" if m["capabilities"].get("vision") else "Text")
            best = ", ".join(x for x in m["categories"] if x != "general") or "general"
            rows.append([rank, g["display"], freellm.INTELLIGENCE_LABELS[g["tier"]], g["tier"], g["size"],
                         m["gateway"], m["model_id"], m["context_class"], m.get("context_length") or "",
                         modality, yes(m, "tools"), yes(m, "json"), yes(m, "reasoning"), yes(m, "coding"),
                         m.get("speed_hint", ""), "Free tier" if m["free_kind"] == "free_tier" else "Price 0",
                         best, len(g["models"])])
    return rows


def csv_cells(row: list) -> list:
    """Same row with colour-marker emoji so the CSV is readable on GitHub / Excel without real colours."""
    r = list(row)
    r[COL_IDX["Intelligence"]] = f"{TIER_EMOJI[row[COL_IDX['Tier (1-5)']]]} {row[COL_IDX['Intelligence']]}"
    cls = row[COL_IDX["Context class"]]
    r[COL_IDX["Context class"]] = f"{CTX_EMOJI[cls]} {CTX_LABEL[cls]}"
    return r


VISION_BANNER = "VISION-SPECIALIST MODELS (image models, listed separately; skip these if you only need text)"


def write_csv(registry: dict, path: Path) -> None:
    main, vis = build_groups(registry)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for r in group_rows(main):
            w.writerow(csv_cells(r))
        if vis:
            w.writerow([""] * len(COLUMNS))
            w.writerow([VISION_BANNER] + [""] * (len(COLUMNS) - 1))
            w.writerow(COLUMNS)
            for r in group_rows(vis):
                w.writerow(csv_cells(r))


LEGEND = [
    ("What this is", "Free, active models only. The same model offered by several gateways is clubbed into one group "
                     "(adjacent rows with the same Rank). Groups are ordered by Intelligence (highest first), then context size."),
    ("Rank", "Position of the model group. All gateways serving the same model share one rank."),
    ("Row order inside a group", "Largest context first, then fastest. The first row is usually the best gateway to try first."),
    ("Intelligence", "1-5 rating derived from model size (parameters), with family estimates for models that publish no size "
                     "(Gemini, Mistral Large...). Top = 100B+/frontier, Strong = ~32-100B, Good = ~13-30B, Fair = ~4-12B, Basic = ~1-3B. "
                     "A rough proxy, not a benchmark: newer small models can beat older big ones."),
    ("Context class", "Ultra >200K tokens | Long 32K-200K | Medium 8K-32K | Short <=8K | Unknown = the gateway does not report it "
                      "(treated as short for big prompts). 1 token is about 4 characters."),
    ("Tools / JSON / Reasoning / Coding", "Yes = declared by the gateway. Yes~ = inferred from the model name (not declared). No = not supported or unknown."),
    ("Speed", "0-100 heuristic from the gateway's hardware and the model size. Not a measurement."),
    ("Vision", "'Text + Vision' models stay in the main table. Models named like -vl / vision / llava are vision "
               "specialists and are listed in the separate block below the main table."),
    ("Same-model matching", "Done by name (vendor prefix, ':free' and words like instruct / versatile / instant are ignored). "
                            "Gateways may serve quantised or context-limited variants of the same name: check 'Context (tokens)' per row."),
    ("Colours", "Intelligence: purple Top, green Strong, blue Good, yellow Fair, red Basic. Context: blue Ultra, green Long, "
                "yellow Medium, orange Short, grey Unknown. The CSV shows the same colours as emoji."),
]


def write_xlsx(registry: dict, path: Path) -> bool:
    try:
        from openpyxl import Workbook
        from openpyxl.formatting.rule import ColorScaleRule
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        print("openpyxl not installed: skipped models.xlsx (pip install openpyxl)", file=sys.stderr)
        return False
    main, vis = build_groups(registry)
    wb = Workbook()
    ws = wb.active
    ws.title = "Free models"
    base = Font(name="Arial", size=10)
    bold = Font(name="Arial", size=10, bold=True)
    grey = Font(name="Arial", size=10, color="808080")
    fill = lambda hex_: PatternFill("solid", start_color=hex_, end_color=hex_)
    thin = Side(style="thin", color="D9D9D9")
    thick = Side(style="medium", color="404040")
    head_font, head_fill = Font(name="Arial", size=10, bold=True, color="FFFFFF"), fill("305496")
    band = [fill("FFFFFF"), fill("F2F2F2")]
    CENTER = {"Rank", "Tier (1-5)", "Size", "Context class", "Speed (0-100)", "Tools", "JSON", "Reasoning",
              "Coding", "Gateways in group", "Free type", "Intelligence", "Modality"}

    def header(row: int) -> None:
        for c, name in enumerate(COLUMNS, 1):
            cell = ws.cell(row, c, name)
            cell.font, cell.fill = head_font, head_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.row_dimensions[row].height = 30

    def block(start_row: int, groups: list[dict]) -> int:
        r = start_row
        last_rank, band_i = None, -1
        for row in group_rows(groups):
            rank = row[0]
            first_in_group = rank != last_rank
            if first_in_group:
                band_i += 1
            last_rank = rank
            for c, name in enumerate(COLUMNS, 1):
                v = row[c - 1]
                cell = ws.cell(r, c, v if v != "" else None)
                cell.font = bold if (name == "Model" and first_in_group) else (grey if (name == "Model") else base)
                cell.fill = band[band_i % 2]
                cell.alignment = Alignment(horizontal="center" if name in CENTER else "left", vertical="center")
                cell.border = Border(top=thick if first_in_group else thin, bottom=thin, left=thin, right=thin)
                if name == "Context (tokens)":
                    cell.number_format = "#,##0"
                if name == "Intelligence":
                    cell.fill, cell.font = fill(TIER_FILL[row[COL_IDX["Tier (1-5)"]]]), bold
                if name == "Context class":
                    cls = row[c - 1]
                    cell.value = CTX_LABEL[cls]
                    cell.fill = fill(CTX_FILL[cls])
                if name in ("Tools", "JSON", "Reasoning", "Coding"):
                    if v == "Yes":
                        cell.fill = fill("C6EFCE")
                    elif v == "Yes~":
                        cell.fill, cell.font = fill("E2EFDA"), Font(name="Arial", size=10, italic=True)
                    else:
                        cell.font = grey
            r += 1
        return r

    header(1)
    end_main = block(2, main)                      # first free row after the main table
    last_main = max(end_main - 1, 1)
    if main:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{last_main}"
        sp = COL_IDX["Speed (0-100)"] + 1
        ws.conditional_formatting.add(
            f"{get_column_letter(sp)}2:{get_column_letter(sp)}{last_main}",
            ColorScaleRule(start_type="num", start_value=0, start_color="F8CBAD",
                           mid_type="num", mid_value=50, mid_color="FFEB9C",
                           end_type="num", end_value=100, end_color="C6EFCE"))
    if vis:
        r = end_main + 1
        ws.cell(r, 1, VISION_BANNER)
        for c in range(1, len(COLUMNS) + 1):
            ws.cell(r, c).fill, ws.cell(r, c).font = fill("7F6000"), Font(name="Arial", size=11, bold=True, color="FFFFFF")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=len(COLUMNS))
        header(r + 1)
        block(r + 2, vis)
    widths = {"Rank": 6, "Model": 30, "Intelligence": 14, "Tier (1-5)": 8, "Size": 9, "Gateway": 12,
              "Gateway model id": 36, "Context class": 18, "Context (tokens)": 14, "Modality": 17, "Tools": 8,
              "JSON": 8, "Reasoning": 11, "Coding": 8, "Speed (0-100)": 10, "Free type": 11, "Best for": 44,
              "Gateways in group": 10}
    for name, w in widths.items():
        ws.column_dimensions[get_column_letter(COL_IDX[name] + 1)].width = w
    ws.freeze_panes = "C2"

    lg = wb.create_sheet("How to read")
    lg.column_dimensions["A"].width = 34
    lg.column_dimensions["B"].width = 120
    lg["A1"], lg["B1"] = "Item", "Meaning"
    for c in ("A1", "B1"):
        lg[c].font, lg[c].fill = head_font, head_fill
    for i, (k, v) in enumerate(LEGEND, 2):
        lg.cell(i, 1, k).font = bold
        lg.cell(i, 2, v).font = base
        lg.cell(i, 2).alignment = Alignment(wrap_text=True, vertical="top")
        lg.cell(i, 1).alignment = Alignment(vertical="top")
    r0 = len(LEGEND) + 3
    lg.cell(r0, 1, "Intelligence colours").font = bold
    for j, t in enumerate((5, 4, 3, 2, 1)):
        cell = lg.cell(r0 + 1 + j, 1, freellm.INTELLIGENCE_LABELS[t])
        cell.fill, cell.font = fill(TIER_FILL[t]), base
    lg.cell(r0, 2, "Context colours").font = bold
    for j, cl in enumerate(CLASS_ORDER):
        cell = lg.cell(r0 + 1 + j, 2, CTX_LABEL[cl])
        cell.fill, cell.font = fill(CTX_FILL[cl]), base
    lg.cell(r0 + 8, 1, f"Registry updated {registry.get('updated_at', '?')} (source: {registry.get('source', '?')})").font = grey
    wb.save(path)
    return True


def write_tables(registry: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "MODELS.md").write_text(render_markdown(registry) + "\n", "utf-8")
    write_csv(registry, out_dir / "models.csv")
    write_xlsx(registry, out_dir / "models.xlsx")


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("registry/models.json")
    registry = json.loads(src.read_text("utf-8"))
    write_tables(registry, src.parent)
    print(f"Wrote MODELS.md, models.csv and models.xlsx in {src.parent}")


if __name__ == "__main__":
    main()
