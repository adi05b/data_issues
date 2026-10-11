"""Problem 3, precision tie-break: what changes between merge runs. Read-only.

  rebuild <run> <main run> <out.json>
      Rebuild, with the code on PYTHONPATH, every merged site of <run> where a
      change is possible: >= 2 members with a coordinate, or a (0, 0) member, in
      <main run>. Same as prep_kgrel_input: from_dedup_sites over the partials.
      Run it once per run with that run's own code (main for run-main).

  compare <main.json> <run.json> <main run> <run> <label> <out dir>
      Compare two rebuilds; record-level diffs (inventories as sets); the
      invariants; and, for the tie-break-only run, the set against
      out/amandeep_row5.csv. Needs fix/p3-null-island on PYTHONPATH.

    CFG_FILE=<code>/tests/resources/config.yml PYTHONPATH=<code>:. \\
      .venv-p2/bin/python p3_tiebreak_measure.py ...
"""

from __future__ import annotations

import collections
import csv
import inspect
import json
import math
import statistics
import sys
from pathlib import Path

import serde.json

from p3_null_island_measure import files, norm


def targets(main_run: Path) -> set[str]:
    coord, zero = collections.Counter(), set()
    for p in files(main_run).values():
        for m in serde.json.deser(p)["MineralSiteAndInventory"]:
            lv = m["ms"].get("location_view") or {}
            if lv.get("lat") is not None and lv.get("lon") is not None:
                coord[m["ms"]["dedup_site_id"]] += 1
                if lv["lat"] == 0 and lv["lon"] == 0:
                    zero.add(m["ms"]["dedup_site_id"])
    return {e for e, n in coord.items() if n >= 2} | zero


def rebuild(run: Path, main_run: Path, out: Path):
    from minmodkg.models.kgrel.dedup_mineral_site import DedupMineralSite
    from minmodkg.models.kgrel.mineral_site import MineralSiteAndInventory
    from minmodkg.services.kgrel_entity import FileEntityService

    ids = targets(main_run)
    partials, wanted = collections.defaultdict(list), set()
    for p in files(run).values():
        for x in serde.json.deser(p)["DedupMineralSite"]:
            if x["id"] in ids:
                partials[x["id"]].append(x)
                wanted.update(r["site_id"] for r in x["ranked_sites"])
    msis = {}
    for p in files(run).values():
        for x in serde.json.deser(p)["MineralSiteAndInventory"]:
            if x["ms"]["site_id"] in wanted:
                msis[x["ms"]["site_id"]] = MineralSiteAndInventory.from_dict(x)
    kw = {}
    if "crs_names" in inspect.signature(DedupMineralSite.from_dedup_sites).parameters:
        kw["crs_names"] = FileEntityService(run / "data/entities").get_crs_name()
    res = {}
    for e in ids:
        lst = [DedupMineralSite.from_dict(x) for x in partials[e]]
        res[e] = DedupMineralSite.from_dedup_sites(
            lst, [msis[r.site_id] for d in lst for r in d.ranked_sites], is_site_ranked=True, **kw
        ).dms.to_dict()
    out.write_text(json.dumps(res))
    print(f"{run.name}: rebuilt {len(res)} merged sites ({'with' if kw else 'without'} crs_names)", file=sys.stderr)


def haversine_km(a, b):
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b["lon"] - a["lon"]) / 2) ** 2
    return 2 * 6371.0088 * math.asin(min(1.0, math.sqrt(h)))


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, math.ceil(q * len(xs)) - 1)] if xs else None


def compare(main_json: Path, run_json: Path, main_run: Path, run: Path, label: str, out: Path):
    from minmodkg.misc.coord_precision import SourceCoordinate
    from minmodkg.models.kgrel.custom_types import Location
    from minmodkg.services.kgrel_entity import FileEntityService

    A, B = json.loads(main_json.read_text()), json.loads(run_json.read_text())
    assert A.keys() == B.keys()
    crs_names = FileEntityService(run / "data/entities").get_crs_name()

    # record level: every record in both runs
    raw, views_a, views_b, rec_diff = {}, {}, {}, collections.Counter()
    fa, fb = files(main_run), files(run)
    for k in fa:
        ma = {m["ms"]["site_id"]: m for m in serde.json.deser(fa[k])["MineralSiteAndInventory"]}
        mb = {m["ms"]["site_id"]: m for m in serde.json.deser(fb[k])["MineralSiteAndInventory"]}
        for s in ma:
            raw[s] = ma[s]["ms"].get("location") or {}
            views_a[s], views_b[s] = ma[s]["ms"].get("location_view") or {}, mb[s]["ms"].get("location_view") or {}
            x, y = norm(ma[s]), norm(mb[s])
            if x != y:
                rec_diff[str(sorted(f for f in set(x["ms"]) | set(y["ms"]) if x["ms"].get(f) != y["ms"].get(f))
                             + (["invs"] if x["invs"] != y["invs"] else []))] += 1

    def coord(site_id, views):
        loc = Location.from_dict(raw[site_id])
        v = views[site_id]
        return SourceCoordinate(site_id, loc.coordinates, loc.crs_name(crs_names), v["lat"], v["lon"])

    def score_of(d, site_id):
        return next(r["score"] for r in d["ranked_sites"] if r["site_id"] == site_id)

    changes, fields, inv = [], collections.Counter(), collections.Counter()
    for e in sorted(A):
        diff = sorted(f for f in set(A[e]) | set(B[e]) if A[e].get(f) != B[e].get(f))
        if not diff:
            continue
        fields[str(diff)] += 1
        if diff != ["coordinates"]:
            inv["a field other than coordinates changed"] += 1
        old, new = A[e].get("coordinates"), B[e].get("coordinates")
        null_island = old is not None and old["value"] == {"lat": 0.0, "lon": 0.0}
        row = {"dedup_site_id": e, "name": (B[e].get("name") or {}).get("value"),
               "driver": "null island" if null_island else "tie-break",
               "old_site_id": old and old["refid"], "new_site_id": new and new["refid"],
               "old_wkt": old and raw[old["refid"]].get("coordinates"),
               "new_wkt": new and raw[new["refid"]].get("coordinates"),
               "old_source": old and old["refid"].split("__")[1], "new_source": new and new["refid"].split("__")[1],
               "km": haversine_km(old["value"], new["value"]) if old and new else None,
               "old_score": None, "new_score": None}
        changes.append(row)
        if old is None or new is None:
            continue
        so, sn = score_of(A[e], old["refid"]), score_of(B[e], new["refid"])
        row["old_score"], row["new_score"] = so["score"], sn["score"]
        if null_island:  # the rule there is "skip the missing value", whatever the score
            continue
        if so["suborder"][0]:
            inv["the top record is an expert/curator"] += 1
        if sn["score"] < so["score"]:
            inv["new point has a lower score than the old one"] += 1
        if sn["score"] != so["score"]:
            inv["tie-break change between different scores"] += 1
        o, n = coord(old["refid"], views_a), coord(new["refid"], views_b)
        if not o.contains(n):
            inv["new point outside the old point's box"] += 1
        if not (n.resolution_km() < o.resolution_km()):
            inv["new point not strictly more precise"] += 1

    tb = [c for c in changes if c["driver"] == "tie-break"]
    kms = [c["km"] for c in tb]
    res = {
        "label": label,
        "merged sites rebuilt": len(A),
        "records changed (fields)": dict(rec_diff),
        "merged sites changed": len(changes),
        "by driver": dict(collections.Counter(c["driver"] for c in changes)),
        "fields changed": dict(fields),
        "null island: now no coordinate": sum(c["driver"] == "null island" and c["new_site_id"] is None for c in changes),
        "null island: another member's point": sum(c["driver"] == "null island" and c["new_site_id"] is not None for c in changes),
        "tie-break moves": {"n": len(kms), "median_km": statistics.median(kms) if kms else None,
                            "p95_km": pct(kms, 0.95), "max_km": max(kms, default=None),
                            "gt_100m": sum(k > 0.1 for k in kms), "gt_1km": sum(k > 1 for k in kms)},
        "tie-break by source pair": dict(collections.Counter(
            f"{c['old_source']} -> {c['new_source']}" for c in tb).most_common()),
        "invariant violations (tie-break changes)": dict(inv),
        "null island fallbacks to a lower score (by design)": [
            {k: c[k] for k in ("name", "old_source", "old_score", "new_source", "new_score")}
            for c in changes
            if c["driver"] == "null island" and c.get("new_score") is not None and c["new_score"] < c["old_score"]],
    }
    row5 = {r["dedup_site_id"]: r for r in csv.DictReader(open(Path(__file__).parent / "out/amandeep_row5.csv"))}
    got = {c["dedup_site_id"]: c for c in tb}
    res["vs amandeep_row5.csv"] = {
        "row5": len(row5), "tie-break changes": len(got),
        "in both": len(row5.keys() & got.keys()),
        "only in row5": len(row5.keys() - got.keys()), "only here": len(got.keys() - row5.keys()),
        "same new record": sum(got[e]["new_site_id"] == row5[e]["better_site_id"] for e in row5.keys() & got.keys()),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / f"tiebreak_{label}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    with open(out / f"tiebreak_{label}_changes.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(changes[0]))
        w.writeheader()
        w.writerows(changes)
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "rebuild":
        rebuild(Path(args[0]), Path(args[1]), Path(args[2]))
    else:
        compare(*map(Path, args[:4]), args[4], Path(args[5]))
