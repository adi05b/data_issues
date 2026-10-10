#!/usr/bin/env python3
"""Which PROJ operation actually handles each point? group[0] is the globally
best-ranked op, not necessarily the one used for a given coordinate."""
import csv, os, pathlib, collections, statistics, json
SP = pathlib.Path(__file__).parent
os.environ.setdefault("PROJ_USER_WRITABLE_DIRECTORY", str(SP / "projdata"))
import pyproj
from pyproj import Geod, Transformer

CSV = pathlib.Path("/Users/adiitii05/Downloads/nad27_stored_as_wgs84 - nad27_stored_as_wgs84.csv")
rows = list(csv.DictReader(CSV.open()))
GEOD = Geod(ellps="WGS84")
DECLINED = {"GI001"} | {f"SL{n:03d}" for n in range(1, 24)}

def per_point(enable):
    pyproj.network.set_network_enabled(enable)
    t = Transformer.from_crs(4267, 4326, always_xy=True)
    ops, per_rec = collections.Counter(), {}
    for r in rows:
        lon = float(r["stored_lon_read_as_wgs84"]); lat = float(r["stored_lat_read_as_wgs84"])
        x, y = t.transform(lon, lat)
        try:
            op = t.get_last_used_operation()
            name, acc = op.description, op.accuracy
        except Exception as e:
            name, acc = f"(unavailable: {type(e).__name__})", None
        ops[(name, acc)] += 1
        per_rec[r["record_id"]] = (name, acc, lon, lat, x, y)
    return ops, per_rec

for label, enable in (("GRIDS ABSENT", False), ("GRIDS PRESENT", True)):
    print("=" * 74); print(label); print("=" * 74)
    ops, per_rec = per_point(enable)
    print(f"{'n':>6}  {'acc(m)':>7}  operation actually used")
    for (name, acc), n in ops.most_common():
        print(f"{n:>6}  {str(acc):>7}  {name[:62]}")
    sub = [per_rec[k] for k in DECLINED if k in per_rec]
    c = collections.Counter((s[0], s[1]) for s in sub)
    print(f"\n  the 24 St Lawrence / Gareloi records specifically:")
    for (name, acc), n in c.most_common():
        print(f"     {n:>3}  acc={acc}  {name[:58]}")
    moved = sum(1 for s in sub if (s[4], s[5]) != (s[2], s[3]))
    print(f"     of these 24, actually moved: {moved}")
    print()
