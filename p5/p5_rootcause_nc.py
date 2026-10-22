"""Problem 5 root cause, NC Geological Survey: compare the site JSON with the NC
DEQ "NC_MRDS" service (MapServer layer 2, Location point), read-only.

    python3 -I p5_rootcause_nc.py <nc_location_points.json> <ta2-minmod-data> <rdbms-tab-all dir> out [corrections.csv]

nc_location_points.json is every feature's attributes from
https://maps.deq.nc.gov/arcgis/rest/services/DEMLR/NC_MRDS/MapServer/2/query
(where=1=1, outFields=*, returnGeometry=false), fetched 2026-10-22.

ProcMine steps reproduced (umn-ta2-database-processing @ ce1ed70):
  _attribute.py:74, 80-89  title-case; several columns mapped to one label are
                           joined with "; "
  _procmine.py:158-164     deposit_type = deposit_type + " " + commodity
  _procmine.py:210-212     PGE / REE replaced, case-insensitively
  _procmine.py:215-218     commodity and deposit_type split on '|', ',' and ';'
"""

from __future__ import annotations

import collections
import csv
import json
import re
import sys
from pathlib import Path

# as p5_rootcause_mrds.py (python -I does not put this folder on sys.path)
PGE = "Platinum; Palladium; Rhodium; Ruthenium; Iridium; Osmium"
REE = ("Lanthanum; Praseodymium; Samarium; Gadolinium; Thulium; Holmium; Cerium; "
       "Europium; Ytterbium; Erbium; Yttrium; Neodymium; Terbium; Dysprosium; Lutetium")
SPLIT = re.compile(r"\s*[\|,;]\s*")


def procmine_pieces(value: str) -> list[str]:
    v = re.sub("pge", PGE, value, flags=re.I)
    v = re.sub("ree", REE, v, flags=re.I)
    return [p for p in SPLIT.split(v) if p != ""]


def main(points: Path, repo: Path, rdbms: Path, out: Path, corrections: Path | None = None):
    src = {r["NCGS_ID"]: r for r in json.load(open(points))}
    js = {}
    for f in sorted((repo / "data/mineral-sites/umn/nc_geological_survey").glob("*.json")):
        for s in json.load(open(f)):
            js[str(s["record_id"])] = s

    # every commodity name MRDS uses, to tell a cut-off name from a whole one
    csv.field_size_limit(10**9)
    name2code = {}
    with open(rdbms / "Commodity.txt", newline="", encoding="latin-1") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            name2code.setdefault(r["commod"].casefold(), r["code"])
    names = {r for r in name2code}

    cmp = collections.Counter()
    dt_cmp = collections.Counter()
    examples = []
    for rid, s in js.items():
        r = src.get(rid)
        if r is None:
            cmp["record not in today's service"] += 1
            continue
        joined = "; ".join(v for v in (r["MajorCommodity"], r["MinorCommodity"], r["TraceCommodity"]) if v)
        pred = {p.casefold() for p in procmine_pieces(joined)}
        have = {(i["commodity"].get("observed_name") or "").casefold() for i in s.get("mineral_inventory", [])}
        if r["DepositType"]:
            # _procmine.py:158-164, then the same split
            dt = {p.casefold() for p in SPLIT.split(r["DepositType"] + " " + joined) if p}
            have_dt = {(d.get("observed_name") or "").casefold() for d in s.get("deposit_type_candidate", [])}
            dt_cmp["equal" if dt == have_dt else "differ"] += 1
        if pred == have:
            cmp["equal"] += 1
        else:
            cmp["differ"] += 1
            if len(examples) < 8:
                examples.append({"NCGS_ID": rid, "source": joined, "json": sorted(have), "rebuilt": sorted(pred)})

    # cut-off names: a value of exactly 25 characters that is a strict prefix
    # of a longer MRDS commodity name
    cut = collections.Counter()
    cut_records = collections.defaultdict(set)
    for rid, r in src.items():
        for fld in ("MajorCommodity", "MinorCommodity", "TraceCommodity"):
            v = (r[fld] or "").casefold()
            for name in names:
                n = name
                if len(n) > 25 and n[:25] in v and n not in v:
                    cut[(name[:25], name)] += 1
                    cut_records[name[:25]].add(rid)
    # MRDS-style "Parent, Subtype" names inside NC's commodity text: the split
    # breaks each of them into two candidates
    compound = collections.defaultdict(set)
    for rid, r in src.items():
        v = "; ".join(x for x in (r["MajorCommodity"], r["MinorCommodity"], r["TraceCommodity"]) if x).casefold()
        for name in names:
            if "," in name and name in v:
                compound[name].add(rid)
        if "sand and gravel, construc" in v and "sand and gravel, construction" not in v:
            compound["Sand and Gravel, Construc (cut)"].add(rid)
        if "aluminum, contained or me" in v and "aluminum, contained or metal" not in v:
            compound["Aluminum, Contained or Me (cut)"].add(rid)
    # three states per (record, QID): today, today + the list, and a reader that
    # rejoins "Parent, Subtype" when MRDS has that name (repairing the two
    # 25-character cuts) and maps it by its MRDS code through commodity.csv
    MR = "https://minmod.isi.edu/resource/"
    NC = "https://www.deq.nc.gov/about/divisions/energy-mineral-and-land-resources/nc-geological-survey"
    by_code = collections.defaultdict(list)
    ents = {}
    with open(repo / "data/entities/commodity.csv", encoding="utf-8-sig") as f:
        for e in csv.DictReader(f):
            ents[e["minmod_id"]] = e
            if e["mrds_code"]:
                by_code[e["mrds_code"]].append(e["minmod_id"])
    repair = {"sand and gravel, construc": "sand and gravel, construction",
              "aluminum, contained or me": "aluminum, contained or metal"}
    list_rows = {}
    if corrections is not None:
        for r in csv.DictReader(open(corrections, encoding="utf-8")):
            if r["source_id"] == NC and r["context"] == "":
                list_rows[r["observed_name"]] = r
    three = collections.Counter()
    pairs = collections.Counter()
    root_only = collections.Counter()
    for rid, s in js.items():
        if rid not in src:
            continue
        lst = [((i["commodity"].get("observed_name") or ""), (i["commodity"].get("normalized_uri") or "")[len(MR):] or None) for i in s.get("mineral_inventory", [])]
        piece_q = {o.casefold(): q for o, q in lst}
        T = {q for _, q in lst if q}
        L = set()
        for o, q in lst:
            row = list_rows.get(o)
            if row is None or q is None:
                if q:
                    L.add(q)
            elif row["action"] == "remap":
                L.add(row["normalized_uri"][len(MR):])
        r = src[rid]
        joined = "; ".join(v for v in (r["MajorCommodity"], r["MinorCommodity"], r["TraceCommodity"]) if v)
        ps = procmine_pieces(joined)
        R, i = set(), 0
        while i < len(ps):
            pair = (ps[i] + ", " + ps[i + 1]).casefold() if i + 1 < len(ps) else None
            pair = repair.get(pair, pair)
            if pair is not None and "," in pair and pair in name2code:
                code = name2code[pair]
                if len(by_code.get(code, [])) == 1:
                    R.add(by_code[code][0])
                i += 2
                continue
            q = piece_q.get(ps[i].casefold())
            if q:
                R.add(q)
            i += 1
        if R == T:
            three["root: no change"] += 1
            continue
        three["root: matched commodities change"] += 1
        if L == R:
            three["list already gives the root result"] += 1
        for q in T - R:
            if q in L:
                is_parent = any(ents[x]["parent"] == q or ents[x]["name"].startswith(ents[q]["name"] + " > ") for x in R)
                key = "parent next to its own subtype" if is_parent else "wrong match, not in the list"
                pairs[f"removed by root only: {key}"] += 1
                if not is_parent:
                    root_only[f"{q} {ents[q]['name']}"] += 1
            else:
                pairs["removed by both list and root"] += 1
        for q in R - T:
            pairs["added by both list and root" if q in L else "added by root only"] += 1
    lengths = collections.Counter(len(r["MajorCommodity"]) for r in src.values() if r["MajorCommodity"])

    result = {
        "json_records": len(js),
        "service_points": len(src),
        "rebuild_vs_json": dict(cmp),
        "deposit_type_rebuild_vs_json": dict(dt_cmp),
        "compound_names_in_service": {k: len(v) for k, v in sorted(compound.items(), key=lambda kv: -len(kv[1]))},
        "compound_records_in_service": len(set().union(*compound.values())) if compound else 0,
        "differ_examples": examples,
        "major_commodity_length_24_25_26": [lengths[24], lengths[25], lengths[26]],
        "major_commodity_longer_than_25": sum(n for k, n in lengths.items() if k > 25),
        "three_states_records": dict(three),
        "three_states_record_qid_pairs": dict(pairs),
        "root_only_wrong_matches_by_qid": dict(root_only.most_common()),
        "cut_names": {f"{a} (from {b})": len(cut_records[a]) for (a, b) in cut},
        "mrds_names_longer_than_25": sorted(n for n in names if len(n) > 25),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "p5_rootcause_nc.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1)[:3000])


if __name__ == "__main__":
    main(*map(Path, sys.argv[1:6]))
