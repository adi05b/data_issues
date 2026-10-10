#!/usr/bin/env python3
"""Step 2 of the Natural Earth check: does ne_10m_admin_1_states_provinces have
DR Congo's four post-2015 successor provinces of Katanga?

Lists every DR Congo feature (adm0_a3 = COD or iso_a2 = CD), and searches the
whole file, every country, for the four successor names. Writes
ne_cod_features.csv and prints the verdict. Steps 3 and 4 run only if all four
successors exist as separate features.

    python ne_katanga_check.py
"""

import csv
import json
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "src/v5.1.2/ne_10m_admin_1_states_provinces.geojson"
SUCCESSORS = {"Haut-Katanga": "Q3000", "Lualaba": "Q3012", "Haut-Lomami": "Q3001", "Tanganyika": "Q3021"}


def fold(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().replace("-", " ")


feats = json.load(open(SRC, encoding="utf-8"))["features"]
cod = [f["properties"] for f in feats if f["properties"].get("adm0_a3") == "COD" or f["properties"].get("iso_a2") == "CD"]
cod.sort(key=lambda p: p["name"] or "")
with open(HERE / "ne_cod_features.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["name", "iso_3166_2", "type_en", "name_alt", "adm1_code"])
    for p in cod:
        w.writerow([p["name"], p["iso_3166_2"], p["type_en"], p.get("name_alt") or "", p.get("adm1_code")])

found = {}
for f in feats:
    p = f["properties"]
    names = [p.get("name"), p.get("name_en"), *(p.get("name_alt") or "").split("|")]
    for s in SUCCESSORS:
        if any(fold(n) == fold(s) for n in names if n):
            found.setdefault(s, []).append(f'{p["name"]} ({p.get("adm0_a3")}, {p.get("iso_3166_2")})')

print(f"DR Congo features: {len(cod)}")
for p in cod:
    print(f'  {p["name"]} | {p["iso_3166_2"]} | {p["type_en"]} | {p.get("name_alt") or ""}')
print("single Katanga feature:", [p["iso_3166_2"] for p in cod if p["name"] == "Katanga"])
for s, q in SUCCESSORS.items():
    print(f"{s} ({q}) anywhere in the file: {found.get(s, 'not found')}")
all_four = all(any("COD" in x for x in found.get(s, [])) for s in SUCCESSORS)
print("all four successors present for DR Congo:", all_four)
if not all_four:
    print("STOP: Steps 3 and 4 skipped.")
