#!/usr/bin/env python3
"""Section 3: run geo.py's conversion both ways on the REAL stored strings.

The WKT is passed to shapely.wkt.loads exactly as the graph returned it -
not rounded, reformatted, or rebuilt from parsed numbers.
"""
import csv, pathlib, statistics, collections
import shapely.ops
from shapely.wkt import loads
from pyproj import Transformer
from math import cos, radians

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-14")
rows = list(csv.DictReader((RD / "n2-nad27-coords-all.csv").open()))
print(f"records: {len(rows)}")

# built once, exactly as geo.py would
T_NOW   = Transformer.from_crs(4267, 4326)
T_FIXED = Transformer.from_crs(4267, 4326, always_xy=True)

def both_ways(wkt):
    g = loads(wkt)
    now   = shapely.ops.transform(T_NOW.transform,   g)
    fixed = shapely.ops.transform(T_FIXED.transform, g)
    dlat = (fixed.y - now.y) * 111_000
    dlon = (fixed.x - now.x) * 111_000 * cos(radians(fixed.y))
    return now, fixed, (dlat ** 2 + dlon ** 2) ** 0.5

out, failures = [], []
for r in rows:
    try:
        now, fixed, d = both_ways(r["wkt"])
    except Exception as e:
        failures.append((r["site"], r["wkt"], f"{type(e).__name__}: {e}"))
        continue
    g = loads(r["wkt"])
    out.append({
        "site": r["site"], "record_id": r["record_id"], "label": r["label"],
        "wkt": r["wkt"], "in_lon": g.x, "in_lat": g.y,
        "now_x": now.x, "now_y": now.y, "fixed_x": fixed.x, "fixed_y": fixed.y,
        "shift_m": d,
        "now_unchanged": abs(now.x - g.x) < 1e-12 and abs(now.y - g.y) < 1e-12,
        "fixed_finite": all(abs(v) < 1e30 for v in (fixed.x, fixed.y)),
    })

print(f"converted: {len(out)}   failures: {len(failures)}")
for s, w, e in failures[:5]:
    print("   FAIL", s.split('__')[-2], w[:40], e)

shifts = [o["shift_m"] for o in out if o["fixed_finite"]]
print(f"\n=== SHIFT DISTRIBUTION (metres) ===")
print(f"   n        {len(shifts)}")
print(f"   min      {min(shifts):.1f}")
print(f"   median   {statistics.median(shifts):.1f}")
print(f"   mean     {statistics.mean(shifts):.1f}")
print(f"   max      {max(shifts):.1f}")
for p in (5, 25, 75, 95, 99):
    print(f"   p{p:<7} {statistics.quantiles(shifts, n=100)[p-1]:.1f}")

unchanged = sum(1 for o in out if o["now_unchanged"])
print(f"\ncurrent code returns the input UNCHANGED: {unchanged} / {len(out)} "
      f"({100*unchanged/len(out):.2f}%)")
nonfinite = [o for o in out if not o["fixed_finite"]]
print(f"non-finite results after the fix        : {len(nonfinite)}")

print("\n=== spread by longitude band (input lon) ===")
bands = collections.defaultdict(list)
for o in out:
    lo = o["in_lon"]
    b = "E of -140 (SE AK)" if lo > -140 else \
        ("-140..-150"       if lo > -150 else
        ("-150..-160"       if lo > -160 else
        ("-160..-170"       if lo > -170 else
        ("W of -170"        if lo < 0 else "POSITIVE lon (Aleutians)"))))
    bands[b].append(o["shift_m"])
for b in ["E of -140 (SE AK)", "-140..-150", "-150..-160", "-160..-170", "W of -170",
          "POSITIVE lon (Aleutians)"]:
    if b in bands:
        v = bands[b]
        print(f"   {b:<26} n={len(v):>5}  min={min(v):>6.1f}  median={statistics.median(v):>6.1f}  max={max(v):>7.1f}")

# any result that lands outside a generous Alaska box?
print("\n=== sanity: does the fixed output stay in Alaska? ===")
def in_ak(x, y):
    return (-180.1 <= x <= -128 or 168 <= x <= 180.1) and 50 <= y <= 72.5
bad = [o for o in out if not in_ak(o["fixed_x"], o["fixed_y"])]
print(f"   fixed outputs outside a generous Alaska box: {len(bad)}")
for o in bad[:8]:
    print(f"      {o['record_id']:<8} {o['wkt'][:34]:<34} -> ({o['fixed_x']:.5f}, {o['fixed_y']:.5f})")
bad_now = [o for o in out if not in_ak(o["now_x"], o["now_y"])]
print(f"   CURRENT outputs outside that box          : {len(bad_now)}")

print("\n=== named real examples (largest, median, smallest shift) ===")
srt = sorted([o for o in out if o["fixed_finite"]], key=lambda o: o["shift_m"])
for tag, o in [("SMALLEST", srt[0]), ("MEDIAN", srt[len(srt)//2]), ("LARGEST", srt[-1])]:
    print(f"\n  {tag}: {o['label'][:46]}  (record_id {o['record_id']})")
    print(f"     stored  {o['wkt']}")
    print(f"     current ({o['now_x']:.7f}, {o['now_y']:.7f})")
    print(f"     fixed   ({o['fixed_x']:.7f}, {o['fixed_y']:.7f})")
    print(f"     shift   {o['shift_m']:.1f} m")

with (RD / "n3-nad27-bothways.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
    w.writeheader(); w.writerows(out)
print(f"\nwrote n3-nad27-bothways.csv ({len(out)} rows)")
