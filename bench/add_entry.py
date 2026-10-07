"""Publish one finished run as a gallery entry.

Usage:
  python3 bench/add_entry.py <run_dir> --slug SLUG --harness claude-code|claude-code-openrouter|codex|grok-build|antigravity
      [--display-model NAME] [--requested ID] [--actual ID] [--run NAME] [--note TEXT]
      [--rates IN,CACHED,CACHE_WRITE,OUT]   # USD per 1M tokens; required when the transcript has no cost or Claude Code has no price for the model

Reads <run_dir>/transcript.jsonl, copies <run_dir>/pacman.html (or index.html) to entries/<slug>.html,
and upserts the entry into entries/meta.json. On an existing entry, score fields (and the note, unless --note) are kept.
Fails loudly if the transcript has no usage record or the HTML is missing.
"""
import argparse
import json
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
META = REPO / "entries" / "meta.json"
HARNESS_LABEL = {
    "claude-code": "Claude Code",
    "claude-code-openrouter": "OpenRouter / Claude Code",
    "codex": "Codex",
    "grok-build": "Grok Build",
    "antigravity": "Antigravity",
}
KEEP_KEYS = ("score", "score_summary", "score_notes")


###############################################################################
def events(path):
    for line in path.open():
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


###############################################################################
def claude_stats(run_dir, rates):
    """Claude Code stream-json: the final `result` event carries usage and total_cost_usd.

    Claude Code prices models it doesn't know with a placeholder (`costBasis: unknown`); those runs
    need --rates, which then replaces total_cost_usd with the published rate card.
    """
    results = [e for e in events(run_dir / "transcript.jsonl") if e.get("type") == "result"]
    if not results:
        sys.exit("no result event in transcript")
    r = results[-1]
    u = r["usage"]
    models = list((r.get("modelUsage") or {}).keys())
    unknown = any(m.get("costBasis") == "unknown" for m in (r.get("modelUsage") or {}).values())
    if unknown and rates is None:
        sys.exit("Claude Code has no price for this model (costBasis unknown); pass --rates IN,CACHED,CACHE_WRITE,OUT")
    cost = r["total_cost_usd"] if rates is None else price(
        rates, u["input_tokens"], u.get("cache_read_input_tokens", 0), u.get("cache_creation_input_tokens", 0),
        u["output_tokens"])
    return {
        "actual": models[0] if len(models) == 1 else None,
        "duration_ms": r["duration_ms"],
        "input_tokens": u["input_tokens"],
        "cached_input_tokens": u.get("cache_read_input_tokens"),
        "cache_write_tokens": u.get("cache_creation_input_tokens"),
        "output_tokens": u["output_tokens"],
        "thinking_tokens": (u.get("output_tokens_details") or {}).get("thinking_tokens"),
        "cost_usd": round(cost, 8),
    }


###############################################################################
def codex_stats(run_dir, rates):
    """Codex --json: sum every turn.completed usage; price it with the published rate card."""
    turns = [e["usage"] for e in events(run_dir / "transcript.jsonl") if e.get("type") == "turn.completed"]
    if not turns:
        sys.exit("no turn.completed event in transcript")
    tot = {k: sum(t.get(k, 0) for t in turns) for k in
           ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens", "reasoning_output_tokens")}
    return {
        "duration_ms": wall_ms(run_dir),
        "input_tokens": tot["input_tokens"],
        "cached_input_tokens": tot["cached_input_tokens"],
        "cache_write_tokens": tot["cache_write_input_tokens"],
        "output_tokens": tot["output_tokens"],
        "thinking_tokens": tot["reasoning_output_tokens"],
        "tokens_total": tot["input_tokens"] + tot["output_tokens"],
        # Cached and cache-write tokens are inside input_tokens; reasoning is inside output_tokens.
        "cost_usd": price(rates, tot["input_tokens"] - tot["cached_input_tokens"] - tot["cache_write_input_tokens"],
                          tot["cached_input_tokens"], tot["cache_write_input_tokens"], tot["output_tokens"]),
    }


###############################################################################
def grok_stats(run_dir):
    """Grok Build streaming-json: the final `end` event carries usage and total_cost_usd."""
    ends = [e for e in events(run_dir / "transcript.jsonl") if e.get("type") == "end"]
    if not ends:
        sys.exit("no end event in transcript")
    u = ends[-1]["usage"]
    return {
        "duration_ms": wall_ms(run_dir),
        "input_tokens": u["input_tokens"],
        "cached_input_tokens": u.get("cache_read_input_tokens"),
        "output_tokens": u["output_tokens"],
        "thinking_tokens": u.get("reasoning_tokens"),
        "cost_usd": round(ends[-1]["total_cost_usd"], 8),
    }


###############################################################################
def antigravity_stats(run_dir, rates):
    """agy stream-json: the final `result` event carries usage but no cost."""
    results = [e["result"] for e in events(run_dir / "transcript.jsonl") if e.get("event") == "result"]
    if not results:
        sys.exit("no result event in transcript")
    r = results[-1]
    u = r["usage"]
    return {
        "duration_ms": round(r["duration_seconds"] * 1000),
        "input_tokens": u["input_tokens"],
        "cached_input_tokens": u.get("cache_read_tokens"),
        "output_tokens": u["output_tokens"],
        "thinking_tokens": u.get("thinking_tokens"),
        "cost_usd": price(rates, u["input_tokens"], u.get("cache_read_tokens", 0), 0,
                          u["output_tokens"] + u.get("thinking_tokens", 0)),
    }


###############################################################################
def wall_ms(run_dir):
    meta = run_dir / "meta.json"
    if meta.exists() and "wall_seconds" in json.loads(meta.read_text()):
        return round(json.loads(meta.read_text())["wall_seconds"] * 1000)
    wall = run_dir / "wall_seconds"
    if wall.exists():
        return round(float(wall.read_text()) * 1000)
    sys.exit("no wall time: expected meta.json wall_seconds or a wall_seconds file")


###############################################################################
def run_effort(run_dir):
    """run_cell.py records effort in meta.json; runs that predate it all ran at high."""
    meta = run_dir / "meta.json"
    return json.loads(meta.read_text()).get("effort", "high") if meta.exists() else "high"


###############################################################################
def price(rates, uncached, cached, cache_write, output):
    if rates is None:
        sys.exit("this transcript has no cost; pass --rates IN,CACHED,CACHE_WRITE,OUT (USD per 1M tokens)")
    r_in, r_cached, r_write, r_out = rates
    return round((uncached * r_in + cached * r_cached + cache_write * r_write + output * r_out) / 1e6, 8)


###############################################################################
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=pathlib.Path)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--harness", required=True, choices=sorted(HARNESS_LABEL))
    ap.add_argument("--display-model")
    ap.add_argument("--requested")
    ap.add_argument("--actual")
    ap.add_argument("--run")
    ap.add_argument("--note")
    ap.add_argument("--phase", type=int, default=1)
    ap.add_argument("--rates", type=lambda s: [float(x) for x in s.split(",")])
    args = ap.parse_args()
    run_dir = args.run_dir.expanduser()

    if args.harness.startswith("claude-code"):
        stats = claude_stats(run_dir, args.rates)
    elif args.harness == "codex":
        stats = codex_stats(run_dir, args.rates)
    elif args.harness == "grok-build":
        stats = grok_stats(run_dir)
    else:
        stats = antigravity_stats(run_dir, args.rates)

    html = next((run_dir / n for n in ("pacman.html", "index.html") if (run_dir / n).exists()), None)
    if html is None:
        sys.exit(f"no pacman.html or index.html in {run_dir}")
    shutil.copy(html, REPO / "entries" / f"{args.slug}.html")

    requested = args.requested or args.display_model or args.slug
    entry = {
        "slug": args.slug,
        "harness": HARNESS_LABEL[args.harness],
        "run": args.run or run_dir.name,
        "requested": requested,
        "actual": args.actual or stats.pop("actual", None) or requested,
        "effort": run_effort(run_dir),
        "duration_ms": None, "input_tokens": None, "cached_input_tokens": None, "cache_write_tokens": None,
        "output_tokens": None, "thinking_tokens": None, "tokens_total": None, "cost_usd": None,
        "note": args.note,
        "display_model": args.display_model or args.slug,
        "phase": args.phase,
        "score": None,
    }
    stats.pop("actual", None)
    entry.update(stats)

    entries = json.loads(META.read_text())
    old = next((e for e in entries if e["slug"] == args.slug), None)
    if old:
        entry.update({k: old[k] for k in KEEP_KEYS if k in old})
        if args.note is None:
            entry["note"] = old.get("note")
        entries[entries.index(old)] = entry
    else:
        entries.append(entry)
    META.write_text(json.dumps(entries, indent=2) + "\n")
    print(json.dumps(entry, indent=1))


if __name__ == "__main__":
    main()
