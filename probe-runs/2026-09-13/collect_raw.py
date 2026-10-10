#!/usr/bin/env python3
"""Collect every out-of-range raw record captured in earlier probe runs.

Reads the saved SPARQL JSON snapshots only - the endpoint is not contacted.
Emits one row per (site URI, raw easting, raw northing, declared CRS).
"""
import json, pathlib, re, csv, collections

RUNS = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs")
POINT = re.compile(r"POINT\s*\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)")

records = {}   # site URI -> dict
seen_files = []

for jf in sorted(RUNS.glob("*/*.json")):
    if jf.name.endswith(".meta.json"):
        continue
    try:
        doc = json.loads(jf.read_text())
        bindings = doc["results"]["bindings"]
    except Exception:
        continue
    for b in bindings:
        site = None
        for key in ("site", "s"):
            if key in b and b[key]["value"].startswith("https://minmod.isi.edu/resource/site__"):
                site = b[key]["value"]
        if not site:
            continue
        # raw coordinate: either a wkt string, or separate lon/lat bindings
        east = north = crs = None
        for key in ("wkt", "location", "loc"):
            if key in b:
                m = POINT.search(b[key]["value"])
                if m:
                    east, north = float(m.group(1)), float(m.group(2))
        if east is None and "lon" in b and "lat" in b:
            try:
                east, north = float(b["lon"]["value"]), float(b["lat"]["value"])
            except ValueError:
                pass
        if east is None:
            continue
        if abs(north) <= 90:          # only out-of-range records matter here
            continue
        for key in ("crs_label", "crs", "crs_obs"):
            if key in b and b[key]["value"].startswith("EPSG"):
                crs = b[key]["value"]
        prev = records.get(site)
        if prev is None or (prev["crs"] is None and crs):
            records[site] = {"site": site, "east": east, "north": north,
                             "crs": crs, "src_file": f"{jf.parent.name}/{jf.name}"}
            seen_files.append(f"{jf.parent.name}/{jf.name}")

print(f"distinct out-of-range raw records recovered from snapshots: {len(records)}")
print("from files:")
for f, n in collections.Counter(r["src_file"] for r in records.values()).most_common():
    print(f"   {n:>4}  {f}")

out = pathlib.Path(__file__).with_name("raw_outofrange.csv")
with out.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["site", "east", "north", "crs", "src_file"])
    w.writeheader()
    for r in sorted(records.values(), key=lambda r: r["site"]):
        w.writerow(r)
print("wrote", out)
