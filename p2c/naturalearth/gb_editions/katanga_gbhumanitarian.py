#!/usr/bin/env python3
"""Katanga points against geoBoundaries gbHumanitarian COD ADM1 (full resolution),
compared record by record with the gbOpen full-resolution result in
p2c/katanga_points_fullres.csv. Same points and the same usability rules
(a MULTIPOINT counts if all its points fall in one shape).

Writes katanga_points_gbhumanitarian.csv and katanga_gbhumanitarian_results.json.
"""

import collections
import csv
import json
from pathlib import Path

import shapely
from shapely import wkt
from shapely.geometry import Point, shape
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
P2C = HERE.parent.parent
KM = 111.32  # km per degree; distances are approximate


def load(p):
    return [(f["properties"]["shapeName"], shape(f["geometry"])) for f in json.load(open(p, encoding="utf-8"))["features"]]


hum = load(HERE / "gbHumanitarian_COD_ADM1.geojson")
opn = dict(load(P2C / "geoboundaries_full/COD_ADM1.geojson"))
hum_union = unary_union([g for _, g in hum])


def fold(s):
    return s.lower().replace("ï", "i").replace("é", "e").replace(" ", "-")


out = []
for r in csv.DictReader(open(P2C / "katanga_points_fullres.csv", newline="", encoding="utf-8")):
    row = {k: r[k] for k in ("group", "source_id", "record_id", "location", "status")}
    row["gbopen"] = r.get("shape_fullres") or r["status"]
    if r["status"] == "usable":
        g = wkt.loads(r["location"])
        pts = [g] if isinstance(g, Point) else list(g.geoms)
        hit = {n for n, s in hum for p in pts if s.contains(p)}
        row["gbhumanitarian"] = hit.pop() if len(hit) == 1 else ("none" if not hit else " | ".join(sorted(hit)))
        row["inside_cod_gbhumanitarian"] = all(hum_union.contains(p) for p in pts)
        p = pts[0]
        hs = dict(hum).get(row["gbhumanitarian"])
        os_ = opn.get(row["gbopen"])
        row["km_to_boundary_gbhumanitarian"] = round(hs.boundary.distance(p) * KM, 2) if hs is not None else ""
        row["km_to_boundary_gbopen"] = round(os_.boundary.distance(p) * KM, 2) if os_ is not None else ""
        row["km_to_cod_gbhumanitarian"] = round(hum_union.distance(p) * KM, 1)
    else:
        row["gbhumanitarian"] = r["status"]
    row["agree"] = fold(row["gbopen"]) == fold(row["gbhumanitarian"])
    out.append(row)

fields = ["group", "source_id", "record_id", "location", "status", "gbopen", "gbhumanitarian", "agree",
          "inside_cod_gbhumanitarian", "km_to_boundary_gbopen", "km_to_boundary_gbhumanitarian", "km_to_cod_gbhumanitarian"]
with open(HERE / "katanga_points_gbhumanitarian.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(out)

res = {
    "vertices": {"gbHumanitarian": int(sum(shapely.get_num_coordinates(g) for _, g in hum)),
                 "gbOpen": int(sum(shapely.get_num_coordinates(g) for g in opn.values()))},
    "by_group": {g: {"records": sum(1 for r in out if r["group"] == g),
                     "gbopen": dict(collections.Counter(r["gbopen"] for r in out if r["group"] == g)),
                     "gbhumanitarian": dict(collections.Counter(r["gbhumanitarian"] for r in out if r["group"] == g))}
                 for g in sorted({r["group"] for r in out})},
    "disagreements": [r for r in out if not r["agree"]],
    "outside_cod_gbhumanitarian": [{k: r[k] for k in ("record_id", "location", "km_to_cod_gbhumanitarian")}
                                   for r in out if r["status"] == "usable" and r["inside_cod_gbhumanitarian"] is False],
    "closest_to_boundary_gbhumanitarian": sorted(
        ({k: r[k] for k in ("record_id", "gbhumanitarian", "km_to_boundary_gbhumanitarian", "km_to_boundary_gbopen")}
         for r in out if r.get("km_to_boundary_gbhumanitarian") != "" and "km_to_boundary_gbhumanitarian" in r),
        key=lambda x: x["km_to_boundary_gbhumanitarian"])[:10],
}
(HERE / "katanga_gbhumanitarian_results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
print(json.dumps(res, indent=1, ensure_ascii=False))
