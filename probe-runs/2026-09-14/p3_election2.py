#!/usr/bin/env python3
"""Section 4, corrected for the two traps the earlier runs identified.

Trap 1 - trailing zeros. 'POINT(148.56667 -9.50000)' stores 5 decimals on both
axes in the STRING; float() would report 1 for -9.50000. The string is what the
source wrote, so short strings are counted from the string.

Trap 2 - DMS. A 12-14 decimal value is a degrees/minutes/seconds conversion
round-tripping through float, not precision. Tested only on long values, where
the test discriminates (it is vacuous on short ones), coarsest grid first.

Precision is therefore reported as an angular RESOLUTION in degrees, not a
decimal count, and the two are not interchangeable.
"""
import csv, re, collections, pathlib

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-14")
pairs = list(csv.DictReader((RD / "p3.4a-coord-pairs.csv").open()))
scores = {r["uri"]: float(r["score"]) for r in csv.DictReader((RD / "p3.4b-source-scores.csv").open())
          if r["uri"] and r["score"]}
POINT = re.compile(r"POINT\s*\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)")
TOL = 1e-8

def str_dp(s):
    return len(s.split(".")[1]) if "." in s else 0

def on_grid(v, grid):        # grid = 60 (arcmin) or 3600 (arcsec)
    return abs(v * grid - round(v * grid)) < TOL

def resolution(s):
    """Angular resolution in degrees that this stored string actually carries."""
    d, v = str_dp(s), float(s)
    if d <= 6:
        return 10.0 ** (-d), f"{d}dp"        # trust the string, trailing zeros included
    # long value: float round-trip of either a DMS conversion or a <=6dp decimal
    if on_grid(v, 60):
        return 1.0 / 60, "arcmin"            # coarsest grid first - order matters
    if on_grid(v, 3600):
        return 1.0 / 3600, "arcsec"
    for dd in range(0, 7):                   # collapse float noise
        if abs(round(v, dd) - v) < 1e-9:
            return 10.0 ** (-dd), f"{dd}dp*"
    return 1e-6, "fine"

def parse(wkt):
    m = POINT.search(wkt)
    if not m:
        return None
    lon, lat = m.group(1), m.group(2)
    rlon, klon = resolution(lon)
    rlat, klat = resolution(lat)
    return {"res": max(rlon, rlat), "kind": f"{klon}/{klat}", "wkt": wkt}

rec, edges = {}, []
for r in pairs:
    for side in ("s", "o"):
        u = r[side]
        if u not in rec:
            p = parse(r[f"{side}_wkt"])
            if p:
                rec[u] = {**p, "src": r[f"{side}_src"], "label": r.get(f"{side}_label") or ""}
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

print(f"coordinate-bearing records in clusters : {len(rec)}")
print(f"multi-record groups                    : {len(multi)}")

# A coordinate must be MATERIALLY better to count: at least 3x finer resolution,
# so float-noise and one-notch ties do not manufacture findings.
FACTOR = 3.0
loss_hist, elected_src, discarded_src, hits = collections.Counter(), collections.Counter(), collections.Counter(), []
ties_no_score = 0
for gid, members in multi.items():
    ms = [rec[u] for u in members]
    if all(m["src"] not in scores for m in ms):
        ties_no_score += 1
    elected = max(ms, key=lambda m: scores.get(m["src"], -1.0))
    best = min(ms, key=lambda m: m["res"])
    if elected["res"] > best["res"] * FACTOR:
        ratio = elected["res"] / best["res"]
        b = 1 if ratio < 12 else (2 if ratio < 120 else 3)
        loss_hist[b] += 1
        elected_src[elected["src"]] += 1
        discarded_src[best["src"]] += 1
        hits.append((gid, elected, best, ratio, len(ms)))

print(f"groups where NO member has a source score: {ties_no_score}  "
      f"(election is then arbitrary)")
print(f"\n=== GROUPS ELECTING A MATERIALLY COARSER COORDINATE (>{FACTOR:.0f}x) ===")
print(f"   {len(hits)} of {len(multi)} groups ({100*len(hits)/len(multi):.1f}%)")
print("\n--- magnitude of loss (resolution ratio) ---")
for k, n in sorted(loss_hist.items()):
    print(f"   {{1:'~1 decimal place (3-12x)',2:'~2 (12-120x)',3:'3+ (>120x)'}}[{k}]  ".replace(
        "{1:'~1 decimal place (3-12x)',2:'~2 (12-120x)',3:'3+ (>120x)'}", "")
        .replace(f"[{k}]", f"{ {1:'~1 dp (3-12x)',2:'~2 dp (12-120x)',3:'3+ dp (>120x)'}[k]:<20}") + f"{n:>6}")

print("\n--- most often ELECTED but coarser ---")
for k, v in elected_src.most_common(10):
    print(f"   {v:>5}  score={str(scores.get(k,'none')):<5} {k}")
print("\n--- most often DISCARDED but better ---")
for k, v in discarded_src.most_common(10):
    print(f"   {v:>5}  score={str(scores.get(k,'none')):<5} {k}")

print("\n--- named examples ---")
for gid, el, best, ratio, n in sorted(hits, key=lambda t: -t[3])[:8]:
    lbl = el["label"] or best["label"] or "(unnamed)"
    print(f"\n  {lbl[:50]}   group of {n},  {ratio:.0f}x coarser")
    print(f"     ELECTED {el['wkt'][:44]:<44} res={el['res']:.6f}° [{el['kind']}] "
          f"score={scores.get(el['src'],'none')} {el['src'].split('/')[-1]}")
    print(f"     BETTER  {best['wkt'][:44]:<44} res={best['res']:.6f}° [{best['kind']}] "
          f"score={scores.get(best['src'],'none')} {best['src'].split('/')[-1]}")

with (RD / "p3.4-election.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["group_size", "ratio", "elected_src", "elected_score", "elected_wkt",
                "elected_res_deg", "elected_kind", "best_src", "best_score", "best_wkt",
                "best_res_deg", "best_kind"])
    for gid, el, best, ratio, n in hits:
        w.writerow([n, round(ratio, 2), el["src"], scores.get(el["src"], ""), el["wkt"],
                    el["res"], el["kind"], best["src"], scores.get(best["src"], ""),
                    best["wkt"], best["res"], best["kind"]])
print(f"\nwrote p3.4-election.csv  ({len(hits)} rows)")
