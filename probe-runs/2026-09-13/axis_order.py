#!/usr/bin/env python3
"""Which pyproj call signature reproduces the observed stored_lat/stored_lon?

Observed for Harts Draw (OFR-757 record 0), EPSG:26912, easting 632887 northing 4199554:
    stored_lat = -109.4878352   (a longitude)
    stored_lon =   37.93385228  (a latitude)
"""
from pyproj import Transformer, CRS

E, N, CRS_IN = 632887.0, 4199554.0, "EPSG:26912"
OBS_LAT, OBS_LON = -109.4878352, 37.93385228

print(f"EPSG:4326 declared axis order: "
      f"{[a.abbrev for a in CRS.from_epsg(4326).axis_info]}  (lat,lon officially)\n")

cases = {
    "Transformer(always_xy=True).transform(E,N)":
        Transformer.from_crs(CRS_IN, "EPSG:4326", always_xy=True).transform(E, N),
    "Transformer(always_xy=False).transform(E,N)":
        Transformer.from_crs(CRS_IN, "EPSG:4326").transform(E, N),
}

for label, out in cases.items():
    a, b = out
    print(f"{label}")
    print(f"    returns ({a:.7f}, {b:.7f})")
    for unpack, (lat, lon) in {"lat, lon = ...": (a, b), "lon, lat = ...": (b, a)}.items():
        hit = abs(lat - OBS_LAT) < 1e-6 and abs(lon - OBS_LON) < 1e-6
        print(f"      {unpack:<16} -> lat={lat:>12.7f} lon={lon:>12.7f}   "
              f"{'*** REPRODUCES THE BUG ***' if hit else 'no'}")
    print()
