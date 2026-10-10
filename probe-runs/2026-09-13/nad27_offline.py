#!/usr/bin/env python3
"""What can be settled about NAD27 without the endpoint.

(a) Section 5: do any NAD27 records appear in Adriana's out-of-range export?
(b) Mechanism only: how does pyproj 4267->4326 behave without always_xy?
    This is a property of pyproj, NOT a claim about any real MinMod record.
"""
import csv, collections, pathlib
import shapely.ops
from shapely.wkt import loads
from pyproj import Transformer
from math import cos, radians

SHEET = pathlib.Path("/Users/adiitii05/Downloads/coord_out_of_range - coord_out_of_range.csv")

print("=" * 72)
print("(a) SECTION 5 - NAD27 overlap with Adriana's out-of-range export")
print("=" * 72)
rows = list(csv.DictReader(SHEET.open()))
crs_counts = collections.Counter(r["source_crs"] for r in rows)
print(f"rows in export: {len(rows)}")
for k, v in crs_counts.most_common():
    print(f"   {v:>6}  {k}")
nad27 = [r for r in rows if "4267" in r["source_crs"]]
print(f"\nrows whose source_crs is EPSG:4267: {len(nad27)}")
print("VERDICT: zero overlap." if not nad27 else "VERDICT: OVERLAP EXISTS - investigate.")

print()
print("=" * 72)
print("(b) MECHANISM ONLY - pyproj 4267->4326 axis-order behaviour")
print("    Synthetic inputs. Says nothing about real MinMod records.")
print("=" * 72)

now_t   = Transformer.from_crs(4267, 4326)
fixed_t = Transformer.from_crs(4267, 4326, always_xy=True)

def both_ways(wkt):
    g = loads(wkt)
    now   = shapely.ops.transform(now_t.transform, g)
    fixed = shapely.ops.transform(fixed_t.transform, g)
    dlat = (fixed.y - now.y) * 111_000
    dlon = (fixed.x - now.x) * 111_000 * cos(radians(fixed.y))
    return now, fixed, (dlat ** 2 + dlon ** 2) ** 0.5

# Longitude-first US coordinates, east to west, as geo.py would receive them.
probes = [
    ("Maine-ish",      "POINT (-68.0 45.0)"),
    ("Virginia-ish",   "POINT (-78.5 37.5)"),
    ("Missouri-ish",   "POINT (-92.0 38.5)"),
    ("Colorado-ish",   "POINT (-105.0 39.0)"),
    ("Utah-ish",       "POINT (-111.5 39.5)"),
    ("Oregon-ish",     "POINT (-120.5 44.0)"),
]
print(f"{'probe':<15} {'input':<22} {'current output':<24} {'fixed output':<24} {'shift m':>9}")
print("-" * 98)
for name, wkt in probes:
    now, fixed, d = both_ways(wkt)
    print(f"{name:<15} {wkt:<22} "
          f"{f'({now.x:.6f}, {now.y:.6f})':<24} "
          f"{f'({fixed.x:.6f}, {fixed.y:.6f})':<24} {d:>9.1f}")

print("\nIs the current output identical to the input (i.e. transform gave up)?")
for name, wkt in probes:
    g = loads(wkt)
    now, _, _ = both_ways(wkt)
    same = (abs(now.x - g.x) < 1e-12) and (abs(now.y - g.y) < 1e-12)
    print(f"   {name:<15} unchanged={same}")

print("\nWhat does the transformer return for a longitude in the latitude slot?")
print("   raw no-always_xy transform(-105.0, 39.0) =", now_t.transform(-105.0, 39.0))
print("   raw always_xy   transform(-105.0, 39.0) =", fixed_t.transform(-105.0, 39.0))
print("   (no-always_xy reads arg1 as LATITUDE; -105 is out of domain)")
