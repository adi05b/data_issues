#!/usr/bin/env python3
"""Download full-resolution (non-simplified) gbOpen ADM1 GeoJSON for the given
ISO3 codes into geoboundaries_full/, using the gjDownloadURL in the API index
already saved at geoboundaries/api_ALL_ADM1.json. Reports codes with no gbOpen ADM1.

    python fetch_full_res.py COD FRA ...
"""

import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "geoboundaries_full"
OUT.mkdir(exist_ok=True)
meta = {m["boundaryISO"]: m for m in json.load(open(HERE / "geoboundaries/api_ALL_ADM1.json", encoding="utf-8"))}
for iso3 in sys.argv[1:]:
    dest = OUT / f"{iso3}_ADM1.geojson"
    if iso3 not in meta:
        print(f"{iso3}: no gbOpen ADM1")
        continue
    if not dest.exists():
        with urllib.request.urlopen(meta[iso3]["gjDownloadURL"], timeout=300) as r:  # default TLS verification
            dest.write_bytes(r.read())
    print(f"{iso3}: {dest.stat().st_size:,} bytes")
