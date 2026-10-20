"""Problem 5 fix: compare the offline merge of main with the merge of the fix
branch on the data branch (with its commodity corrections list). Read-only.

    CFG_FILE=<fix>/tests/resources/config.yml PYTHONPATH=<fix> \\
      .venv-p2/bin/python p5_fix_measure.py run-main0 run-fix0 <list.csv> out

Both runs use PYTHONHASHSEED=0: main orders a record's view rows by iterating
a set of commodity ids (models/kgrel/mineral_site.py:140), so without a fixed
seed two runs of main differ in that order.

Checks, per record (679,778):
  - every field of the stored site except `inventories` is unchanged;
  - `inventories` equal main's with the list applied, nothing else;
  - the merged partials (name, coordinates, country, state, ranks) are unchanged.
Per merged site with a changed member, rebuilt with main's own
DedupMineralSite.from_dedup_sites in both runs: every commodity removed must be
the old QID of a corrected candidate, every one added a remap target, and no
other commodity's grade/tonnage may change ("unintended" must be 0).

Writes out/p5_fix_measure.json and out/p5_fix_rows.csv (hits per list row).
"""

from __future__ import annotations

import collections
import copy
import csv
import json
import sys
from pathlib import Path

import serde.json
from minmodkg.misc.commodity_corrections import CommodityCorrections
from minmodkg.models.kgrel.dedup_mineral_site import DedupMineralSite
from minmodkg.models.kgrel.mineral_site import MineralSiteAndInventory

MR = "https://minmod.isi.edu/resource/"
OREGON = "http://www.oregongeology.org"
NC = "https://www.deq.nc.gov/about/divisions/energy-mineral-and-land-resources/nc-geological-survey"
MRDS = "https://mrdata.usgs.gov/mrds"

# the investigation's 7 defects, as (source, observed, wrong QID)
DEFECTS = {
    "Construction->Strontium": (MRDS, "Construction", "Q609"),
    "SC->Scandium (Oregon)": (OREGON, "SC", "Q607"),
    "S->Sulfur (Oregon)": (OREGON, "S", "Q633"),
    "Construc->Cobalt": (NC, "Construc", "Q537"),
    "CS->Cesium (Oregon)": (OREGON, "CS", "Q591"),
    "SD->Sand (Oregon)": (OREGON, "SD", "Q655"),
    "Metal->Nonmetal (mrds)": (MRDS, "Metal", "Q581"),
    "Metal->Nonmetal (nc)": (NC, "Metal", "Q581"),
}
# the H5 pairs left out of the list (mineral names), all from nc
LEFT_OUT = {
    "Galena": "Q594", "Chalcopyrite": "Q525", "Hematite": "Q593", "Apatite": "Q553",
    "Monazite": "Q570", "Sillimanite": "Q657", "Tourmaline": "Q632", "Vesuvianite": "Q564",
}


def qid(c: dict):
    u = c.get("normalized_uri")
    return u[len(MR):] if u else None


def gt_key(inv: dict):
    g = (inv.get("grade") or {}).get("value")
    o = (inv.get("ore") or {}).get("value")
    return None if g is None and o is None else (g, o)


def view_gt(v):
    return (v.tonnage, v.grade, v.contained_metal)


def files_of(run: Path):
    return sorted(p.relative_to(run / "data/mineral-sites/merged") for p in (run / "data/mineral-sites/merged").glob("*/*"))


def main(run_a: Path, run_b: Path, list_csv: Path, out: Path):
    corr = CommodityCorrections.from_file(list_csv)
    rows = corr.rows
    row_key = lambda r: (r.source_id, r.observed_name, r.context)
    hits = {row_key(r): collections.Counter() for r in rows}
    hit_dedups = {row_key(r): set() for r in rows}

    fa, fb = files_of(run_a), files_of(run_b)
    assert fa == fb
    bad = collections.Counter()  # unintended differences, must stay 0
    n_records = 0
    changed_sites: dict[str, list] = {}  # site_id -> applied (row, old inventory)
    targets: set[str] = set()
    defect_rec = {d: [0, 0] for d in DEFECTS}  # records before / after
    defect_dedup = {d: [set(), set()] for d in DEFECTS}
    left_rec = collections.Counter()
    qid_rec = collections.defaultdict(lambda: [0, 0])  # records carrying a QID
    qid_dedup = collections.defaultdict(lambda: [set(), set()])  # merged sites listing it
    drop_gt = collections.Counter()
    drop_gt_examples = []

    watch = {q for _, _, q in DEFECTS.values()} | {r.normalized_uri[len(MR):] for r in rows if r.normalized_uri}
    watch |= {"Q523", "Q659", "Q559", "Q619", "Q569", "Q10004", "Q636"}  # wrong QIDs of the other rows

    for p in fa:
        da = serde.json.deser(run_a / "data/mineral-sites/merged" / p)
        db = serde.json.deser(run_b / "data/mineral-sites/merged" / p)
        if da["DedupMineralSite"] != db["DedupMineralSite"]:
            bad["merged partial changed"] += 1
        assert len(da["MineralSiteAndInventory"]) == len(db["MineralSiteAndInventory"])
        for x, y in zip(da["MineralSiteAndInventory"], db["MineralSiteAndInventory"]):
            n_records += 1
            msa, msb = x["ms"], y["ms"]
            assert msa["site_id"] == msb["site_id"]
            if {k: v for k, v in msa.items() if k != "inventories"} != {k: v for k, v in msb.items() if k != "inventories"}:
                bad["site field other than inventories changed"] += 1
            # main's inventories with the list applied must be the fix's
            pseudo = {"source_id": msa["source_id"], "mineral_inventory": copy.deepcopy(msa.get("inventories", []))}
            applied = corr.apply(pseudo)
            if pseudo["mineral_inventory"] != msb.get("inventories", []):
                bad["inventories differ from main + list"] += 1
            if applied:
                changed_sites[msa["site_id"]] = applied
                targets.add(msa["dedup_site_id"])
                for r, inv in applied:
                    k = row_key(r)
                    hits[k]["inventories"] += 1
                    hit_dedups[k].add(msa["dedup_site_id"])
                    if r.action == "drop" and gt_key(inv) is not None:
                        others = [gt_key(j) for j in msa["inventories"] if j is not inv and j["commodity"] != inv["commodity"]]
                        dup = gt_key(inv) in others
                        drop_gt["with grade/tonnage"] += 1
                        drop_gt["duplicated on the same record" if dup else "NOT duplicated"] += 1
                        if len(drop_gt_examples) < 5:
                            drop_gt_examples.append({"site_id": msa["site_id"], "observed": inv["commodity"]["observed_name"], "grade_ore": gt_key(inv), "duplicated": dup})
                for k in {row_key(r) for r, _ in applied}:
                    hits[k]["records"] += 1
            elif x.get("invs", []) != y.get("invs", []):
                bad["views changed without a correction"] += 1

            for i, ms in enumerate((msa, msb)):
                invs = ms.get("inventories", [])
                for d, (src, obs, q) in DEFECTS.items():
                    if ms["source_id"] == src and any(v["commodity"].get("observed_name") == obs and qid(v["commodity"]) == q for v in invs):
                        defect_rec[d][i] += 1
                        defect_dedup[d][i].add(ms["dedup_site_id"])
                if i == 1 and ms["source_id"] == NC:
                    for v in invs:
                        if LEFT_OUT.get(v["commodity"].get("observed_name")) == qid(v["commodity"]):
                            left_rec[v["commodity"]["observed_name"]] += 1
                qs = {qid(v["commodity"]) for v in invs} & watch
                for q in qs:
                    qid_rec[q][i] += 1
            for i, z in enumerate((x, y)):
                for v in z.get("invs", []):
                    if v["commodity"] in watch:
                        qid_dedup[v["commodity"]][i].add(z["ms"]["dedup_site_id"])

    # merged sites with a changed member, rebuilt in both runs
    def load(run: Path):
        partials, wanted, msis = collections.defaultdict(list), set(), {}
        for p in fa:
            for x in serde.json.deser(run / "data/mineral-sites/merged" / p)["DedupMineralSite"]:
                if x["id"] in targets:
                    partials[x["id"]].append(x)
                    wanted.update(r["site_id"] for r in x["ranked_sites"])
        for p in fa:
            for x in serde.json.deser(run / "data/mineral-sites/merged" / p)["MineralSiteAndInventory"]:
                if x["ms"]["site_id"] in wanted:
                    msis[x["ms"]["site_id"]] = MineralSiteAndInventory.from_dict(x)
        return partials, msis

    pa, ma = load(run_a)
    pb, mb = load(run_b)
    merged = collections.Counter()
    unintended = []
    for e in sorted(targets):
        sa = [DedupMineralSite.from_dict(x) for x in pa[e]]
        sb = [DedupMineralSite.from_dict(x) for x in pb[e]]
        order = [r.site_id for d in sa for r in d.ranked_sites]
        now = DedupMineralSite.from_dedup_sites(sa, [ma[s] for s in order], is_site_ranked=True)
        aft = DedupMineralSite.from_dedup_sites(sb, [mb[s] for s in order], is_site_ranked=True)
        if now.dms.to_dict() != aft.dms.to_dict():
            unintended.append({"dedup_id": e, "why": "merged site fields changed"})
        cn = {v.commodity: v for v in now.invs}
        ca = {v.commodity: v for v in aft.invs}
        applied = [ra for s in order for ra in changed_sites.get(s, [])]
        old = {qid(inv["commodity"]) for _, inv in applied}
        new = {r.normalized_uri[len(MR):] for r, _ in applied if r.action == "remap"}
        removed, added = set(cn) - set(ca), set(ca) - set(cn)
        gt_changed = {q for q in set(cn) & set(ca) if view_gt(cn[q]) != view_gt(ca[q])}
        why = []
        if removed - old:
            why.append(f"removed {sorted(removed - old)}")
        if added - new:
            why.append(f"added {sorted(added - new)}")
        if gt_changed - old - new:
            why.append(f"grade/tonnage changed {sorted(gt_changed - old - new)}")
        if why:
            unintended.append({"dedup_id": e, "why": "; ".join(why)})
        merged["merged sites with a corrected member"] += 1
        merged["commodity list changed"] += bool(removed or added)
        merged["left with no commodity"] += len(ca) == 0
        merged["wrong QID kept because another candidate has it"] += len((old - new) & set(ca))
        for q in removed:
            merged[f"removed {q}"] += 1
        for q in added:
            merged[f"added {q}"] += 1
        for q in old & set(cn):
            if view_gt(cn[q]) != (None, None, None) and q not in ca:
                merged[f"grade/tonnage row removed with {q}"] += 1
        for q in new & set(ca):
            if view_gt(ca[q]) != (None, None, None):
                merged[f"grade/tonnage row now under {q}"] += 1

    result = {
        "records": n_records,
        "unintended_record_level": dict(bad),
        "unintended_merged_sites": unintended,
        "dropped_inventories_with_grade_tonnage": dict(drop_gt),
        "dropped_gt_examples": drop_gt_examples,
        "defects_records_before_after": {d: v for d, v in defect_rec.items()},
        "defects_merged_sites_before_after": {d: [len(v[0]), len(v[1])] for d, v in defect_dedup.items()},
        "left_out_records_after": dict(left_rec),
        "records_carrying_qid_before_after": {q: v for q, v in sorted(qid_rec.items())},
        "merged_sites_listing_qid_before_after": {q: [len(v[0]), len(v[1])] for q, v in sorted(qid_dedup.items())},
        "merged": dict(merged),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "p5_fix_measure.json").write_text(json.dumps(result, indent=1, default=str))
    with open(out / "p5_fix_rows.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["source_id", "observed_name", "context", "action", "normalized_uri", "inventories", "records", "merged_sites"])
        for r in rows:
            k = row_key(r)
            w.writerow([r.source_id, r.observed_name, r.context, r.action, r.normalized_uri or "", hits[k]["inventories"], hits[k]["records"], len(hit_dedups[k])])
    print(json.dumps({k: v for k, v in result.items() if k != "unintended_merged_sites"}, indent=1, default=str))
    print("unintended merged sites:", len(unintended), unintended[:5])


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
