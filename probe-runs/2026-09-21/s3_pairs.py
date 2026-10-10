#!/usr/bin/env python3
"""Section 3: rebuild both convergence populations from the dedup grouping."""
import json, csv, re, subprocess, pathlib, statistics, collections, os
from concurrent.futures import ThreadPoolExecutor

SP = pathlib.Path(__file__).parent
os.environ.setdefault("PROJ_USER_WRITABLE_DIRECTORY", str(SP / "projdata"))
import pyproj
from pyproj import Geod, Transformer
pyproj.network.set_network_enabled(True)          # grids present

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-21")
API = "https://minmod.isi.edu/api/v1"
GEOD = Geod(ellps="WGS84")
T = Transformer.from_crs(4267, 4326, always_xy=True)
P = re.compile(r"POINT\s*\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)")

members = json.load((RD / "q3-dedup-members.json").open())
site2ded = json.load((RD / "q2-site-to-dedup.json").open())
NAD = set(site2ded)

# NAD27 stored coords, from the graph pull
nad_xy = {}
for r in csv.DictReader(pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/"
                                     "probe-runs/2026-09-14/n2-nad27-coords-all.csv").open()):
    m = P.search(r["wkt"])
    nad_xy[r["site"].rsplit("/", 1)[-1]] = (float(m.group(1)), float(m.group(2)))

# every non-NAD27 member of any entity that holds a NAD27 record
need = sorted({s for v in members.values() if v for s in v["sites"] if s and s not in NAD})
print(f"non-NAD27 member sites to resolve: {len(need)}")

def batch(ids):
    for _ in range(3):
        p = subprocess.run(["curl", "-sS", "-m", "120", "-X", "POST",
                            f"{API}/mineral-sites/find_by_ids", "-H", "Content-Type: application/json",
                            "-d", json.dumps({"ids": ids})], capture_output=True)
        try:
            return json.loads(p.stdout)
        except Exception:
            continue
    return {}

sib = {}
chunks = [need[i:i + 400] for i in range(0, len(need), 400)]
with ThreadPoolExecutor(max_workers=6) as ex:
    for d in ex.map(batch, chunks):
        sib.update(d or {})
print(f"resolved: {len(sib)}")
json.dump({k: {"source_id": v.get("source_id"), "coordinates": v.get("coordinates")}
           for k, v in sib.items()}, (RD / "q3-sibling-coords.json").open("w"))

MAXKM = 5.0
all_pairs, by_nad = [], collections.defaultdict(list)
for did, v in members.items():
    if not v:
        continue
    ms = v["sites"]
    nads = [s for s in ms if s in NAD and s in nad_xy]
    sibs = [s for s in ms if s in sib and (sib[s].get("coordinates") or {}).get("lat") is not None]
    for n in nads:
        lo, la = nad_xy[n]
        fx, fy = T.transform(lo, la)
        for s in sibs:
            c = sib[s]["coordinates"]
            if sib[s]["source_id"] == "https://doi.org/10.5066/P96MMRFD":
                continue
            _, _, before = GEOD.inv(lo, la, c["lon"], c["lat"])
            if before > MAXKM * 1000:
                continue
            _, _, after = GEOD.inv(fx, fy, c["lon"], c["lat"])
            rec = {"dedup": did, "nad": n, "sib": s, "sib_src": sib[s]["source_id"],
                   "before": before, "after": after}
            all_pairs.append(rec); by_nad[n].append(rec)

nearest = [min(v, key=lambda r: r["before"]) for v in by_nad.values()]

def summ(name, rows, ents=None):
    b = [r["before"] for r in rows]; a = [r["after"] for r in rows]
    imp = sum(1 for r in rows if r["after"] < r["before"])
    print(f"\n=== {name} ===")
    print(f"  pairs/rows        : {len(rows)}")
    if ents is not None:
        print(f"  distinct entities : {ents}")
    print(f"  median before     : {statistics.median(b):.1f} m")
    print(f"  median after      : {statistics.median(a):.1f} m")
    print(f"  within 50 m before: {100*sum(1 for x in b if x<=50)/len(b):.1f} %")
    print(f"  within 50 m after : {100*sum(1 for x in a if x<=50)/len(a):.1f} %")
    print(f"  improving         : {imp} ({100*imp/len(rows):.1f} %)")
    return {"n": len(rows), "median_before": statistics.median(b), "median_after": statistics.median(a),
            "w50_before": 100*sum(1 for x in b if x<=50)/len(b),
            "w50_after": 100*sum(1 for x in a if x<=50)/len(a), "improving": imp}

ents_all = len({r["dedup"] for r in all_pairs})
r1 = summ("ALL PAIRS (expect ~2,279 across 1,470 entities; 174.2 -> 101.1; 5.3% -> 47.6%)",
          all_pairs, ents_all)
r2 = summ("NEAREST SIBLING ONLY (expect 1,602 rows / 1,470 entities; 159.1 -> 32.2; 6.6% -> 64.7%; 1,239 improve)",
          nearest, len({r["dedup"] for r in nearest}))

worse = [r for r in nearest if r["after"] > r["before"]]
print(f"\n  nearest-only pairs that get WORSE: {len(worse)}")
for k, v in collections.Counter(r["sib_src"] for r in worse).most_common(6):
    print(f"     {v:>4}  {k}")

json.dump({"all_pairs": r1, "nearest": r2, "entities_all": ents_all,
           "worse_nearest": len(worse)}, (RD / "q3-convergence.json").open("w"), indent=1)
with (RD / "q3-pairs.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(all_pairs[0].keys())); w.writeheader(); w.writerows(all_pairs)
print("\nwrote q3-convergence.json, q3-pairs.csv")
