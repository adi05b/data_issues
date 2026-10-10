"""Problem 3: Amandeep's question as one funnel, on main's own merge. Read-only.

  1  merged sites with >= 2 member records
  2  ... of which >= 2 members have a coordinate
  3  ... of which the top trust score is shared by >= 2 members with a coordinate:
         the tie main breaks by source_id / record_id. Same source vs different
         sources = the tied records come from one source_id or from several.
  4  ... of which a tied member main did not pick has strictly better real
         precision (p3_measure.ground_res_km: trailing zeros and float noise
         dropped, DMS at its grid, in the CRS's own unit)
  5  ... of which that better point lies inside the picked point's rounding box
         (half a unit of its last real digit, each axis its own), i.e. it refines
         the same spot. The rest of row 4 points somewhere else: conflicts.

Uses the definitions in p3_measure.py and the run it measured:

    CFG_FILE=<main>/tests/resources/config.yml PYTHONPATH=<main>:. \\
      .venv-p2/bin/python p3_amandeep.py run-main out
"""

from __future__ import annotations

import collections
import csv
import json
import math
import statistics
import sys
from pathlib import Path

from p3_measure import (KM_PER_DEGREE, Rec, eff_dp, ground_res_km, haversine_km, km_per_unit, load, pct,
                        rebuild_kept, xy_tokens)

GEOGRAPHIC = {"EPSG:4326", "EPSG:4267", "none"}


def half_units(r: Rec) -> tuple[float, float]:
    """Half a unit of the last real digit of r's x and y (each axis its own), in
    r's own CRS unit; a DMS-shaped record is good to its grid on both axes. For
    a multipoint, the coarsest of its points on each axis."""
    if r.dms:
        h = 0.5 / (60 if r.dms == "arcmin" else 3600)
        return h, h
    xy = xy_tokens(r.wkt)
    return tuple(0.5 * 10 ** -min(eff_dp(p[i]) for p in xy) for i in (0, 1))


def inside(picked: Rec, cand: Rec, k: float = 1.0) -> bool:
    """cand within k half-units of picked's last real digit, per axis. Same frame
    and both POINTs: compare the raw numbers as written; otherwise compare the
    WGS84 location views, with the box converted to degrees."""
    hx, hy = (k * h + 1e-9 for h in half_units(picked))
    frame = {"none": "EPSG:4326"}
    if frame.get(picked.crs, picked.crs) == frame.get(cand.crs, cand.crs) and picked.geom == cand.geom == "POINT":
        (px, py), (cx, cy) = [tuple(map(float, xy_tokens(r.wkt)[0])) for r in (picked, cand)]
        return abs(px - cx) <= hx and abs(py - cy) <= hy
    if picked.crs not in GEOGRAPHIC:
        hy = hy * km_per_unit(picked.crs) / KM_PER_DEGREE
        hx = hx * km_per_unit(picked.crs) / KM_PER_DEGREE / max(math.cos(math.radians(picked.lat)), 1e-6)
    return abs(picked.lat - cand.lat) <= hy and abs(picked.lon - cand.lon) <= hx


def selfcheck():
    def r(wkt, crs="EPSG:4326", eff=None, dms=None, lat=0.0, lon=0.0):
        nums = [n for xy in xy_tokens(wkt) for n in xy]
        e = eff if eff is not None else min(len(n.split(".")[1]) if "." in n else 0 for n in nums)
        return Rec("s", "d", "src", "r", None, wkt, crs, "POINT", e, e, False, dms, False, lat, lon)
    assert inside(r("POINT(-110.9 30.0)"), r("POINT(-110.9149 30.0142)"))      # 1 dp box is +-0.05
    assert not inside(r("POINT(-110.9 30.0)"), r("POINT(-110.96 30.0)"))
    assert inside(r("POINT(-110.9 30.0)"), r("POINT(-110.96 30.0)"), k=2)     # truncation box
    assert not inside(r("POINT(-83.08333 48)"), r("POINT(-83.16667 47.75)"))  # each axis its own box
    assert inside(r("POINT(-83.08333 48)"), r("POINT(-83.083331 47.75)"))
    assert inside(r("POINT(5 5)", dms="arcmin"), r("POINT(5.008 4.992)")) and not inside(
        r("POINT(5 5)", dms="arcmin"), r("POINT(5.01 5)"))                     # half of 1/60
    p = r("POINT(500000 4000000)", crs="EPSG:26912", eff=0, lat=36.1, lon=-111.0)
    assert inside(p, r("POINT(-111.000004 36.100004)", lat=36.100004, lon=-111.000004))  # 0.5 m ~ 4.5e-6 deg
    assert not inside(p, r("POINT(-111.00001 36.1)", lat=36.1, lon=-111.00001))


def stats(xs):
    return {"n": len(xs), "median_km": statistics.median(xs) if xs else None, "p95_km": pct(xs, 0.95),
            "max_km": max(xs, default=None), "gt_100m": sum(x > 0.1 for x in xs), "gt_1km": sum(x > 1 for x in xs),
            "gt_11km": sum(x > 11 for x in xs), "gt_50km": sum(x > 50 for x in xs)}


def main(run: Path, out: Path):
    selfcheck()
    files, _, _, _, recs, score, n_members = load(run)
    members = collections.defaultdict(list)
    for m in recs.values():
        members[m.dedup_id].append(m)
    multi = {e for e, ms in members.items() if len(ms) >= 2}
    kept = rebuild_kept(files, multi, recs)

    rows = collections.Counter()
    row5, conflicts = [], []
    for e in sorted(multi):
        ms = sorted(members[e], key=lambda m: score[m.site_id], reverse=True)  # main's order
        top = score[ms[0].site_id]
        if top.suborder.is_expert:
            rows["2 led by an expert/curator"] += 1
            continue
        tied = [m for m in ms if score[m.site_id].score == top.score]
        if len(tied) < 2:
            continue
        split = "same source" if len({m.source_id for m in tied}) == 1 else "different sources"
        rows[f"3 {split}"] += 1
        picked = kept[e]
        assert picked == tied[0], e  # main keeps the first of the tie
        better = [m for m in tied[1:] if ground_res_km(m) < ground_res_km(picked)]
        if not better:
            continue
        rows[f"4 {split}"] += 1

        def finest(lst):
            return max(lst, key=lambda m: -ground_res_km(m))  # first of equals: main's order

        refine = [m for m in better if inside(picked, m)]
        if any(inside(picked, m, k=2) for m in better):
            rows[f"5 truncation box {split}"] += 1
        new = finest(refine or better)
        row = {"dedup_site_id": e, "name": picked.name or new.name, "split": split,
               **{f"{p}_{f}": getattr(r, f) for p, r in (("picked", picked), ("better", new))
                  for f in ("site_id", "source_id", "wkt", "crs", "prec", "eff", "dms")},
               "picked_res_km": ground_res_km(picked), "better_res_km": ground_res_km(new),
               "picked_null_island": picked.null_island,
               "km": haversine_km(picked.lat, picked.lon, new.lat, new.lon)}
        if refine:
            rows[f"5 {split}"] += 1
            row5.append(row)
        else:
            conflicts.append(row)

    total = lambda n: sum(v for k, v in rows.items() if k.startswith(f"{n} ") and "truncation" not in k)  # noqa: E731
    res = {
        "1 merged sites with >= 2 member records": sum(n >= 2 for n in n_members.values()),
        "2 ... >= 2 members with a coordinate": len(multi),
        "2a ... top score held by an expert/curator (not a source tie)": rows["2 led by an expert/curator"],
        "3 ... top score tied": total(3),
        "4 ... a tied member not picked is strictly more precise": total(4),
        "5 ... and refines the picked point (inside its rounding box)": total(5),
        "4-5 conflicts (more precise, points elsewhere)": len(conflicts),
        "by split": {k: v for k, v in sorted(rows.items()) if not k.startswith("2 ")},
        "row 5 move": stats([r["km"] for r in row5]),
        "conflict distance": stats([r["km"] for r in conflicts]),
        "conflicts with a Null Island pick": sum(r["picked_null_island"] for r in conflicts),
        "row 5 better point is DMS-shaped": sum(r["better_dms"] is not None for r in row5),
        "row 5 better point is a float print": sum(recs[r["better_site_id"]].float_print for r in row5),
        "row 5 picked and better from the same source": sum(r["picked_source_id"] == r["better_source_id"] for r in row5),
        "row 5 by source pair": dict(collections.Counter(
            f"{r['picked_source_id']} -> {r['better_source_id']}" for r in row5).most_common(10)),
        "conflicts by source pair": dict(collections.Counter(
            f"{r['picked_source_id']} -> {r['better_source_id']}" for r in conflicts).most_common(10)),
    }
    row5.sort(key=lambda r: r["km"])
    res["row 5 examples (distance deciles)"] = [row5[round(i * (len(row5) - 1) / 9)] for i in range(10)] if row5 else []
    out.mkdir(parents=True, exist_ok=True)
    (out / "amandeep_funnel.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    for name, lst in (("amandeep_row5.csv", row5), ("amandeep_conflicts.csv", conflicts)):
        with open(out / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(lst[0]))
            w.writeheader()
            w.writerows(lst)
    print(json.dumps({k: v for k, v in res.items() if "examples" not in k}, indent=2, default=str))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
