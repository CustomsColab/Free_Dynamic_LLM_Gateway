"""Refresh registry/models.json from every configured gateway's live /models catalogue.

    python scripts/refresh_registry.py            # live refresh (needs API keys in env)
    python scripts/refresh_registry.py --seed     # write the built-in starter registry

Rules:
  * a gateway without an API key is skipped and its previous entries are kept untouched
  * a gateway that answers OK but no longer lists a model -> that model becomes status "missing"
    (and is dropped after KEEP_MISSING_DAYS)
  * a gateway that errors keeps its previous entries (so one outage cannot wipe the registry)
  * API keys are never written anywhere

Logs (every live run):
  * stdout table                      -> visible in the GitHub Actions log
  * $GITHUB_STEP_SUMMARY              -> table on the workflow run page
  * registry/refresh_log.jsonl        -> one JSON line per run (history, last LOG_KEEP runs)
  * registry/models.json "last_refresh" -> the same record for the latest run

Gateway status values:
  ok              answered and lists at least one free model
  no_free_models  answered, models listed, but none are free
  empty           answered but listed no usable chat models
  error           HTTP / network / parse failure (previous entries kept)
  skipped         no API key configured
"""
from __future__ import annotations

import argparse
import calendar
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

import freellm  # noqa: E402

OUT = Path("registry/models.json")
LOG = Path("registry/refresh_log.jsonl")
TIMEOUT = 30
KEEP_MISSING_DAYS = 3
LOG_KEEP = 200
EXAMPLES = 10


def fetch(name: str, cfg: dict, client: httpx.Client) -> dict:
    base = {"gateway": name, "models": None, "listed": 0, "http_status": None, "latency_ms": None}
    key = os.getenv(cfg["key_env"], "")
    if not key:
        return {**base, "status": "skipped", "error": "API key not configured"}
    t0 = time.perf_counter()
    try:
        r = client.get(f'{cfg["base_url"].rstrip("/")}/models',
                       headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
                       timeout=TIMEOUT)
        base["http_status"] = r.status_code
        base["latency_ms"] = round((time.perf_counter() - t0) * 1000)
        r.raise_for_status()
        payload = r.json()
        rows = payload if isinstance(payload, list) else (payload.get("data") or payload.get("models") or [])
        models = [m for m in (freellm.normalize_row(name, cfg, row) for row in rows if isinstance(row, dict)) if m]
        free = sum(1 for m in models if m["is_free"])
        status = "empty" if not models else ("ok" if free else "no_free_models")
        return {**base, "models": models, "listed": len(rows), "status": status, "error": None}
    except Exception as exc:  # noqa: BLE001 - any failure must not break other gateways
        if isinstance(exc, httpx.HTTPStatusError):
            base["http_status"] = exc.response.status_code
        base["latency_ms"] = base["latency_ms"] or round((time.perf_counter() - t0) * 1000)
        msg = str(exc).replace(key, "***")
        return {**base, "status": "error", "error": msg[:300]}


def merge(previous: list[dict], fresh: dict[str, list[dict]], now: float) -> list[dict]:
    prev = {m["uid"]: m for m in previous}
    today = freellm._iso(now)
    out: dict[str, dict] = {}
    for gateway, models in fresh.items():
        for m in models:
            old = prev.get(m["uid"], {})
            m["first_seen"] = old.get("first_seen", today)
            m["missing_since"] = None
            out[m["uid"]] = m
    for uid, old in prev.items():
        if uid in out:
            continue
        if old["gateway"] in fresh:                      # gateway answered, model is gone
            since = old.get("missing_since") or today
            age_days = (now - calendar.timegm(time.strptime(since, "%Y-%m-%dT%H:%M:%SZ"))) / 86400
            if age_days <= KEEP_MISSING_DAYS:
                old.update(status="missing", available=False, missing_since=since)
                out[uid] = old
        else:                                            # gateway not refreshed -> keep as-is
            out[uid] = old
    return sorted(out.values(), key=lambda m: m["uid"])


def build_record(results: list[dict], previous: list[dict], now: float) -> dict:
    """One log record: per-gateway status, counts, and which models appeared / disappeared."""
    prev_active: dict[str, set] = {}
    for m in previous:
        if m.get("status", "active") == "active":
            prev_active.setdefault(m["gateway"], set()).add(m["uid"])
    gateways = {}
    for r in results:
        g, models = r["gateway"], r["models"]
        entry = {"status": r["status"], "http_status": r["http_status"], "latency_ms": r["latency_ms"],
                 "models_listed": r["listed"] if models is not None else None,
                 "chat_models": len(models) if models is not None else None,
                 "free_models": sum(1 for m in models if m["is_free"]) if models is not None else None,
                 "error": r["error"]}
        if models is not None:
            now_uids = {m["uid"] for m in models}
            added = sorted(now_uids - prev_active.get(g, set()))
            removed = sorted(prev_active.get(g, set()) - now_uids)
            entry.update(added_count=len(added), removed_count=len(removed),
                         added=added[:EXAMPLES], removed=removed[:EXAMPLES])
        gateways[g] = entry
    return {"time": freellm._iso(now), "gateways": gateways,
            "ok": sum(1 for v in gateways.values() if v["status"] == "ok"),
            "failed": sum(1 for v in gateways.values() if v["status"] == "error"),
            "skipped": sum(1 for v in gateways.values() if v["status"] == "skipped")}


def append_log(path: Path, record: dict, keep: int = LOG_KEEP) -> None:
    lines = path.read_text("utf-8").splitlines() if path.exists() else []
    lines.append(json.dumps(record, ensure_ascii=False))
    path.write_text("\n".join(lines[-keep:]) + "\n", "utf-8")


def render_table(record: dict, markdown: bool = False) -> str:
    cols = ["gateway", "status", "http", "ms", "listed", "free", "added", "removed", "error"]
    rows = []
    for g, v in record["gateways"].items():
        rows.append([g, v["status"], v["http_status"] or "-", v["latency_ms"] if v["latency_ms"] is not None else "-",
                     v["models_listed"] if v["models_listed"] is not None else "-",
                     v["free_models"] if v["free_models"] is not None else "-",
                     v.get("added_count", "-"), v.get("removed_count", "-"), (v["error"] or "")[:80]])
    if markdown:
        out = [f"### LLM registry refresh {record['time']}",
               f"ok **{record['ok']}**, failed **{record['failed']}**, skipped **{record['skipped']}**", "",
               "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        out += ["| " + " | ".join(str(c).replace("|", "/") for c in r) + " |" for r in rows]
        return "\n".join(out) + "\n"
    widths = [max(len(str(x)) for x in [c] + [r[i] for r in rows]) for i, c in enumerate(cols)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    return "\n".join([fmt.format(*cols)] + [fmt.format(*[str(c) for c in r]) for r in rows])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", action="store_true", help="write the built-in starter registry")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--log", default=str(LOG))
    args = ap.parse_args()
    out, log = Path(args.out), Path(args.log)
    out.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    gws = freellm.all_gateways()
    record = None

    if args.seed:
        registry = freellm.seed_registry()
    else:
        previous = []
        if out.exists():
            try:
                previous = json.loads(out.read_text("utf-8")).get("models", [])
            except Exception:
                pass
        with httpx.Client() as client, ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda kv: fetch(kv[0], kv[1], client), gws.items()))
        fresh = {r["gateway"]: r["models"] for r in results if r["models"] is not None}
        errors = [{"gateway": r["gateway"], "error": r["error"]} for r in results if r["error"]]
        record = build_record(results, previous, now)
        registry = {
            "schema_version": 2,
            "source": "live",
            "updated_at": freellm._iso(now),
            "gateways": freellm.public_gateways(gws),
            "models": merge(previous, fresh, now),
            "errors": errors,
            "last_refresh": record,
        }

    models = registry["models"]
    registry["summary"] = {
        "total": len(models),
        "free_active": sum(1 for m in models if m["is_free"] and m["status"] == "active"),
        "by_gateway": {g: sum(1 for m in models if m["gateway"] == g and m["is_free"] and m["status"] == "active")
                       for g in sorted({m["gateway"] for m in models})},
    }
    out.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"Models: {registry['summary']['total']}  free+active: {registry['summary']['free_active']}")

    if record:
        append_log(log, record)
        print(render_table(record))
        summary = os.getenv("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as fh:
                fh.write(render_table(record, markdown=True))
        if record["ok"] == 0:
            print("WARNING: no gateway returned free models - check keys / URLs above", file=sys.stderr)


if __name__ == "__main__":
    main()
