#!/usr/bin/env python3
"""Which NAD27->WGS84 operation does PROJ actually select for Alaska, and for
St Lawrence Island specifically? The group's first entry is the best for the
whole NAD27 extent, which is not necessarily the one an Alaska point gets.
"""
import json, pathlib, sys
import pyproj
from pyproj.aoi import AreaOfInterest
from pyproj.transformer import TransformerGroup

RD = pathlib.Path(sys.argv[1])
pyproj.network.set_network_enabled(sys.argv[2] == "net")
AOIS = {
    "whole NAD27 extent": None,
    "Alaska mainland (HE015 Lignite Creek)": (-149.0, 63.8, -148.8, 64.0),
    "St Lawrence Island (SL001-SL023)": (-172.0, 63.2, -168.8, 63.8),
    "Gareloi Island (GI001)": (-178.9, 51.7, -178.6, 51.85),
}
out = {"network": pyproj.network.is_network_enabled()}
for name, box in AOIS.items():
    kw = {} if box is None else {"area_of_interest": AreaOfInterest(*box)}
    g = TransformerGroup(4267, 4326, always_xy=True, **kw)
    top = [{"description": t.description, "accuracy_m": t.accuracy} for t in g.transformers[:3]]
    out[name] = {"n_available": len(g.transformers),
                 "n_unavailable": len(g.unavailable_operations), "top3": top}
    print(f"\n{name}:  {len(g.transformers)} available / {len(g.unavailable_operations)} unavailable")
    for t in top:
        print(f"    {t['accuracy_m']!s:>6} m   {t['description']}")
(RD / f"s4-which-op-{'net' if pyproj.network.is_network_enabled() else 'nonet'}.json").write_text(json.dumps(out, indent=2))
