"""Problem 5: the six commodity defects at merged-site grain, with main's code.

Reads the merged files of an offline merge (p2c/rerun/scripts/p2d_run_merge.py,
main @ 45a2a16 on ta2-minmod-data @ 0c8b827) and, for every merged site with a
defect member, rebuilds it with main's own MineralSiteAndInventory.from_raw_site
and DedupMineralSite.from_dedup_sites, as prep_kgrel_input does:

  now   as main builds it today
  drop  the defect candidates' normalized_uri set to None (the candidate and
        its inventory stay; main skips it at mineral_site.py:72)
  floor every matched candidate below 0.62 treated the same way

Also, over all 679,778 records: per wrong commodity, how many records,
inventories and merged sites carry it today, and how many only through a
defect candidate (what the dashboard and the commodity facet would lose).

Nothing touches a graph, Postgres or the API.

    CFG_FILE=<main>/tests/resources/config.yml PYTHONPATH=<main> \\
      .venv-p2/bin/python p5_merged.py run-main out
"""

from __future__ import annotations

import collections
import copy
import json
import sys
from pathlib import Path

import serde.json
from minmodkg.models.kg.mineral_site import MineralSite as KGMineralSite
from minmodkg.models.kgrel.dedup_mineral_site import DedupMineralSite
from minmodkg.models.kgrel.mineral_site import MineralSiteAndInventory
from minmodkg.services.kgrel_entity import FileEntityService

from p5_scan import DEFECTS, defect_of

SAND_AND_GRAVEL = "Q656"


def inv_defect(src: str, inv: dict):
    c = inv["commodity"]
    return defect_of(src, c.get("observed_name"), c.get("normalized_uri"))


def has_gt(v) -> bool:
    return v.contained_metal is not None or v.tonnage is not None or v.grade is not None


def selfcheck(ent: FileEntityService):
    """What main does with an inventory whose commodity is dropped, three ways."""
    raw = {
        "source_id": "https://mrdata.usgs.gov/mrds",
        "record_id": "r1",
        "created_by": "https://minmod.isi.edu/users/s/umn",
        "modified_at": "2025-01-01T00:00:00Z",
        "mineral_inventory": [
            {
                "reference": {"document": {"uri": "https://mrdata.usgs.gov/mrds"}},
                "commodity": {"source": "m", "confidence": 0.5, "observed_name": "Construction",
                              "normalized_uri": "https://minmod.isi.edu/resource/Q609"},
            }
        ],
    }
    args = dict(
        commodity_form_conversion=ent.get_commodity_form_conversion(),
        crs_names=ent.get_crs_name(),
        source_score=ent.get_data_source_score(),
    )
    msi = MineralSiteAndInventory.from_raw_site(copy.deepcopy(raw), **args)
    assert [v.commodity for v in msi.invs] == ["Q609"]

    # (1) normalized_uri -> None: inventory kept in ms.inventories and the KG
    # export, no MineralInventoryView row
    r1 = copy.deepcopy(raw)
    del r1["mineral_inventory"][0]["commodity"]["normalized_uri"]
    m1 = MineralSiteAndInventory.from_raw_site(r1, **args)
    assert m1.invs == [] and len(m1.ms.inventories) == 1
    assert len(m1.ms.to_kg().mineral_inventory) == 1

    # (2) inventory removed: gone everywhere, the site itself is still built
    r2 = copy.deepcopy(raw)
    r2["mineral_inventory"] = []
    m2 = MineralSiteAndInventory.from_raw_site(r2, **args)
    assert m2.invs == [] and m2.ms.inventories == []

    # (3) commodity key removed: commodity is required, the merge raises
    r3 = copy.deepcopy(raw)
    del r3["mineral_inventory"][0]["commodity"]
    try:
        MineralSiteAndInventory.from_raw_site(r3, **args)
        raise AssertionError("expected a KeyError")
    except KeyError:
        pass

    # a merged site whose only member loses its only commodity is still built
    d = DedupMineralSite.from_sites([m1])
    assert d.invs == []
    return {"(1) uri None": "inventory kept, no view row, still in KG export",
            "(2) inventory removed": "gone from site, views and KG export; site kept",
            "(3) commodity key removed": "KeyError in MineralInventory.from_dict: merge fails",
            "merged site with no commodity": "built, with zero DedupMineralInventoryView rows"}


FLOOR = 0.62


def is_defect(src, inv):
    return inv_defect(src, inv) is not None


def below_floor(src, inv):
    c = inv["commodity"]
    return c.get("normalized_uri") is not None and c["confidence"] < FLOOR


def drop(msi: MineralSiteAndInventory, ent_args, pred=is_defect) -> MineralSiteAndInventory:
    kgms = msi.ms.to_kg()
    raw = kgms.to_dict()
    for inv in raw.get("mineral_inventory", []):
        if pred(raw["source_id"], inv):
            inv["commodity"].pop("normalized_uri", None)
    new = MineralSiteAndInventory.from_raw_site(raw, **ent_args)
    new.ms.dedup_site_id = msi.ms.dedup_site_id
    new.ms.modified_at = msi.ms.modified_at
    return new


def main(run: Path, out: Path):
    ent = FileEntityService(run / "data/entities")
    ent_args = dict(
        commodity_form_conversion=ent.get_commodity_form_conversion(),
        crs_names=ent.get_crs_name(),
        source_score=ent.get_data_source_score(),
    )
    behaviour = selfcheck(ent)
    files = sorted((run / "data/mineral-sites/merged").glob("*/*"))

    # pass 1: affected records and their merged sites
    site_defects: dict[str, set[str]] = {}
    targets: set[str] = set()
    floor_sites: set[str] = set()
    wrong = {DEFECTS[d]["uri"] for d in DEFECTS}
    den = {q: collections.Counter() for q in wrong}
    den_dedup = {q: set() for q in wrong}
    den_dedup_only = {q: collections.defaultdict(lambda: [0, 0]) for q in wrong}
    n_members = collections.Counter()
    n_records = 0
    for f in files:
        for x in serde.json.deser(f)["MineralSiteAndInventory"]:
            ms = x["ms"]
            n_records += 1
            n_members[ms["dedup_site_id"]] += 1
            invs = ms.get("inventories", [])
            ds = {d for inv in invs if (d := inv_defect(ms["source_id"], inv))}
            if ds:
                site_defects[ms["site_id"]] = ds
                targets.add(ms["dedup_site_id"])
            if any(below_floor(ms["source_id"], inv) for inv in invs):
                floor_sites.add(ms["site_id"])
                targets.add(ms["dedup_site_id"])
            for q in wrong:
                via = [inv for inv in invs if (inv["commodity"].get("normalized_uri") or "").endswith("/" + q)]
                if not via:
                    continue
                only = all(is_defect(ms["source_id"], inv) for inv in via)
                den[q]["records"] += 1
                den[q]["inventories"] += len(via)
                den[q]["records_only_via_defect"] += only
                den[q]["inventories_via_defect"] += sum(is_defect(ms["source_id"], inv) for inv in via)
                den_dedup[q].add(ms["dedup_site_id"])
                t = den_dedup_only[q][ms["dedup_site_id"]]
                t[0] += 1
                t[1] += only

    # pass 2: partials and members of those merged sites
    partials, wanted = collections.defaultdict(list), set()
    for f in files:
        for x in serde.json.deser(f)["DedupMineralSite"]:
            if x["id"] in targets:
                partials[x["id"]].append(x)
                wanted.update(r["site_id"] for r in x["ranked_sites"])
    msis = {}
    for f in files:
        for x in serde.json.deser(f)["MineralSiteAndInventory"]:
            if x["ms"]["site_id"] in wanted:
                msis[x["ms"]["site_id"]] = MineralSiteAndInventory.from_dict(x)

    # record grain, main's MineralInventoryView: wrong commodity with grade/tonnage
    rec = {d: collections.Counter() for d in DEFECTS}
    for sid, ds in site_defects.items():
        msi = msis[sid]
        for d in ds:
            w = DEFECTS[d]["uri"]
            v = next((v for v in msi.invs if v.commodity == w), None)
            rec[d]["records"] += 1
            rec[d]["view_row_for_wrong_commodity"] += v is not None
            rec[d]["view_row_with_gt"] += v is not None and has_gt(v)

    for q in wrong:
        den[q]["merged_sites"] = len(den_dedup[q])
        den[q]["merged_sites_only_via_defect"] = sum(1 for a, b in den_dedup_only[q].values() if a == b)

    labels = {c.id: c.name for c in ent.get_commodities()}
    fl = collections.Counter()
    fl_removed = collections.Counter()
    fl_empty = collections.Counter()
    fl_gt = []
    m = {d: collections.Counter() for d in DEFECTS}
    any_def = collections.Counter()
    examples = collections.defaultdict(list)
    for e in sorted(targets):
        dms_lst = [DedupMineralSite.from_dict(x) for x in partials[e]]
        order = [r.site_id for d in dms_lst for r in d.ranked_sites]
        now = DedupMineralSite.from_dedup_sites(dms_lst, [msis[s] for s in order], is_site_ranked=True)
        dropped = {s: drop(msis[s], ent_args) if s in site_defects else msis[s] for s in order}
        after = DedupMineralSite.from_dedup_sites(
            [DedupMineralSite.from_dict(x) for x in partials[e]],
            [dropped[s] for s in order], is_site_ranked=True)
        now_c = {v.commodity: v for v in now.invs}
        after_c = {v.commodity: v for v in after.invs}
        if any(s in floor_sites for s in order):
            fd = {s: drop(msis[s], ent_args, below_floor) if s in floor_sites else msis[s] for s in order}
            fafter = DedupMineralSite.from_dedup_sites(
                [DedupMineralSite.from_dict(x) for x in partials[e]],
                [fd[s] for s in order], is_site_ranked=True)
            fafter_c = {v.commodity for v in fafter.invs}
            removed = set(now_c) - fafter_c
            fl["merged_sites_touched"] += 1
            fl["merged_sites_losing_a_commodity"] += len(removed) > 0
            fl["merged_sites_no_commodity_after"] += len(fafter_c) == 0
            fl["merged_sites_losing_gt"] += any(has_gt(now_c[q]) for q in removed)
            if len(fafter_c) == 0:
                fl_empty[" + ".join(sorted(labels.get(q, q) for q in removed))] += 1
            for q in removed:
                if has_gt(now_c[q]):
                    fl_gt.append({"dedup_id": e, "commodity": labels.get(q, q), "site_id": now_c[q].site_id,
                                  "tonnage": now_c[q].tonnage, "grade": now_c[q].grade})
            for q in removed:
                fl_removed[labels.get(q, q)] += 1
        if not any(s in site_defects for s in order):
            continue
        ds_here = set().union(*(site_defects.get(s, set()) for s in order))
        any_def["merged_sites"] += 1
        any_def["merged_sites_multi_member"] += len(order) > 1
        any_def["merged_sites_with_no_commodity_after_drop"] += len(after_c) == 0
        any_def["merged_sites_with_no_commodity_now"] += len(now_c) == 0
        for d in ds_here:
            w = DEFECTS[d]["uri"]
            c = m[d]
            c["merged_sites"] += 1
            c["multi_member"] += len(order) > 1
            c["wrong_commodity_listed_now"] += w in now_c
            c["wrong_commodity_with_gt_now"] += w in now_c and has_gt(now_c[w])
            c["wrong_commodity_still_listed_after_drop"] += w in after_c
            c["sand_and_gravel_listed_now"] += SAND_AND_GRAVEL in now_c
            c["no_commodity_after_drop"] += len(after_c) == 0
            c["commodity_count_now"] += len(now_c)
            c["commodity_count_after"] += len(after_c)
            if w in after_c and len(examples[d]) < 5:
                examples[d].append({"dedup_id": e, "members": order, "kept_from": after_c[w].site_id})
            if w in now_c and has_gt(now_c[w]) and len(examples[d + " gt"]) < 5:
                v = now_c[w]
                examples[d + " gt"].append({"dedup_id": e, "site_id": v.site_id, "tonnage": v.tonnage,
                                             "grade": v.grade, "contained_metal": v.contained_metal})

    summary = {
        "records_in_merge": n_records,
        "merged_sites_in_merge": len(n_members),
        "drop_behaviour": behaviour,
        "any_defect": dict(any_def),
        "record_grain_views": {d: dict(c) for d, c in rec.items()},
        "wrong_commodity_totals": {f"{q} {labels.get(q, '')}": dict(c) for q, c in den.items()},
        "floor_062": {**dict(fl), "removed_from_merged_sites_by_label": dict(fl_removed.most_common()),
                     "left_with_no_commodity_by_removed": dict(fl_empty.most_common()), "losing_gt": fl_gt},
        "merged_grain": {d: dict(c) for d, c in m.items()},
        "examples": examples,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "p5_merged.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
