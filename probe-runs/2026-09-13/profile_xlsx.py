#!/usr/bin/env python3
"""Profile Adriana's coord_out_of_range export. Read-only."""
import csv, re, collections, pathlib

SRC = pathlib.Path("/Users/adiitii05/Downloads/coord_out_of_range - coord_out_of_range.csv")
rows = list(csv.DictReader(SRC.open()))
print("total rows:", len(rows))
print("columns:", list(rows[0].keys()))

def tag(refid):
    # site__<sourceslug>__<recordid>__<team>
    parts = refid.split("__")
    return parts[-1] if len(parts) >= 3 else "(none)"

def slug(refid):
    parts = refid.split("__")
    return parts[1] if len(parts) >= 3 else "(none)"

by_source = collections.Counter()
by_crs = collections.Counter()
by_tag = collections.Counter()
by_src_crs_tag = collections.Counter()
for r in rows:
    by_source[r["source_id"]] += 1
    by_crs[r["source_crs"]] += 1
    by_tag[tag(r["refid"])] += 1
    by_src_crs_tag[(r["source_id"], r["source_crs"], tag(r["refid"]))] += 1

print("\n=== by source_id ===")
for k, v in by_source.most_common():
    print(f"{v:>8}  {k!r}")
print("\n=== by source_crs ===")
for k, v in by_crs.most_common():
    print(f"{v:>8}  {k!r}")
print("\n=== by team tag (from refid) ===")
for k, v in by_tag.most_common():
    print(f"{v:>8}  {k!r}")
print("\n=== by (source, crs, tag) ===")
for k, v in by_src_crs_tag.most_common():
    print(f"{v:>8}  {k}")

# Are stored_lat/stored_lon transposed? lat should be in [-90,90].
bad_lat = sum(1 for r in rows if abs(float(r["stored_lat"])) > 90)
lon_ok_as_lat = sum(1 for r in rows if abs(float(r["stored_lon"])) <= 90)
swap_fixes = sum(1 for r in rows
                 if abs(float(r["stored_lat"])) > 90 and abs(float(r["stored_lon"])) <= 90)
print(f"\nstored_lat out of [-90,90]      : {bad_lat} / {len(rows)}")
print(f"stored_lon within [-90,90]      : {lon_ok_as_lat} / {len(rows)}")
print(f"a plain column swap fixes        : {swap_fixes} / {len(rows)}")

# Range of each column - a swapped pair looks like lat holding lon and vice versa.
lats = [float(r["stored_lat"]) for r in rows]
lons = [float(r["stored_lon"]) for r in rows]
print(f"\nstored_lat range: {min(lats):.5f} .. {max(lats):.5f}")
print(f"stored_lon range: {min(lons):.5f} .. {max(lons):.5f}")

# Same, split by source.
print("\n=== per-source column ranges ===")
per = collections.defaultdict(list)
for r in rows:
    per[r["source_id"]].append((float(r["stored_lat"]), float(r["stored_lon"])))
for k, v in per.items():
    la = [a for a, b in v]; lo = [b for a, b in v]
    print(f"{k}\n    stored_lat {min(la):>12.5f} .. {max(la):>12.5f}   "
          f"stored_lon {min(lo):>11.5f} .. {max(lo):>11.5f}   n={len(v)}")

# Distinct refid prefixes -> which source slugs appear
print("\n=== refid source slugs ===")
for k, v in collections.Counter(slug(r["refid"]) for r in rows).most_common():
    print(f"{v:>8}  {k}")
