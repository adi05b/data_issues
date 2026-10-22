"""Problem 5 root cause, Oregon DOGAMI: compare the site JSON with MILO-4
(gis.dogami.oregon.gov .../Public/MILO/MapServer/1, "MILO Points"), read-only.

    python3 -I p5_rootcause_oregon.py <milo4_points.json> <ta2-minmod-data> out

milo4_points.json is every point's attributes (MILO_ID, Commodity, Type,
CommodityAbbreviation, ...), fetched 2026-10-22. MILO's metadata defines
Commodity as "a comma separated list" and CommodityAbbreviation as "a 'space'
separated list".

The Oregon candidates carry the matcher label "UMN Matching System v1", whose
code is not public. Its split is inferred here from input and output.
"""

from __future__ import annotations

import collections
import csv
import json
import re
import sys
from pathlib import Path

OREGON = "http://www.oregongeology.org"
CODES = ["SC", "SD", "CS", "S", "G"]
RULES = {
    # rule name -> how each column is split
    "Commodity on ',' + CommodityAbbreviation on '&'": (r"\s*,\s*", r"\s*&\s*"),
    "both on ',' ';' '|' (ProcMinev2's rule)": (r"\s*[\|,;]\s*", r"\s*[\|,;]\s*"),
}


def pieces(value: str | None, pattern: str) -> list[str]:
    return [p for p in re.split(pattern, value or "") if p != ""]


def main(points: Path, repo: Path, out: Path):
    milo = collections.defaultdict(list)
    for r in json.load(open(points)):
        milo[r["MILO_ID"]].append(r)
    js = {}
    for f in sorted((repo / "data/mineral-sites/umn/oregon_department_geology_mineral_industries").glob("*.json")):
        for s in json.load(open(f)):
            js[s["record_id"]] = [i["commodity"].get("observed_name") or "" for i in s.get("mineral_inventory", [])]

    # an exact, case-insensitive lookup on commodity.csv's name, aliases,
    # geokb_name and mrds_code, as ProcMine's own table (_selected_cols.pkl)
    exact = {}
    with open(repo / "data/entities/commodity.csv", encoding="utf-8-sig") as f:
        for e in csv.DictReader(f):
            for col in ("name", "aliases", "geokb_name", "mrds_code"):
                for v in (e[col] or "").split("|"):
                    if v.strip():
                        exact.setdefault(v.strip().casefold(), e["minmod_id"])

    def dedup(names: list[str]) -> list[str]:
        """drop a piece whose exact match is an entity an earlier piece has"""
        seen, keep = set(), []
        for n in names:
            q = exact.get(n.casefold())
            if q is not None and q in seen:
                continue
            seen.add(q)
            keep.append(n)
        return keep

    RULES["Commodity on ',' + CommodityAbbreviation on '&', repeats of an entity dropped"] = RULES[
        "Commodity on ',' + CommodityAbbreviation on '&'"
    ]
    cmp = {name: collections.Counter() for name in RULES}
    defect_cmp = collections.Counter()
    examples = collections.defaultdict(list)
    for rid, obs in js.items():
        rows = milo.get(rid)
        if not rows:
            for c in cmp.values():
                c["record not in MILO-4"] += 1
            continue
        r = rows[0]
        for name, (pc, pa) in RULES.items():
            pred = pieces(r["Commodity"], pc) + pieces(r["CommodityAbbreviation"], pa)
            if "repeats" in name:
                pred = dedup(pred)
                if set(obs) & {"SC", "SD", "CS", "S"}:
                    defect_cmp["equal" if pred == obs else "differ"] += 1
            if pred == obs:
                cmp[name]["equal, in order"] += 1
            elif sorted(set(pred)) == sorted(set(obs)):
                cmp[name]["same names, other order or repeats"] += 1
            else:
                cmp[name]["differ"] += 1
                if len(examples[name]) < 5:
                    examples[name].append({"MILO_ID": rid, "Commodity": r["Commodity"], "CommodityAbbreviation": r["CommodityAbbreviation"], "json": obs})

    # where each candidate came from, for the records the inferred rule rebuilds
    # exactly: the Commodity column or the CommodityAbbreviation column
    MR = "https://minmod.isi.edu/resource/"
    names = {}
    with open(repo / "data/entities/commodity.csv", encoding="utf-8-sig") as f:
        for e in csv.DictReader(f):
            names[e["minmod_id"]] = e["name"]
    full = {}
    for f in sorted((repo / "data/mineral-sites/umn/oregon_department_geology_mineral_industries").glob("*.json")):
        for s in json.load(open(f)):
            full[s["record_id"]] = [((i["commodity"].get("observed_name") or ""), (i["commodity"].get("normalized_uri") or "")[len(MR):] or None) for i in s.get("mineral_inventory", [])]
    pc, pa = RULES["Commodity on ',' + CommodityAbbreviation on '&'"]
    origin = collections.Counter()
    abbr_matched = collections.Counter()
    only_from_abbr = []
    compound = collections.Counter()
    for rid, lst in full.items():
        r = (milo.get(rid) or [None])[0]
        if r is None:
            continue
        com = pieces(r["Commodity"], pc)
        pred = dedup(com + pieces(r["CommodityAbbreviation"], pa))
        if pred != [o for o, _ in lst]:
            continue
        origin["records rebuilt exactly"] += 1
        if "," in (r["Commodity"] or ""):
            compound[r["Commodity"]] += 1
        from_com = [x for x in lst[: len(com)]]
        from_abbr = [x for x in lst[len(com):]]
        origin["inventories from Commodity"] += len(from_com)
        origin["inventories from CommodityAbbreviation"] += len(from_abbr)
        origin["  of which matched"] += sum(1 for _, q in from_abbr if q)
        for o, q in from_abbr:
            if q:
                abbr_matched[f"{o} -> {q} {names.get(q, '')}"] += 1
        if any(q for _, q in from_abbr) and not any(q for _, q in from_com):
            only_from_abbr.append({"MILO_ID": rid, "Commodity": r["Commodity"], "CommodityAbbreviation": r["CommodityAbbreviation"]})

    # what each code sits next to, in MILO-4 itself
    cooc = {c: collections.Counter() for c in CODES + ["S&G"]}
    for rows in milo.values():
        for r in rows:
            abbr = r["CommodityAbbreviation"] or ""
            toks = set(abbr.split()) | set(pieces(abbr, r"\s*&\s*|\s+"))
            for c in cooc:
                if c in toks or (c == "S&G" and "S&G" in abbr):
                    cooc[c][f"{r['Commodity']} [{abbr}]"] += 1

    # which commodity.csv column holds each code as a key, case-insensitively
    keys = collections.defaultdict(list)
    with open(repo / "data/entities/commodity.csv", encoding="utf-8-sig") as f:
        for e in csv.DictReader(f):
            for col in ("name", "aliases", "geokb_name", "mrds_code"):
                for v in (e[col] or "").split("|"):
                    if v.strip().casefold() in {c.casefold() for c in CODES}:
                        keys[v.strip().upper()].append(f"{e['minmod_id']} {e['name']} ({col} = {v.strip()})")

    result = {
        "json_records": len(js),
        "milo4_points": sum(len(v) for v in milo.values()),
        "milo4_ids_with_several_points": sum(1 for v in milo.values() if len(v) > 1),
        "json_ids_in_milo4": sum(1 for k in js if k in milo),
        "rebuild_vs_json": {k: dict(v) for k, v in cmp.items()},
        "defect_records_rebuild_vs_json": dict(defect_cmp),
        "differ_examples": examples,
        "candidate_origin": dict(origin),
        "abbreviation_candidates_matched": dict(abbr_matched.most_common(25)),
        "records_whose_only_matches_come_from_the_abbreviation": len(only_from_abbr),
        "only_from_abbreviation_examples": only_from_abbr[:8],
        "last_chance_sulfur_mine_among_them": any(x["MILO_ID"] == "ID_04514" for x in only_from_abbr),
        "commodity_values_with_a_comma": dict(compound.most_common(15)),
        "code_cooccurrence_in_milo4": {c: v.most_common(8) for c, v in cooc.items()},
        "commodity_csv_keys_equal_to_codes": {c: keys.get(c, []) for c in CODES},
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "p5_rootcause_oregon.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1)[:6000])


if __name__ == "__main__":
    main(*map(Path, sys.argv[1:4]))
