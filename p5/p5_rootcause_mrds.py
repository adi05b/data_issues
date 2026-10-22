"""Problem 5 root cause, MRDS: rebuild each record's commodity observed names from
the USGS MRDS comprehensive tables with ProcMine's own steps, and compare them
with the site JSON. Read-only; the MRDS download stays outside data_issues.

    python3 -I p5_rootcause_mrds.py <rdbms-tab-all dir> <ta2-minmod-data> <commodity-codes.html> out [corrections.csv]

ProcMine steps reproduced (umn-ta2-database-processing @ ce1ed70):
  _attribute.py:74     every mapped column is title-cased
  _procmine.py:210-212 'PGE' / 'REE' are replaced, case-insensitively, by
                       element lists (_entities/_commod_groups.pkl)
  _procmine.py:215-218 commodity is split on '|', ',' and ';'
The map file (sample_mapfile.csv) reads commodity from Commodity.commod and
Resource_detail.commod.

Writes out/p5_rootcause_mrds.json and out/p5_mrds_compound_names.csv.
"""

from __future__ import annotations

import collections
import csv
import html
import json
import re
import sys
from pathlib import Path

PGE = "Platinum; Palladium; Rhodium; Ruthenium; Iridium; Osmium"
REE = ("Lanthanum; Praseodymium; Samarium; Gadolinium; Thulium; Holmium; Cerium; "
       "Europium; Ytterbium; Erbium; Yttrium; Neodymium; Terbium; Dysprosium; Lutetium")
SPLIT = re.compile(r"\s*[\|,;]\s*")
MRDS = "https://mrdata.usgs.gov/mrds"
MR = "https://minmod.isi.edu/resource/"


def procmine_pieces(value: str) -> list[str]:
    v = re.sub("pge", PGE, value, flags=re.I)
    v = re.sub("ree", REE, v, flags=re.I)
    return [p for p in SPLIT.split(v) if p != ""]


def read_tab(path: Path):
    csv.field_size_limit(10**9)
    with open(path, newline="", encoding="latin-1") as f:
        yield from csv.DictReader(f, delimiter="\t")


def main(rdbms: Path, repo: Path, codes_html: Path, out: Path, corrections: Path | None = None):
    # one row per commodity: dep_id, commod, code
    rows = collections.defaultdict(list)
    for r in read_tab(rdbms / "Commodity.txt"):
        rows[r["dep_id"]].append((r["commod"], r["code"]))
    for r in read_tab(rdbms / "Resource_detail.txt"):
        rows[r["dep_id"]].append((r["commod"], r["code"]))

    # MinMod's commodity table: name and mrds_code
    ents = {r["minmod_id"]: r for r in csv.DictReader(open(repo / "data/entities/commodity.csv", encoding="utf-8-sig"))}
    by_code = collections.defaultdict(list)
    for q, r in ents.items():
        if r["mrds_code"]:
            by_code[r["mrds_code"]].append(q)

    # the site JSON: observed names and matched QIDs per MRDS record
    obs = {}
    qids = {}
    cand = collections.defaultdict(collections.Counter)  # observed -> (qid, conf)
    for f in sorted((repo / "data/mineral-sites/umn/mrdata_mrds").glob("*.json")):
        for s in json.load(open(f)):
            names = set()
            qs = set()
            for inv in s.get("mineral_inventory", []):
                c = inv["commodity"]
                names.add((c.get("observed_name") or "").casefold())
                u = c.get("normalized_uri")
                cand[c.get("observed_name")][(u[len(MR):] if u else None, round(c["confidence"], 4))] += 1
                if u:
                    qs.add(u[len(MR):])
            obs[str(s["record_id"])] = names
            qids[str(s["record_id"])] = qs

    cmp = collections.Counter()
    examples = []
    for rid, names in obs.items():
        pred = {p.casefold() for v, _ in rows.get(rid, []) for p in procmine_pieces(v)}
        if pred == names:
            cmp["equal"] += 1
        elif not rows.get(rid):
            cmp["record not in the 2019 tables"] += 1
        else:
            cmp["differ"] += 1
            if len(examples) < 10:
                examples.append({"dep_id": rid, "json": sorted(names), "rebuilt": sorted(pred)})

    # every MRDS commodity name that contains a comma: records, and what the
    # pieces became in the JSON
    compound = collections.defaultdict(lambda: {"code": None, "records": set()})
    for rid, lst in rows.items():
        if rid not in obs:
            continue
        for v, code in lst:
            if "," in v:
                compound[v]["code"] = code
                compound[v]["records"].add(rid)
    labels = {q: r["name"] for q, r in ents.items()}
    table = []
    for v, d in sorted(compound.items(), key=lambda kv: -len(kv[1]["records"])):
        pieces = procmine_pieces(v)
        sub = pieces[-1]
        (q, conf), _ = cand[sub.title()].most_common(1)[0] if cand[sub.title()] else ((None, None), 0)
        code_q = by_code.get(d["code"], [])
        code_q1 = code_q[0] if len(code_q) == 1 else None
        if code_q1 is None:
            verdict = "code has no MinMod entity"
        elif q == code_q1:
            verdict = "subtype piece hits the code's entity"
        else:
            verdict = "subtype piece hits another entity"
        table.append({
            "mrds_name": v, "mrds_code": d["code"], "records": len(d["records"]), "verdict": verdict,
            "pieces": " | ".join(p.title() for p in pieces),
            "subtype_piece_matched_to": f"{q} {labels.get(q, '')}".strip() if q else "unmatched",
            "confidence": conf,
            "minmod_entity_by_mrds_code": "; ".join(f"{x} {labels[x]}" for x in code_q) or "none",
        })

    # MRDS's own code list: names with a comma
    t = codes_html.read_text(encoding="utf-8", errors="replace")
    code_names = {}
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S | re.I):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S | re.I)]
        if len(cells) == 2 and cells[0] != "Code":
            code_names[cells[0]] = cells[1]

    # codes used by the MRDS records in the JSON, and whether commodity.csv maps them
    used = collections.Counter(code for rid, lst in rows.items() if rid in obs for _, code in set(lst))
    unmapped = {c: n for c, n in used.items() if c not in by_code}
    ambiguous = {c: by_code[c] for c in used if len(by_code.get(c, [])) > 1}

    by_verdict = collections.Counter()
    rec_by_verdict = collections.defaultdict(set)
    for t in table:
        by_verdict[t["verdict"]] += t["records"]
        rec_by_verdict[t["verdict"]] |= compound[t["mrds_name"]]["records"]

    # names that the case-insensitive PGE/REE replacement rewrites inside
    # another word (e.g. "Water, Free" -> "Water, F" + the REE list)
    infix = collections.Counter()
    for rid, lst in rows.items():
        if rid in obs:
            for v, code in set(lst):
                if re.search("pge|ree", v, re.I) and v.upper() not in ("PGE", "REE"):
                    infix[(v, code)] += 1

    # a reader that maps each MRDS commodity row by its code through
    # commodity.csv's mrds_code column, compared with today's matched QIDs
    sim = collections.Counter()
    removed = collections.Counter()
    added = collections.Counter()
    for rid, now in qids.items():
        lst = rows.get(rid, [])
        new = {by_code[c][0] for _, c in lst if len(by_code.get(c, [])) == 1}
        lost = {c for _, c in lst if c not in by_code}
        if new == now:
            sim["same matched commodities"] += 1
        else:
            sim["matched commodities change"] += 1
            for q in now - new:
                removed[f"{q} {labels.get(q, '')}"] += 1
            for q in new - now:
                added[f"{q} {labels.get(q, '')}"] += 1
        if lost:
            sim["has a code without a MinMod entity"] += 1

    # three states per (record, QID): today, today + the corrections list, and a
    # reader that keeps each MRDS commodity row whole and maps it by its code
    # (REE / PGE codes still expanded to their elements, as ProcMine intends)
    name2q = {r["name"]: q for q, r in ents.items()}
    expand = {
        "REE": {name2q[n] for n in REE.split("; ")},
        "PGE": {name2q[n] for n in PGE.split("; ")},
    }
    list_rows = {}
    if corrections is not None:
        for r in csv.DictReader(open(corrections, encoding="utf-8")):
            if r["source_id"] == MRDS and r["context"] == "":
                list_rows[r["observed_name"]] = r
    inv = collections.defaultdict(list)  # rid -> [(observed, qid)]
    for f in sorted((repo / "data/mineral-sites/umn/mrdata_mrds").glob("*.json")):
        for s in json.load(open(f)):
            for i in s.get("mineral_inventory", []):
                c = i["commodity"]
                u = c.get("normalized_uri")
                inv[str(s["record_id"])].append((c.get("observed_name"), u[len(MR):] if u else None))
    parents = {q: r["parent"] for q, r in ents.items() if r["parent"]}
    free_only = set()
    three = collections.Counter()
    pairs = collections.Counter()
    rec_cat = collections.Counter()
    wrong_only = collections.Counter()
    for rid, lst in inv.items():
        T = {q for _, q in lst if q}
        L = set()
        for o, q in lst:
            row = list_rows.get(o)
            if row is None or q is None:
                if q:
                    L.add(q)
            elif row["action"] == "remap":
                L.add(row["normalized_uri"][len(MR):])
        R = set()
        for _, code in rows.get(rid, []):
            if code in expand:
                R |= expand[code]
            elif len(by_code.get(code, [])) == 1:
                R.add(by_code[code][0])
        codes = {c for _, c in rows.get(rid, [])}
        if R == T:
            three["root: no change"] += 1
            continue
        three["root: matched commodities change"] += 1
        if L == R:
            three["list already gives the root result"] += 1
        cats = set()
        for q in T - R:
            if q in L:
                is_parent = any(
                    parents.get(x) == q or labels.get(x, "").startswith(labels.get(q, "?") + " > ")
                    for x in R
                )
                if is_parent:
                    why = "parent next to its own subtype code"
                elif "H2O" in codes and q in expand["REE"] and "REE" not in codes:
                    why = "phantom REE from 'Water, Free'"
                elif any(c not in by_code for c in codes):
                    why = "code has no MinMod entity (would be lost)"
                else:
                    why = "wrong match, not in the list"
                pairs[f"removed by root only: {why}"] += 1
                cats.add(why)
                if why == "wrong match, not in the list":
                    wrong_only[f"{q} {labels.get(q, '')}"] += 1
            else:
                pairs["removed by both list and root"] += 1
        for q in R - T:
            pairs["added by both list and root" if q in L else "added by root only"] += 1
        for c in cats:
            rec_cat[c] += 1
        for q in L - T:
            if q not in R:
                pairs["added by the list, not by root"] += 1
        for q in T - L:
            if q in R:
                pairs["removed by the list, kept by root"] += 1

    result = {
        "records_in_json": len(obs),
        "rebuild_vs_json": dict(cmp),
        "differ_examples": examples,
        "compound_names": len(table),
        "compound_records": len({r for d in compound.values() for r in d["records"]}),
        "mrds_code_list_names_with_comma": sum("," in n for n in code_names.values()),
        "codes_used": len(used),
        "codes_used_without_mrds_code_in_commodity_csv": unmapped,
        "codes_with_several_entities": ambiguous,
        "compound_records_by_verdict": dict(by_verdict),
        "compound_distinct_records_by_verdict": {k: len(v) for k, v in rec_by_verdict.items()},
        "pge_ree_inside_another_name": {f"{v} [{c}]": n for (v, c), n in infix.most_common()},
        "by_code_reader": dict(sim),
        "by_code_reader_qids_removed_top": dict(removed.most_common(25)),
        "by_code_reader_qids_added_top": dict(added.most_common(25)),
        "three_states_records": dict(three),
        "three_states_record_qid_pairs": dict(pairs),
        "three_states_records_by_root_only_reason": dict(rec_cat),
        "root_only_wrong_matches_by_qid": dict(wrong_only.most_common(30)),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "p5_rootcause_mrds.json").write_text(json.dumps(result, indent=1, default=str))
    with open(out / "p5_mrds_compound_names.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0].keys()))
        w.writeheader()
        w.writerows(table)
    print(json.dumps(result, indent=1, default=str)[:4000])


if __name__ == "__main__":
    main(*map(Path, sys.argv[1:6]))
