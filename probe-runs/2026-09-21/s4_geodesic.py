#!/usr/bin/env python3
"""Section 4 final: geodesic (WGS84 ellipsoid) shift distances, computed twice --
grids absent and grids present -- over all 7,720 stored ARDF coordinates.
"""
import csv, json, math, pathlib, statistics, sys
import pyproj
from pyproj import Geod, Transformer
from pyproj.transformer import TransformerGroup

RD = pathlib.Path(sys.argv[1]); SRC = pathlib.Path(sys.argv[2])
GEOD = Geod(ellps="WGS84")
rows = list(csv.DictReader(SRC.open()))

def pctl(v, p):
    v = sorted(v); k = (len(v) - 1) * p / 100
    lo, hi = math.floor(k), math.ceil(k)
    return v[lo] if lo == hi else v[lo] + (v[hi] - v[lo]) * (k - lo)

def run(net):
    pyproj.network.set_network_enabled(net)
    g = TransformerGroup(4267, 4326, always_xy=True)
    T = Transformer.from_crs(4267, 4326, always_xy=True)
    recs, shifts = [], []
    for r in rows:
        w = r["wkt"]; lon, lat = (float(v) for v in w[w.index("(")+1:w.index(")")].split())
        x, y = T.transform(lon, lat)
        d = GEOD.inv(lon, lat, x, y)[2]
        rec = dict(record_id=r["record_id"], label=r["label"], site=r["site"],
                   source_id=r["source"], crs_obs=r["crs_obs"], wkt=w,
                   stored_lon=lon, stored_lat=lat, fixed_lon=x, fixed_lat=y,
                   shift_m=d, declined=(x == lon and y == lat))
        recs.append(rec)
        if not rec["declined"]:
            shifts.append(d)
    return {
        "network": net, "n_ops_available": len(g.transformers),
        "n_ops_unavailable": len(g.unavailable_operations),
        "selected": g.transformers[0].description,
        "selected_accuracy_m": g.transformers[0].accuracy,
        "declined": sum(r["declined"] for r in recs),
        "moved": len(shifts),
        "min": min(shifts), "p5": pctl(shifts, 5), "p25": pctl(shifts, 25),
        "median": statistics.median(shifts), "p75": pctl(shifts, 75),
        "p95": pctl(shifts, 95), "max": max(shifts),
    }, recs

nonet, recs_nonet = run(False)
net, recs_net = run(True)
by_id = {r["record_id"]: r for r in recs_nonet}
declined_ids = [r["record_id"] for r in recs_nonet if r["declined"]]
detail = []
for rid in sorted(declined_ids):
    a, b = by_id[rid], next(r for r in recs_net if r["record_id"] == rid)
    detail.append({"record_id": rid, "label": a["label"], "site": a["site"],
                   "stored_lon": a["stored_lon"], "stored_lat": a["stored_lat"],
                   "no_grid_shift_m": a["shift_m"],
                   "with_grid_lon": b["fixed_lon"], "with_grid_lat": b["fixed_lat"],
                   "with_grid_shift_m": b["shift_m"]})

out = {"pyproj": pyproj.__version__, "proj": pyproj.proj_version_str,
       "grids_absent": nonet, "grids_present": net,
       "the_24_records": detail}
(RD / "s4-geodesic.json").write_text(json.dumps(out, indent=2))
with (RD / "s4-all-7720-geodesic.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(recs_net[0].keys())); w.writeheader(); w.writerows(recs_net)

for k in ("grids_absent", "grids_present"):
    d = out[k]
    print(f"\n=== {k} === ops {d['n_ops_available']} avail / {d['n_ops_unavailable']} unavail")
    print(f"    selected: {d['selected']}  accuracy {d['selected_accuracy_m']} m")
    print(f"    declined {d['declined']}   moved {d['moved']}")
    print(f"    min {d['min']:.1f}  p5 {d['p5']:.1f}  p25 {d['p25']:.1f}  "
          f"median {d['median']:.1f}  p75 {d['p75']:.1f}  p95 {d['p95']:.1f}  max {d['max']:.1f}")
print(f"\n=== the 24, once the Alaska grid is present ===")
for d in detail:
    print(f"  {d['record_id']:<7} {d['label'][:40]:<40} "
          f"({d['stored_lon']}, {d['stored_lat']}) -> "
          f"({d['with_grid_lon']:.6f}, {d['with_grid_lat']:.6f})  {d['with_grid_shift_m']:7.1f} m")
