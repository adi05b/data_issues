#!/usr/bin/env python3
"""Write ta2-minmod-kg's minmodkg/misc/katanga_successors.geojson: the four
post-2015 successors of Katanga from gbHumanitarian_COD_ADM1.geojson, with
MinMod ids (checked against state_or_province.csv) and coordinates rounded to
6 decimals.

    python extract_katanga_successors.py <out.geojson> <state_or_province.csv>
"""

import csv
import json
import sys
from pathlib import Path

from shapely.geometry import shape

HERE = Path(__file__).resolve().parent
NAMES = {"Haut-Katanga": "Q3000", "Haut-Lomami": "Q3001", "Lualaba": "Q3012", "Tanganyika": "Q3021"}

out, states_csv = map(Path, sys.argv[1:3])
rows = {r["minmod_id"]: r for r in csv.DictReader(open(states_csv, newline="", encoding="utf-8"))}
for name, qid in NAMES.items():
    assert rows[qid]["name"] == name and rows[qid]["country_name"] == "Democratic Republic of the Congo", qid

src = json.load(open(HERE / "gbHumanitarian_COD_ADM1.geojson", encoding="utf-8"))
meta = json.load(open(HERE / "api_gbHumanitarian_COD_ADM1.json", encoding="utf-8"))


def rnd(c):
    return [rnd(x) for x in c] if isinstance(c[0], list) else [round(c[0], 6), round(c[1], 6)]


feats = {}
for f in src["features"]:
    name = f["properties"]["shapeName"]
    if name in NAMES:
        geom = {"type": f["geometry"]["type"], "coordinates": rnd(f["geometry"]["coordinates"])}
        assert shape(geom).is_valid, name
        feats[name] = {"type": "Feature", "properties": {"minmod_id": NAMES[name], "name": name}, "geometry": geom}
assert feats.keys() == NAMES.keys()

lines = [
    "{",
    '"type": "FeatureCollection",',
    '"attribution": "Province boundaries: OCHA / Référentiel Géographique Commun, via HDX and geoBoundaries (gbHumanitarian), CC BY 3.0 IGO.",',
    f'"source": {json.dumps(meta["gjDownloadURL"])},',
    '"features": [',
    ",\n".join(json.dumps(feats[n], ensure_ascii=False, separators=(",", ":")) for n in sorted(feats, key=NAMES.get)),
    "]",
    "}",
]
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(out, out.stat().st_size, "bytes")
