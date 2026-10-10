#!/usr/bin/env python3
"""The decisive test: raw graph record vs merged spreadsheet entity, side by side.

For each record present in BOTH the saved SPARQL snapshots and Adriana's export:
  - reproject the raw (easting, northing) from its declared CRS to EPSG:4326
  - compare the result against what the spreadsheet stores in stored_lat/stored_lon
  - report the residual under the as-written reading and under the swapped reading
"""
import csv, pathlib, collections
from pyproj import Transformer

HERE = pathlib.Path(__file__).parent
SHEET = pathlib.Path("/Users/adiitii05/Downloads/coord_out_of_range - coord_out_of_range.csv")
PREFIX = "https://minmod.isi.edu/resource/"

sheet = {r["refid"]: r for r in csv.DictReader(SHEET.open())}
raw = list(csv.DictReader((HERE / "raw_outofrange.csv").open()))

transformers = {}
def to_wgs84(crs, east, north):
    """Return (lon, lat) in EPSG:4326 for a coordinate in `crs`."""
    if crs not in transformers:
        transformers[crs] = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    return transformers[crs].transform(east, north)

matched, unmatched = [], []
for r in raw:
    refid = r["site"].replace(PREFIX, "")
    row = sheet.get(refid)
    if row is None:
        unmatched.append(refid)
        continue
    east, north = float(r["east"]), float(r["north"])
    crs = r["crs"] or row["source_crs"]
    s_lat, s_lon = float(row["stored_lat"]), float(row["stored_lon"])
    if crs == "EPSG:4326":
        lon, lat = east, north          # nothing to reproject
    else:
        lon, lat = to_wgs84(crs, east, north)
    matched.append({
        "refid": refid, "name": row["name_val"], "source": row["source_id"], "crs": crs,
        "east": east, "north": north, "lon": lon, "lat": lat,
        "s_lat": s_lat, "s_lon": s_lon,
        # residual if the spreadsheet columns mean what they are named
        "d_asis": max(abs(s_lat - lat), abs(s_lon - lon)),
        # residual if stored_lat actually holds lon and stored_lon actually holds lat
        "d_swap": max(abs(s_lat - lon), abs(s_lon - lat)),
    })

print(f"raw records recovered   : {len(raw)}")
print(f"matched into spreadsheet: {len(matched)}")
print(f"not in spreadsheet      : {len(unmatched)}  (dedup collapsed them onto another refid)")

print("\n=== verdict per record ===")
swap_wins = sum(1 for m in matched if m["d_swap"] < m["d_asis"])
print(f"swapped reading closer than as-written reading: {swap_wins} / {len(matched)}")
close = sum(1 for m in matched if m["d_swap"] < 1e-4)
print(f"swapped reading agrees to < 1e-4 deg (~11 m)  : {close} / {len(matched)}")

print("\n=== side-by-side (all matched) ===")
hdr = (f"{'name':<28} {'crs':<11} {'raw easting':>14} {'raw northing':>14} "
       f"{'reproj lon':>12} {'reproj lat':>11} {'stored_lat':>12} {'stored_lon':>11} "
       f"{'d_asis':>10} {'d_swap':>9}")
print(hdr); print("-" * len(hdr))
for m in sorted(matched, key=lambda m: (m["source"], m["name"]))[:60]:
    print(f"{m['name'][:28]:<28} {m['crs']:<11} {m['east']:>14.2f} {m['north']:>14.2f} "
          f"{m['lon']:>12.6f} {m['lat']:>11.6f} {m['s_lat']:>12.6f} {m['s_lon']:>11.6f} "
          f"{m['d_asis']:>10.4f} {m['d_swap']:>9.2e}")

print("\n=== by source ===")
per = collections.defaultdict(list)
for m in matched:
    per[m["source"]].append(m)
for k, v in per.items():
    sw = sum(1 for m in v if m["d_swap"] < m["d_asis"])
    worst = max(m["d_swap"] for m in v)
    print(f"{k}\n    n={len(v)}  swap-wins={sw}  worst d_swap={worst:.3e} deg")

with (HERE / "decisive_table.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(matched[0].keys()))
    w.writeheader(); w.writerows(matched)
print("\nwrote decisive_table.csv")
