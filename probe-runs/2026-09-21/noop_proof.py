#!/usr/bin/env python3
"""The clean confirmation: force the swapped point INSIDE NAD27's area of use
and the no-op should disappear. If it does, the area-of-use explanation is the
right one and the 'invalid latitude' explanation is not.

NAD27 area of use: lon [167.65, 180] U [-180, -47.74], lat [7.15, 83.17].
A record at (lon=20, lat=-60) swaps to (lat=20, lon=-60) -- inside. No real
mineral site is there; the point is to isolate the mechanism.
"""
import json, pathlib, sys
from pyproj import CRS, Transformer

RD = pathlib.Path(sys.argv[1])
cases = [
    ("swap lands INSIDE NAD27 aou", 4267, 20.0, -60.0),
    ("swap lands OUTSIDE NAD27 aou (a real Alaska record)", 4267, -148.9, 63.91),
    ("swap lands OUTSIDE NAD27 aou (a hypothetical CONUS record)", 4267, -80.0, 35.0),
    ("swap lands INSIDE NAD83 aou", 4269, 20.0, -60.0),
    ("swap lands OUTSIDE NAD83 aou (a hypothetical CONUS record)", 4269, -80.0, 35.0),
]
out = []
for why, code, lon, lat in cases:
    t_bug = Transformer.from_crs(code, 4326)
    t_fix = Transformer.from_crs(code, 4326, always_xy=True)
    bug, fix = t_bug.transform(lon, lat), t_fix.transform(lon, lat)
    out.append({"case": why, "epsg": code, "in_lon": lon, "in_lat": lat,
                "bug_out": list(bug), "fix_out": list(fix),
                "noop": bug[0] == lon and bug[1] == lat})
    print(f"{why}\n  EPSG:{code} in=({lon}, {lat})  noop={out[-1]['noop']}  "
          f"bug_out={[round(v,6) for v in bug]}")

# And: can a real mineral site ever make the swap land inside NAD27's aou?
aou = CRS.from_epsg(4267).area_of_use.bounds
print(f"\nNAD27 area of use bounds (w,s,e,n) = {aou}")
print("For the swap to land inside, a record needs lon in [7.15, 83.17] AND")
print("lat in [167.65,180] U [-180,-47.74].  lat<=90, so lat in [-90,-47.74]:")
print("  -> lon 7-83E and lat 48-90S: the Antarctic sector south of the Indian Ocean.")
print("  -> no NAD27 mineral site can be there. The no-op is unconditional in practice.")
(RD / "noop_proof.json").write_text(json.dumps(out, indent=2))
