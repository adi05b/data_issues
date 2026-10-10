#!/usr/bin/env python3
"""Re-check the 270 single matches whose MinMod lat/lon fell outside the matched
shape in BOUNDARY_MATCH.md (212 outside the country, 58 inside it).

For each: where the MinMod point actually is (which country / which shape), how
far it is from the matched shape, and whether the MinMod name and the matched
shape name agree after folding (independent evidence for the match). Uses the
same simplified shapes and the same 0.05-degree slack as boundary_match.py.
Writes centroid_recheck.csv.
"""

import csv
import json
import sys
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.argv = sys.argv[:1]
sys.path.insert(0, str(HERE))
from boundary_match import fold  # noqa: E402

countries = list(csv.DictReader(open(HERE / "ta2-minmod-data/data/entities/country.csv", newline="", encoding="utf-8")))
iso2to3 = {c["iso2"]: c["iso3"] for c in countries}
meta = {m["boundaryISO"]: m for m in json.load(open(HERE / "geoboundaries/api_ALL_ADM1.json", encoding="utf-8"))}
shapes = {iso3: [(f["properties"], shape(f["geometry"])) for f in
                 json.load(open(HERE / f"geoboundaries/{iso3}_ADM1_simplified.geojson", encoding="utf-8"))["features"]]
          for iso3 in meta}
unions = {iso3: unary_union([g for _, g in fs]) for iso3, fs in shapes.items()}
match = {r["minmod_id"]: r for r in csv.DictReader(open(HERE / "state_shape_match.csv", newline="", encoding="utf-8"))}

out = []
for r in csv.DictReader(open(HERE / "centroid_check.csv", newline="", encoding="utf-8")):
    if r["inside_matched_shape"] != "False":
        continue
    pt = Point(float(r["minmod_lon"]), float(r["minmod_lat"]))
    iso3 = iso2to3[r["country_code"]]
    matched = next(g for p, g in shapes[iso3] if p["shapeName"] == r["shapeName"])
    in_country = unions[iso3].distance(pt) < 0.05
    where_country = next((i for i, u in unions.items() if u.contains(pt)), "none (sea, or a country gB lacks)")
    where_shape = next((p["shapeName"] for p, g in shapes[iso3] if g.contains(pt)), "") if in_country else ""
    out.append({
        "minmod_id": r["minmod_id"], "country_code": r["country_code"], "name": r["name"],
        "match_tier": r["match_tier"], "matched_shape": r["shapeName"],
        "shapeISO": match[r["minmod_id"]]["shapeISO"],
        "names_agree_after_folding": fold(r["name"]) == fold(r["shapeName"]),
        "minmod_lat": r["minmod_lat"], "minmod_lon": r["minmod_lon"],
        "group": "inside the country" if in_country else "outside the country",
        "point_is_in_country": iso3 if in_country else where_country,
        "point_is_in_shape": where_shape,
        "km_from_matched_shape": round(matched.distance(pt) * 111, 1),
    })

with open(HERE / "centroid_recheck.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0]))
    w.writeheader()
    w.writerows(out)
print(len(out))
