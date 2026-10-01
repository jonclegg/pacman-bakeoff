"""Flag entries whose play-test numbers contradict their published score.

Usage: python3 bench/playtest/screen.py <playtest out dir> [--anchors claude-opus-5-5,gpt-6.1-sol]

Reads <dir>/<slug>.json from bench/playtest/run.py and entries/meta.json. Every red flag is a
measured symptom; an entry is CONTRADICTED when a flag hits a check its score_notes mark `ok`
or `minor` (or it has script errors at 60+). Those entries need a re-audit; every flag still needs
a human look, since the colour tracker can follow the wrong object.
"""
import argparse
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
SPEED_OK = (4.0, 12.0)  # tiles/s; arcade level 1 is about 7.6 for Pac-Man, 7.1 for ghosts


###############################################################################
def turn_rate(controls):
    ok = n = 0
    for scheme in (controls or {}).values():
        for v in scheme.values():
            a, b = (int(x) for x in v.split("/"))
            ok += a; n += b
    return ok / n if n else None


###############################################################################
def moving_probes(r, who):
    """Probe summaries for Pac-Man ('pac') or a ghost colour, only where the actor was really moving."""
    out = []
    for p in r.get("speed_probes") or []:
        s = p.get("pac") if who == "pac" else (p.get("ghosts") or {}).get(who)
        if s and s["moving_frac"] >= 0.1:
            out.append(s)
    return out


###############################################################################
def flags(r, anchor_path):
    """List of (check, message) red flags from one play-test result."""
    f = []
    if not r.get("start_method"):
        return [("controls", "could not start, or Pac-Man never moved")]
    for s in moving_probes(r, "pac"):
        if s["avg_tps"] > SPEED_OK[1] * 1.5 or (s["moving_frac"] >= 0.5 and not SPEED_OK[0] <= s["speed_tps"] <= SPEED_OK[1]):
            f.append(("controls", f"Pac-Man speed {s['speed_tps']} tiles/s while moving, {s['avg_tps']} over the window"))
    tele = sum(p["pac"]["teleports"] for p in r.get("speed_probes") or [] if p.get("pac"))
    # Eaten ghosts, deaths and level resets each look like one jump, so only repeated jumps count.
    if tele >= 3 or (r.get("pac_jumps_gt3_tiles") or 0) >= 6:
        f.append(("controls", f"Pac-Man teleports ({tele} one-frame jumps > 1.6 tiles, {r.get('pac_jumps_gt3_tiles')} > 3 tiles)"))
    for g in ("red", "pink", "cyan", "orange"):
        for s in moving_probes(r, g):
            if s["avg_tps"] > SPEED_OK[1] * 1.5 or s["teleports"] >= 3:
                f.append(("ghosts", f"{g} ghost {s['avg_tps']} tiles/s over the window, {s['teleports']} teleports"))
                break
        gs = (r.get("ghosts") or {}).get(g) or {}
        if gs.get("seen_frac", 0) > 0.3 and gs.get("cells", 0) <= 3:
            f.append(("ghosts", f"{g} ghost visited only {gs.get('cells')} tiles in {r.get('samples')} samples"))
        if gs.get("onwall_frac", 0) > 0.03:
            f.append(("ghosts", f"{g} ghost drawn on walls {gs['onwall_frac']:.0%} of the time"))
    if anchor_path and r.get("pac_path_tiles", 0) < 0.35 * anchor_path:
        f.append(("stuck", f"Pac-Man travelled {r.get('pac_path_tiles')} tiles vs anchors' {anchor_path:.0f}"))
    if r.get("stuck_events_s"):
        f.append(("stuck", f"stuck events {r['stuck_events_s']} s"))
    tr = turn_rate(r.get("controls"))
    if tr is not None and tr < 0.3:
        f.append(("controls", f"only {tr:.0%} of turns taken"))
    if r.get("pac_onwall_frac", 0) > 0.03:
        f.append(("stuck", f"Pac-Man drawn on walls {r['pac_onwall_frac']:.0%} of the time"))
    a = r.get("audio") or {}
    if not a.get("runningStarts"):
        f.append(("sound", "no audible Web Audio starts"))
    if r.get("errors"):
        f.append(("other", f"errors: {r['errors'][:2]}"))
    return f


###############################################################################
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=pathlib.Path)
    ap.add_argument("--anchors", default="claude-opus-5-5,gpt-6.1-sol")
    args = ap.parse_args()
    meta = {e["slug"]: e for e in json.loads((REPO / "entries" / "meta.json").read_text())}
    results = {p.stem: json.loads(p.read_text()) for p in args.out.glob("*.json")}
    anchors = [results[a] for a in args.anchors.split(",") if a in results]
    anchor_path = sum(a.get("pac_path_tiles", 0) for a in anchors) / len(anchors) if anchors else None

    rows = []
    for slug, e in sorted(meta.items(), key=lambda kv: -(kv[1].get("score") or 0)):
        r = results.get(slug)
        if r is None:
            rows.append((slug, e.get("score"), "MISSING", []))
            continue
        fl = flags(r, anchor_path)
        notes = e.get("score_notes") or {}
        clash = [m for chk, m in fl if (notes.get(chk) or {}).get("mark") in ("ok", "minor")
                 or (chk == "other" and (e.get("score") or 0) >= 60)]
        verdict = "CONTRADICTED" if clash else ("flags" if fl else "clean")
        rows.append((slug, e.get("score"), verdict, fl))
    for slug, score, verdict, fl in rows:
        print(f"{verdict:13} {score!s:>4}  {slug}")
        for chk, m in fl:
            print(f"{'':19}{chk:9} {m}")


if __name__ == "__main__":
    main()
