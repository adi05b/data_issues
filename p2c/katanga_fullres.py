#!/usr/bin/env python3
"""Katanga dry run with full-resolution gbOpen ADM1 (DR Congo), compared with the
simplified run in katanga_points.csv (written by boundary_match.py).

Same usability rules, except a MULTIPOINT now counts if all its points fall in
the same shape (as in coverage.py). Writes katanga_points_fullres.csv and
prints the counts and every point whose province changes.
"""

import collections
import csv
import json
from pathlib import Path

from shapely import wkt
from shapely.geometry import MultiPoint, Point, shape
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
feats = json.load(open(HERE / "geoboundaries_full/COD_ADM1.geojson", encoding="utf-8"))["features"]
shapes = [(f["properties"]["shapeName"], shape(f["geometry"])) for f in feats]
union = unary_union([g for _, g in shapes])

rows = list(csv.DictReader(open(HERE / "katanga_points.csv", newline="", encoding="utf-8")))
out, changes = [], []
for r in rows:
    new = dict(r)
    if r["status"] == "usable":
        g = wkt.loads(r["location"])
        pts = [g] if isinstance(g, Point) else list(g.geoms)
        hit = {n for n, s in shapes for p in pts if s.contains(p)}
        new["shape_fullres"] = hit.pop() if len(hit) == 1 else ("none" if not hit else " | ".join(sorted(hit)))
        new["inside_cod_fullres"] = all(union.contains(p) for p in pts)
        new["distance_to_cod_km"] = round(min(union.distance(p) for p in pts) * 111, 1)
        if new["shape_fullres"] != r["shape"]:
            changes.append({k: new[k] for k in ("group", "source_id", "record_id", "location", "shape", "shape_fullres")})
    out.append(new)

with open(HERE / "katanga_points_fullres.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0]) if "shape_fullres" in out[0] else list(out[-1]), extrasaction="ignore")
    fields = list(rows[0]) + ["shape_fullres", "inside_cod_fullres", "distance_to_cod_km"]
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(out)

res = {}
for grp in sorted({r["group"] for r in out}):
    g = [r for r in out if r["group"] == grp]
    res[grp] = {"records": len(g),
                "simplified": dict(collections.Counter(r.get("shape") or r["status"] for r in g)),
                "fullres": dict(collections.Counter(r.get("shape_fullres") or r["status"] for r in g))}
res["changed"] = changes
res["outside_cod_fullres"] = [{k: r[k] for k in ("group", "location", "flag", "distance_to_cod_km")}
                              for r in out if r["status"] == "usable" and str(r["inside_cod_fullres"]) == "False"]
(HERE / "katanga_fullres_results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
print(json.dumps(res, indent=1, ensure_ascii=False))
