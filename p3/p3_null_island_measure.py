"""Problem 3, Null Island fix: what changes between two merge runs. Read-only.

Compares every record and every partial merged site in two runs of
p2c/rerun/scripts/p2d_run_merge.py on the same data (run-main: main;
run-null-island: fix/p3-null-island), then rebuilds each merged site whose
inputs differ with DedupMineralSite.from_dedup_sites, as prep_kgrel_input does.
Any merged site whose inputs are identical in both runs is identical after the
rebuild too, so the comparison covers all of them.

    CFG_FILE=<branch>/tests/resources/config.yml PYTHONPATH=<branch> \\
      .venv-p2/bin/python p3_null_island_measure.py run-main run-null-island out
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import serde.json
import shapely.wkt
from shapely.geometry import MultiPoint, Point

from minmodkg.models.kgrel.dedup_mineral_site import DedupMineralSite
from minmodkg.models.kgrel.mineral_site import MineralSiteAndInventory


def files(run: Path) -> dict[str, Path]:
    base = run / "data/mineral-sites/merged"
    return {str(p.relative_to(base)): p for p in sorted(base.glob("*/*"))}


def null_island_case(wkt: str | None) -> str | None:
    """How the fix sees this WKT: None if it has no (0, 0) point."""
    if not wkt or "nan" in wkt.lower():
        return None
    try:
        g = shapely.wkt.loads(wkt)
    except Exception:
        return None
    zero = lambda p: p.x == 0 and p.y == 0  # noqa: E731
    if isinstance(g, Point) and not g.is_empty and zero(g):
        return "POINT at (0, 0)"
    if isinstance(g, MultiPoint) and any(zero(p) for p in g.geoms):
        return "MULTIPOINT, all at (0, 0)" if all(zero(p) for p in g.geoms) else "MULTIPOINT, some at (0, 0)"
    return None


def norm(m: dict) -> dict:
    """A record with its inventories as a set: their order is per-process hash
    noise (see p2c/rerun/scripts/p2d_merged.py)."""
    return {**m, "invs": sorted(json.dumps(i, sort_keys=True) for i in m.get("invs", []))}


def rebuild(run: Path, ids: set[str]) -> dict[str, dict]:
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
    out = {}
    for e in ids:
        lst = [DedupMineralSite.from_dict(x) for x in partials[e]]
        out[e] = DedupMineralSite.from_dedup_sites(
            lst, [msis[r.site_id] for d in lst for r in d.ranked_sites], is_site_ranked=True
        ).dms.to_dict()
    return out


def main(run_a: Path, run_b: Path, out: Path):
    fa, fb = files(run_a), files(run_b)
    assert fa.keys() == fb.keys()
    rec_fields, rec_cases, partial_fields = collections.Counter(), collections.Counter(), collections.Counter()
    zero_records, unexpected, ids, wkt_of = [], [], set(), {}
    for k in fa:
        a, b = serde.json.deser(fa[k]), serde.json.deser(fb[k])
        ma = {m["ms"]["site_id"]: m for m in a["MineralSiteAndInventory"]}
        mb = {m["ms"]["site_id"]: m for m in b["MineralSiteAndInventory"]}
        assert ma.keys() == mb.keys(), k
        for s in ma:
            x, y = norm(ma[s]), norm(mb[s])
            wkt = (x["ms"].get("location") or {}).get("coordinates")
            wkt_of[s] = wkt
            case = null_island_case(wkt)
            if case:
                zero_records.append({"site_id": s, "source_id": x["ms"]["source_id"], "wkt": wkt, "case": case})
            if x == y:
                if case:
                    unexpected.append({"site_id": s, "why": "has a (0, 0) point but its view did not change"})
                continue
            diff = {f for f in set(x["ms"]) | set(y["ms"]) if x["ms"].get(f) != y["ms"].get(f)}
            diff |= {"invs"} if x["invs"] != y["invs"] else set()
            lva, lvb = x["ms"].get("location_view") or {}, y["ms"].get("location_view") or {}
            view_diff = {f for f in set(lva) | set(lvb) if lva.get(f) != lvb.get(f)}
            rec_fields[f"{sorted(diff)} / view {sorted(view_diff)}"] += 1
            ids.add(x["ms"]["dedup_site_id"])
            if not case or diff != {"location_view"} or not view_diff <= {"lat", "lon"}:
                unexpected.append({"site_id": s, "why": f"changed outside the rule: {sorted(diff)} {sorted(view_diff)}"})
            rec_cases[f"{case}: {'lat/lon removed' if 'lat' not in lvb else 'lat/lon moved'}"] += 1
        da = {d["id"]: d for d in a["DedupMineralSite"]}
        db = {d["id"]: d for d in b["DedupMineralSite"]}
        assert da.keys() == db.keys(), k
        for e in da:
            if da[e] != db[e]:
                ids.add(e)
                for f in set(da[e]) | set(db[e]):
                    if da[e].get(f) != db[e].get(f):
                        partial_fields[f] += 1

    A, B = rebuild(run_a, ids), rebuild(run_b, ids)
    merged_fields, changed = collections.Counter(), []
    for e in sorted(ids):
        diff = sorted(f for f in set(A[e]) | set(B[e]) if A[e].get(f) != B[e].get(f))
        if not diff:
            continue
        merged_fields[str(diff)] += 1
        if diff != ["coordinates"]:
            unexpected.append({"dedup_site_id": e, "why": f"merged site changed outside coordinates: {diff}"})
        old, new = A[e].get("coordinates"), B[e].get("coordinates")
        changed.append({
            "dedup_site_id": e,
            "name": (B[e].get("name") or {}).get("value"),
            "country": B[e]["country"]["value"], "state_or_province": B[e]["state_or_province"]["value"],
            "old_record": old["refid"] if old else None, "old_wkt": wkt_of.get(old["refid"]) if old else None,
            "old_point": old["value"] if old else None,
            "new_record": new["refid"] if new else None, "new_wkt": wkt_of.get(new["refid"]) if new else None,
            "new_point": new["value"] if new else None,
        })
    res = {
        "records with a (0, 0) point": len(zero_records),
        "(0, 0) records by case": dict(collections.Counter(r["case"] for r in zero_records)),
        "(0, 0) records by source": dict(collections.Counter(r["source_id"] for r in zero_records)),
        "records whose view changed": sum(rec_fields.values()),
        "changed records: fields [record] / view [location_view]": dict(rec_fields),
        "changed records by case": dict(rec_cases),
        "partial merged sites changed, by field": dict(partial_fields),
        "merged sites with different inputs (rebuilt)": len(ids),
        "merged sites that changed": len(changed),
        "changed merged sites: fields": dict(merged_fields),
        "... now no coordinate": sum(c["new_point"] is None for c in changed),
        "... now another member's coordinate": sum(c["new_point"] is not None for c in changed),
        "unexpected": unexpected,
        "fallbacks": [c for c in changed if c["new_point"] is not None],
        "changed": changed,
        "zero_records": zero_records,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "null_island_fix.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    print(json.dumps({k: v for k, v in res.items() if k not in ("changed", "zero_records")}, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
