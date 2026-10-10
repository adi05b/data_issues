#!/usr/bin/env python3
"""Section 4: over all 7,720 stored ARDF coordinates, which ones does the
corrected transform decline to move, and how far does it move the rest?

Input is n2-nad27-coords-all.csv from probe-runs/2026-09-14 -- the verbatim WKT
the graph returned. The brief names nad27_stored_as_wgs84.csv; that file does
not exist in this folder (see P4_DIAGNOSIS.md, 'Inputs').
"""
import csv, json, math, pathlib, statistics, sys
import shapely.ops
from shapely.wkt import loads
from pyproj import Transformer

RD = pathlib.Path(sys.argv[1])
SRC = pathlib.Path(sys.argv[2])

T_NOW = Transformer.from_crs(4267, 4326)                  # as geo.py is written
T_FIX = Transformer.from_crs(4267, 4326, always_xy=True)  # as it should be

def metres(lon0, lat0, lon1, lat1):
    dlat = (lat1 - lat0) * 111_320.0
    dlon = (lon1 - lon0) * 111_320.0 * math.cos(math.radians((lat0 + lat1) / 2))
    return math.hypot(dlat, dlon)

rows = list(csv.DictReader(SRC.open()))
out, declined, shifts = [], [], []
for r in rows:
    g = loads(r["wkt"])
    now = shapely.ops.transform(T_NOW.transform, g)
    fix = shapely.ops.transform(T_FIX.transform, g)
    d = metres(g.x, g.y, fix.x, fix.y)
    rec = {
        "site": r["site"], "record_id": r["record_id"], "label": r["label"],
        "source_id": r["source"], "crs_obs": r["crs_obs"], "wkt": r["wkt"],
        "stored_lon": g.x, "stored_lat": g.y,
        "current_lon": now.x, "current_lat": now.y,
        "fixed_lon": fix.x, "fixed_lat": fix.y,
        "shift_m": d,
        "current_is_noop": (now.x == g.x and now.y == g.y),
        "fix_declined": (fix.x == g.x and fix.y == g.y),
        "fix_finite": math.isfinite(fix.x) and math.isfinite(fix.y),
    }
    out.append(rec)
    if rec["fix_declined"]:
        declined.append(rec)
    else:
        shifts.append(d)

with (RD / "s4-all-7720.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)

def pct(v, p):
    v = sorted(v)
    k = (len(v) - 1) * p / 100
    lo, hi = math.floor(k), math.ceil(k)
    return v[lo] if lo == hi else v[lo] + (v[hi] - v[lo]) * (k - lo)

summary = {
    "records": len(out),
    "current_code_noop_count": sum(r["current_is_noop"] for r in out),
    "current_code_noop_pct": 100.0 * sum(r["current_is_noop"] for r in out) / len(out),
    "fix_declined_count": len(declined),
    "fix_moved_count": len(shifts),
    "fix_nonfinite_count": sum(not r["fix_finite"] for r in out),
    "shift_m_over_moved_only": {
        "min": min(shifts), "p5": pct(shifts, 5), "p25": pct(shifts, 25),
        "median": statistics.median(shifts), "p75": pct(shifts, 75),
        "p95": pct(shifts, 95), "max": max(shifts),
    },
    "shift_m_over_all_7720": {
        "min": min(r["shift_m"] for r in out),
        "median": statistics.median([r["shift_m"] for r in out]),
        "max": max(r["shift_m"] for r in out),
    },
    "declined_records": [
        {"record_id": d["record_id"], "label": d["label"],
         "stored_lon": d["stored_lon"], "stored_lat": d["stored_lat"]}
        for d in sorted(declined, key=lambda d: d["record_id"])
    ],
}
(RD / "s4-summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps({k: v for k, v in summary.items() if k != "declined_records"}, indent=2))
print(f"\n=== {len(declined)} records the corrected transform DECLINED to move ===")
for d in summary["declined_records"]:
    print(f"  {d['record_id']:<8} {d['label'][:52]:<52} "
          f"({d['stored_lon']}, {d['stored_lat']})")
