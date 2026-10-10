#!/usr/bin/env python3
"""Section 3 -- the sweep. Which CRS silently no-op under geo.py's bug?

geo.py does Transformer.from_crs(src, 4326) with no always_xy, then feeds it
(x, y) = (lon, easting) first. Two different failure modes follow, and only one
of them is visible.
"""
import json, pathlib, sys
from pyproj import CRS, Transformer
from pyproj.transformer import TransformerGroup

RD = pathlib.Path(sys.argv[1])

# Codes actually present in the corpus (A2.3-crs-census, 2026-09-03) plus every
# speculative candidate the brief names, plus a systematic 426x/427x/430x sweep.
CORPUS = {
    4326: ("EPSG:4326", 403549 + 7869 + 1, "many"),
    2994: ("EPSG:2994", 23316, "oregongeology"),
    26912: ("EPSG:26912", 7792, "OFR-757 / Utah"),
    4267: ("EPSG:4267", 7720, "ardf (doi.org/10.5066/P96MMRFD)"),
}
SPECULATIVE = [4269, 4322, 4019, 4030, 4267, 4268, 4270, 4271, 4272, 4273,
               4274, 4275, 4276, 4277, 4278, 4279, 4300, 4301, 4302, 4303,
               4304, 4305, 4306, 4307, 4308, 4309]

# One real stored coordinate per corpus CRS, for the empirical no-op test.
PROBE_XY = {
    4267: (-148.90, 63.91),      # HE015 Lignite Creek, the median ARDF record
    4326: (-110.5, 38.0),
    2994: (1_300_000.0, 300_000.0),   # plausible Oregon South ft-ish easting/northing
    26912: (500_000.0, 4_200_000.0),  # UTM 12N central meridian, Utah latitude
}

def describe(code):
    try:
        c = CRS.from_epsg(code)
    except Exception as exc:
        return {"epsg": code, "error": f"{type(exc).__name__}: {exc}"}
    aou = c.area_of_use
    return {
        "epsg": code,
        "name": c.name,
        "is_geographic": bool(c.is_geographic),
        "is_projected": bool(c.is_projected),
        "axis0_direction": c.axis_info[0].direction,
        "axis0_name": c.axis_info[0].name,
        "axis1_direction": c.axis_info[1].direction,
        "area_of_use": list(aou.bounds) if aou else None,
        "area_of_use_name": aou.name if aou else None,
    }

def noop_test(code, xy):
    """Run the transform exactly as geo.py writes it, and as it should be."""
    x, y = xy
    t_bug = Transformer.from_crs(code, 4326)
    t_fix = Transformer.from_crs(code, 4326, always_xy=True)
    bug = t_bug.transform(x, y)
    fix = t_fix.transform(x, y)
    return {
        "probe_input_xy": [x, y],
        "current_code_output": list(bug),
        "always_xy_output": list(fix),
        "current_output_is_input_unchanged": (bug[0] == x and bug[1] == y),
        "current_output_axes_swapped_vs_fix": (
            abs(bug[0] - fix[1]) < 1e-9 and abs(bug[1] - fix[0]) < 1e-9
        ),
        "current_output_nonfinite": not all(
            v == v and abs(v) != float("inf") for v in bug
        ),
    }

out = {"pyproj": __import__("pyproj").__version__,
       "proj": __import__("pyproj").proj_version_str,
       "corpus": [], "speculative": []}

for code, (label, nodes, src) in CORPUS.items():
    row = describe(code)
    row.update({"corpus_nodes_2026_09_03": nodes, "source": src})
    row.update(noop_test(code, PROBE_XY[code]))
    out["corpus"].append(row)

for code in sorted(set(SPECULATIVE)):
    row = describe(code)
    if "error" in row:
        out["speculative"].append(row)
        continue
    # probe with an Alaska-like and a mid-latitude coordinate inside its own area
    if row["area_of_use"]:
        w, s, e, n = row["area_of_use"]
        lon, lat = (w + e) / 2, (s + n) / 2
    else:
        lon, lat = -100.0, 40.0
    row.update(noop_test(code, (lon, lat)))
    out["speculative"].append(row)

# Grid availability for the one CRS that matters
g = TransformerGroup(4267, 4326, always_xy=True)
out["nad27_transformer_group"] = {
    "n_available": len(g.transformers),
    "n_unavailable": len(g.unavailable_operations),
    "selected": g.transformers[0].description if g.transformers else None,
    "selected_accuracy": g.transformers[0].accuracy if g.transformers else None,
    "available_ops": [
        {"description": t.description, "accuracy": t.accuracy}
        for t in g.transformers[:8]
    ],
    "unavailable_ops": [
        {"name": op.name,
         "missing_grids": [gr.short_name for gr in op.grids if not gr.available]}
        for op in g.unavailable_operations[:8]
    ],
}
(RD / "crs_sweep.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
