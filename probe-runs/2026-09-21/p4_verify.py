#!/usr/bin/env python3
"""Independently verify the lead claim in P4_DIAGNOSIS.md, using the REAL
nad27_stored_as_wgs84.csv (which the prior run could not find and substituted for).

Claim under test: the 24 'uncorrectable' records in NAD27_IMPACT.md are not
outside NADCON coverage - they failed because us_noaa_alaska.tif was absent.
"""
import csv, os, json, pathlib, statistics, sys

SP = pathlib.Path(__file__).parent
os.environ.setdefault("PROJ_USER_WRITABLE_DIRECTORY", str(SP / "projdata"))
(SP / "projdata").mkdir(exist_ok=True)

import pyproj
from pyproj import Geod, Transformer
from pyproj.transformer import TransformerGroup

CSV = pathlib.Path("/Users/adiitii05/Downloads/nad27_stored_as_wgs84 - nad27_stored_as_wgs84.csv")
rows = list(csv.DictReader(CSV.open()))
print(f"real CSV rows: {len(rows)}")
print(f"columns: {len(rows[0])}")

GEOD = Geod(ellps="WGS84")

def report_group(tag):
    g = TransformerGroup(4267, 4326, always_xy=True)
    sel = g.transformers[0]
    print(f"\n[{tag}] network={pyproj.network.is_network_enabled()}")
    print(f"   available ops   : {len(g.transformers)}")
    print(f"   unavailable ops : {len(g.unavailable_operations)}")
    print(f"   PROJ selects    : {sel.description}")
    print(f"   declared accuracy: {sel.accuracy} m")
    for op in g.unavailable_operations[:3]:
        miss = [gr.short_name for gr in op.grids if not gr.available]
        print(f"     unavailable: {op.name[:58]}  missing={miss}")
    return sel.description, sel.accuracy

def run_all(tag):
    """Transform every stored coordinate; return per-record geodesic shift."""
    t = Transformer.from_crs(4267, 4326, always_xy=True)
    out = []
    for r in rows:
        lon = float(r["stored_lon_read_as_wgs84"])
        lat = float(r["stored_lat_read_as_wgs84"])
        x, y = t.transform(lon, lat)
        noop = (x == lon and y == lat)
        _, _, d = GEOD.inv(lon, lat, x, y)
        out.append({"site_id": r["site_id"], "record_id": r["record_id"],
                    "name": r["site_name"], "lon": lon, "lat": lat,
                    "fx": x, "fy": y, "shift": d, "noop": noop,
                    "her_shift": float(r["shift_m"]) if r["shift_m"] else None,
                    "her_lat": float(r["corrected_lat_wgs84"]) if r["corrected_lat_wgs84"] else None,
                    "her_lon": float(r["corrected_lon_wgs84"]) if r["corrected_lon_wgs84"] else None})
    noops = [o for o in out if o["noop"]]
    sh = [o["shift"] for o in out if not o["noop"]]
    print(f"   records            : {len(out)}")
    print(f"   transform declined : {len(noops)}")
    print(f"   shift min/med/max  : {min(sh):.1f} / {statistics.median(sh):.1f} / {max(sh):.1f} m")
    return out, noops

print("\n" + "=" * 72)
print("A) GRIDS ABSENT (network off) - reproduces the NAD27_IMPACT.md environment")
print("=" * 72)
pyproj.network.set_network_enabled(False)
desc_off, acc_off = report_group("no-grid")
out_off, noop_off = run_all("no-grid")
if noop_off:
    print(f"   declined records ({len(noop_off)}):")
    for o in noop_off[:30]:
        print(f"      {o['record_id']:<8} ({o['lon']:>10.4f},{o['lat']:>8.4f})  {o['name'][:40]}")

print("\n" + "=" * 72)
print("B) GRIDS AVAILABLE (network on, PROJ may fetch us_noaa_alaska)")
print("=" * 72)
pyproj.network.set_network_enabled(True)
desc_on, acc_on = report_group("grid")
out_on, noop_on = run_all("grid")
if noop_on:
    print(f"   STILL declined ({len(noop_on)}):")
    for o in noop_on[:30]:
        print(f"      {o['record_id']:<8} ({o['lon']:>10.4f},{o['lat']:>8.4f})  {o['name'][:40]}")

# --- independent check of HER arithmetic in the CSV ---
print("\n" + "=" * 72)
print("C) CROSS-CHECK: does my transform reproduce her corrected_lat/lon and shift_m?")
print("=" * 72)
for tag, out in (("grids absent", out_off), ("grids present", out_on)):
    dpos, dsh, n = [], [], 0
    for o in out:
        if o["her_lat"] is None:
            continue
        n += 1
        _, _, d = GEOD.inv(o["fx"], o["fy"], o["her_lon"], o["her_lat"])
        dpos.append(d)
        if o["her_shift"] is not None:
            dsh.append(abs(o["shift"] - o["her_shift"]))
    print(f"  [{tag}] n={n}")
    print(f"     my corrected point vs hers : median {statistics.median(dpos):.3f} m, "
          f"max {max(dpos):.3f} m")
    print(f"     my shift vs her shift_m    : median {statistics.median(dsh):.3f} m, "
          f"max {max(dsh):.3f} m")

json.dump({"grids_absent": {"op": desc_off, "accuracy": acc_off, "declined": len(noop_off),
                            "declined_ids": [o["record_id"] for o in noop_off]},
           "grids_present": {"op": desc_on, "accuracy": acc_on, "declined": len(noop_on),
                             "declined_ids": [o["record_id"] for o in noop_on]}},
          (SP / "p4_verify.json").open("w"), indent=1)
print("\nwrote p4_verify.json")
