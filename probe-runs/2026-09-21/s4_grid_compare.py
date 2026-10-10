#!/usr/bin/env python3
"""Section 4, part 2: what does the fix actually give -- a NADCON result or a
20 m approximation? Run the corrected transform twice, once with PROJ network
grid access off (this machine's default) and once with it on, and compare.
"""
import csv, json, math, os, pathlib, statistics, sys
import pyproj
from pyproj import Transformer
from pyproj.transformer import TransformerGroup

RD = pathlib.Path(sys.argv[1]); SRC = pathlib.Path(sys.argv[2])
WANT_NET = sys.argv[3] == "net"
pyproj.network.set_network_enabled(WANT_NET)

g = TransformerGroup(4267, 4326, always_xy=True)
info = {
    "network_enabled": pyproj.network.is_network_enabled(),
    "pyproj": pyproj.__version__, "proj": pyproj.proj_version_str,
    "n_available": len(g.transformers), "n_unavailable": len(g.unavailable_operations),
    "selected_description": g.transformers[0].description,
    "selected_accuracy_m": g.transformers[0].accuracy,
    "alaska_grid_missing": any(
        "us_noaa_alaska.tif" in [gr.short_name for gr in op.grids if not gr.available]
        for op in g.unavailable_operations),
}
T = Transformer.from_crs(4267, 4326, always_xy=True)

def metres(lo0, la0, lo1, la1):
    return math.hypot((la1 - la0) * 111_320.0,
                      (lo1 - lo0) * 111_320.0 * math.cos(math.radians((la0 + la1) / 2)))

shifts, declined, pts = [], 0, {}
for r in csv.DictReader(SRC.open()):
    lon, lat = (float(v) for v in r["wkt"][r["wkt"].index("(") + 1:r["wkt"].index(")")].split())
    x, y = T.transform(lon, lat)
    d = metres(lon, lat, x, y)
    pts[r["record_id"]] = (x, y)
    if x == lon and y == lat:
        declined += 1
    else:
        shifts.append(d)
info.update({
    "fix_declined_count": declined, "fix_moved_count": len(shifts),
    "median_shift_m": statistics.median(shifts),
    "min_shift_m": min(shifts), "max_shift_m": max(shifts),
})
(RD / f"s4-grid-{'net' if WANT_NET else 'nonet'}.json").write_text(
    json.dumps({"info": info, "points": pts}, indent=2))
print(json.dumps(info, indent=2))
