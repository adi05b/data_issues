#!/usr/bin/env python3
"""Section 1: re-run the election against the REAL rule.

Real rule (from the published minmodkg source, as quoted in the brief):
    expert record (created_by not a system user) -> 1.0
    otherwise                                    -> min(source_score or 0.5, 0.99)
    ties -> SystemCmpKey(False, source_id, record_id, modified_at), DESCENDING

The earlier simulation used `scores.get(src, -1.0)`, i.e. it ranked unscored
sources LAST. The real default is 0.5, which outranks MRDS at 0.1.
"""
import csv, re, math, collections, pathlib

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-14")
pairs = list(csv.DictReader((RD / "v1b-coord-pairs-full.csv").open()))
scores = {r["uri"]: float(r["score"]) for r in csv.DictReader((RD / "p3.4b-source-scores.csv").open())
          if r["uri"] and r["score"]}
POINT = re.compile(r"POINT\s*\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)")
DEFAULT_SOURCE_SCORE = 0.5
TOL = 1e-8

def is_system(created_by):
    return "/users/s/" in created_by

def rank_score(src, created_by):
    if not is_system(created_by):
        return 1.0
    s = scores.get(src)
    if s is None or s < 0:
        s = DEFAULT_SOURCE_SCORE
    return min(s, 0.99)

def str_dp(s):
    return len(s.split(".")[1]) if "." in s else 0
def on_grid(v, g):
    return abs(v * g - round(v * g)) < TOL
def resolution(s):
    d, v = str_dp(s), float(s)
    if d <= 6:
        return 10.0 ** (-d)
    if on_grid(v, 60):   return 1.0 / 60
    if on_grid(v, 3600): return 1.0 / 3600
    for dd in range(0, 7):
        if abs(round(v, dd) - v) < 1e-9:
            return 10.0 ** (-dd)
    return 1e-6

def parse(wkt):
    m = POINT.search(wkt)
    if not m:
        return None
    lon, lat = m.group(1), m.group(2)
    return {"res": max(resolution(lon), resolution(lat)),
            "x": float(lon), "y": float(lat), "wkt": wkt}

rec, edges = {}, []
for r in pairs:
    for side in ("s", "o"):
        u = r[side]
        if u not in rec:
            p = parse(r[f"{side}_wkt"])
            if p:
                rec[u] = {**p, "src": r[f"{side}_src"], "label": r.get(f"{side}_label") or "",
                          "rid": r.get(f"{side}_rid") or "", "by": r[f"{side}_by"],
                          "mod": r[f"{side}_mod"], "uri": u}
    if r["s"] in rec and r["o"] in rec:
        edges.append((r["s"], r["o"]))

parent = {u: u for u in rec}
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
for a, b in edges:
    ra, rb = find(a), find(b)
    if ra != rb: parent[ra] = rb
groups = collections.defaultdict(list)
for u in rec:
    groups[find(u)].append(u)
multi = {k: v for k, v in groups.items() if len(v) > 1}
print(f"multi-record groups: {len(multi)}  (earlier run: 7362)")

def elect(ms):
    """Highest rank_score; ties by (source_id, record_id, modified_at) DESCENDING."""
    return max(ms, key=lambda m: (rank_score(m["src"], m["by"]),
                                  m["src"], m["rid"], m["mod"]))

def elect_old(ms):
    return max(ms, key=lambda m: scores.get(m["src"], -1.0))

FACTOR = 3.0
new_hits, old_hits = {}, {}
tie_decided = expert_decided = 0
for gid, members in multi.items():
    ms = [rec[u] for u in members]
    el, elo = elect(ms), elect_old(ms)
    best = min(ms, key=lambda m: m["res"])
    top = max(rank_score(m["src"], m["by"]) for m in ms)
    if sum(1 for m in ms if rank_score(m["src"], m["by"]) == top) > 1:
        tie_decided += 1
    if top == 1.0:
        expert_decided += 1
    if el["res"] > best["res"] * FACTOR:
        new_hits[gid] = (el, best, el["res"] / best["res"], len(ms))
    if elo["res"] > best["res"] * FACTOR:
        old_hits[gid] = (elo, best, elo["res"] / best["res"], len(ms))

print(f"\n=== CORRECTED ELECTION COUNT ===")
print(f"  earlier (wrong scoring) : {len(old_hits)}")
print(f"  corrected (real rule)   : {len(new_hits)}")
surv = set(new_hits) & set(old_hits)
print(f"  of the earlier {len(old_hits)}: {len(surv)} survive, "
      f"{len(old_hits)-len(surv)} were artefacts of the wrong default score")
print(f"  newly found by the correct rule: {len(set(new_hits)-set(old_hits))}")

print(f"\n  groups decided by the alphabetical tie-break : {tie_decided} "
      f"({100*tie_decided/len(multi):.1f}%)")
print(f"  groups containing an expert (1.0) record     : {expert_decided}")

print("\n--- most often ELECTED but coarser (corrected) ---")
c = collections.Counter(v[0]["src"] for v in new_hits.values())
for k, n in c.most_common(10):
    print(f"   {n:>5}  rank={rank_score(k,'/users/s/x'):<5} {k}")
print("\n--- most often DISCARDED but better (corrected) ---")
d = collections.Counter(v[1]["src"] for v in new_hits.values())
for k, n in d.most_common(10):
    print(f"   {n:>5}  rank={rank_score(k,'/users/s/x'):<5} {k}")

# separation
def sep(a, b):
    dlat = (b["y"] - a["y"]) * 111.0
    dlon = (b["x"] - a["x"]) * 111.0 * math.cos(math.radians((a["y"] + b["y"]) / 2))
    return math.hypot(dlat, dlon)
buck = collections.Counter()
for el, best, ratio, n in new_hits.values():
    dkm = sep(el, best)
    buck["<=1km" if dkm <= 1 else ("1-11km" if dkm <= 11 else ("11-50km" if dkm <= 50 else ">50km"))] += 1
print("\n--- separation, corrected set ---")
for k in ["<=1km", "1-11km", "11-50km", ">50km"]:
    print(f"   {k:<9} {buck[k]:>5} ({100*buck[k]/len(new_hits):.1f}%)")
zeros = sum(1 for el, b, r, n in new_hits.values() if (el["x"], el["y"]) == (0.0, 0.0))
print(f"\ngroups electing (0,0) over a real coordinate: {zeros}")

with (RD / "v1-election-corrected.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["group", "group_size", "ratio", "elected_uri", "elected_src", "elected_rank",
                "elected_wkt", "best_uri", "best_src", "best_rank", "best_wkt", "sep_km",
                "in_earlier_set"])
    for gid, (el, best, ratio, n) in new_hits.items():
        w.writerow([gid, n, round(ratio, 2), el["uri"], el["src"], rank_score(el["src"], el["by"]),
                    el["wkt"], best["uri"], best["src"], rank_score(best["src"], best["by"]),
                    best["wkt"], round(sep(el, best), 3), gid in old_hits])
print("wrote v1-election-corrected.csv")
