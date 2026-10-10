#!/usr/bin/env python3
"""Why does the no-op happen, and when does it NOT happen?

The received explanation is 'the swapped point falls outside the source CRS's
area of use, so PROJ returns the input unchanged'. Test that directly, because
it predicts something different from the competing explanation ('the swapped
latitude is outside [-90, 90] and is therefore not a latitude at all').
"""
import json, pathlib, sys
from pyproj import CRS, Transformer

RD = pathlib.Path(sys.argv[1])
res = {}

for code in (4267, 4269):
    t_bug = Transformer.from_crs(code, 4326)
    t_fix = Transformer.from_crs(code, 4326, always_xy=True)
    rows = []
    # lon sweep across the whole plausible North American range, fixed sane lat
    for lon in [-179, -170, -160, -150, -140, -130, -120, -110, -100, -95,
                -91, -90.5, -90, -89.5, -89, -85, -80, -70, -60, -50, 172]:
        lat = 45.0 if -130 < lon < -60 else 60.0
        bug = t_bug.transform(lon, lat)
        fix = t_fix.transform(lon, lat)
        noop = (bug[0] == lon and bug[1] == lat)
        rows.append({
            "in_lon": lon, "in_lat": lat,
            "abs_lon_gt_90": abs(lon) > 90,
            "bug_out": list(bug), "fix_out": list(fix),
            "noop": noop,
            "bug_nonfinite": not all(v == v for v in bug),
        })
    res[code] = {"name": CRS.from_epsg(code).name, "rows": rows}

# The discriminating case: a geographic non-4326 CRS whose records sit at
# |lon| <= 90, so the swapped value IS a legal latitude.
disc = []
for code, lonlat in [(4267, (-80.0, 35.0)), (4267, (-45.0, 20.0)),
                     (4269, (-80.0, 35.0)), (4275, (2.4, 46.2)),
                     (4301, (139.7, 35.7))]:
    t_bug = Transformer.from_crs(code, 4326)
    t_fix = Transformer.from_crs(code, 4326, always_xy=True)
    lon, lat = lonlat
    bug, fix = t_bug.transform(lon, lat), t_fix.transform(lon, lat)
    # how far is the bug's answer from the right one, in degrees?
    disc.append({
        "epsg": code, "name": CRS.from_epsg(code).name,
        "in_lon": lon, "in_lat": lat, "abs_lon_le_90": abs(lon) <= 90,
        "bug_out": list(bug), "fix_out": list(fix),
        "noop": bug[0] == lon and bug[1] == lat,
        "bug_equals_swapped_fix": abs(bug[0] - fix[1]) < 1e-6 and abs(bug[1] - fix[0]) < 1e-6,
    })
res["discriminating"] = disc
(RD / "noop_mechanism.json").write_text(json.dumps(res, indent=2))

for code in (4267, 4269):
    print(f"\n=== EPSG:{code} {res[code]['name']} ===")
    print(f"{'in_lon':>8} {'in_lat':>7} {'|lon|>90':>9} {'noop':>6}  bug_out")
    for r in res[code]["rows"]:
        print(f"{r['in_lon']:>8} {r['in_lat']:>7} {str(r['abs_lon_gt_90']):>9} "
              f"{str(r['noop']):>6}  {r['bug_out']}")
print("\n=== discriminating cases (|lon| <= 90 -> swapped value is a legal latitude) ===")
for d in disc:
    print(f"EPSG:{d['epsg']:5d} in=({d['in_lon']}, {d['in_lat']}) "
          f"noop={d['noop']} bug_out={[round(v,5) for v in d['bug_out']]} "
          f"fix_out={[round(v,5) for v in d['fix_out']]}")
