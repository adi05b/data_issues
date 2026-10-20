"""Problem 5: commodity candidates in the site JSON, raw-record grain. Read-only.

Walks <data repo>/data/mineral-sites/*/*/*.json and counts every
mineral_inventory[].commodity candidate (source, confidence, observed_name,
normalized_uri) as ProcMine and the other extractors wrote it. Nothing is
written outside <out dir>; no graph, Postgres or API is touched.

    .venv-p2/bin/python -I p5_scan.py <data repo> <out dir>

Writes
  <out>/candidates_census.csv  one row per (folder, source_id, matcher,
                               observed_name, normalized_uri, confidence)
  <out>/matchers.csv           per matcher: graded or constant
  <out>/p5_scan.json           every number quoted in P5_INVESTIGATION.md
  run-big/defect_records.csv  every record that carries a defect (site_id
                               included); next to <out>, ignored by git (> 1 MB)
"""

from __future__ import annotations

import collections
import csv
import json
import random
import sys
from pathlib import Path

# the six defects of the earlier diagnosis, keyed on the observed string and
# the source, exactly as the earlier exclusion rules were
OREGON = "http://www.oregongeology.org"
DEFECTS = {
    "Construction->Strontium": dict(obs="Construction", uri="Q609"),
    "SC->Scandium (Oregon)": dict(obs="SC", uri="Q607", src=OREGON),
    "S->Sulfur (Oregon)": dict(obs="S", uri="Q633", src=OREGON),
    "Construc->Cobalt": dict(obs="Construc", uri="Q537"),
    "CS->Cesium (Oregon)": dict(obs="CS", uri="Q591", src=OREGON),
    # not in the earlier table: Oregon's "stone | dimension | SD" (see H4)
    "SD->Sand (Oregon)": dict(obs="SD", uri="Q655", src=OREGON),
    "Metal->Nonmetal": dict(obs="Metal", uri="Q581"),
}
SAND_AND_GRAVEL = {"Q656"}  # Sand and Gravel; Q655 Sand is its parent
SAND = {"Q655", "Q656"}
FLOOR = 0.62


def qid(uri):
    return uri.rsplit("/", 1)[-1] if uri else None


def username(created_by: str) -> str:
    # minmodkg.models.kgrel.user.get_username: the last path segment
    return created_by.rstrip("/").rsplit("/", 1)[-1]


def site_id(created_by, source_id, record_id):
    # minmodkg.transformations.make_site_id, imported when available so the id
    # matches the merge exactly
    from minmodkg.transformations import make_site_id

    return make_site_id(username(created_by), source_id, str(record_id))


def has_gt(inv: dict) -> bool:
    """grade, ore (tonnage) or ProcMine's contained_metal carries a number"""
    for key in ("grade", "ore", "cutoff_grade"):
        m = inv.get(key) or {}
        if m.get("value") is not None:
            return True
    return inv.get("contained_metal") is not None


def defect_of(src, obs, uri):
    for name, d in DEFECTS.items():
        if obs != d["obs"]:
            continue
        if "src" in d and src != d["src"]:
            continue
        if "uri" in d and qid(uri) != d["uri"]:
            continue
        if uri is None:
            continue
        return name
    return None


def main(repo: Path, out: Path):
    big = out.parent / "run-big"
    big.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    labels = {
        r["minmod_id"]: r["name"]
        for r in csv.DictReader(open(repo / "data/entities/commodity.csv", encoding="utf-8-sig"))
    }

    census = collections.Counter()  # key -> n inventories
    census_rec = collections.defaultdict(set)  # key -> record keys
    census_gt = collections.Counter()
    inv_keys = collections.Counter()
    n_records = 0
    n_inv = 0
    files = sorted((repo / "data/mineral-sites").glob("*/*/*.json"))

    # per defect
    d_inv = collections.Counter()
    d_inv_gt = collections.Counter()
    d_rec = collections.defaultdict(set)
    d_rec_gt = collections.defaultdict(set)
    d_by_src = collections.Counter()
    d_rec_only = collections.Counter()  # record has no other matched commodity
    d_rec_sg = collections.Counter()  # record also has Sand and Gravel (Q656)
    d_rec_sand = collections.Counter()  # ... Sand or Sand and Gravel
    d_rec_gt_kg = collections.Counter()  # gt complete enough for kg's model
    siblings = collections.defaultdict(collections.Counter)
    examples = {}
    defect_rows = []
    graded_below = []  # (matcher, obs, uri, conf, file, record_id) below FLOOR
    oregon_names = collections.defaultdict(collections.Counter)
    oregon_patterns = collections.Counter()  # the record's observed strings, in order
    h8 = collections.defaultdict(set)  # (code, matched?, source, matcher) -> records
    h8_inv = collections.Counter()

    for f in files:
        folder = f"{f.parent.parent.name}/{f.parent.name}"
        for r in json.load(open(f)):
            n_records += 1
            src = r["source_id"]
            rid = str(r["record_id"])
            rkey = (r["created_by"], src, rid)
            invs = r.get("mineral_inventory", [])
            matched = []
            for inv in invs:
                n_inv += 1
                inv_keys.update(inv.keys())
                c = inv["commodity"]
                obs, uri, conf, m = (
                    c.get("observed_name"),
                    c.get("normalized_uri"),
                    c.get("confidence"),
                    c.get("source"),
                )
                key = (folder, src, m, obs, qid(uri), round(conf, 4) if conf is not None else None)
                census[key] += 1
                census_rec[key].add(rkey)
                gt = has_gt(inv)
                if gt:
                    census_gt[key] += 1
                if uri is not None:
                    matched.append((obs, qid(uri)))
                if (
                    uri is not None
                    and m == "UMN Matching System-ProcMinev2"
                    and conf is not None
                    and conf < FLOOR
                ):
                    graded_below.append((m, obs, qid(uri), conf, str(f.relative_to(repo)), rid))
            hits = []
            for inv in invs:
                c = inv["commodity"]
                name = defect_of(src, c.get("observed_name"), c.get("normalized_uri"))
                if name is None:
                    continue
                hits.append(name)
                d_inv[name] += 1
                d_rec[name].add(rkey)
                d_by_src[(name, src)] += 1
                if has_gt(inv):
                    d_inv_gt[name] += 1
                    d_rec_gt[name].add(rkey)
                if name not in examples:
                    examples[name] = {
                        "file": str(f.relative_to(repo)),
                        "record_id": rid,
                        "name": r.get("name"),
                        "commodity": c,
                        "siblings": [i["commodity"] for i in invs if i is not inv],
                    }
            for name in set(hits):
                obs_d = DEFECTS[name]["obs"]
                others = [(o, q) for o, q in matched if o != obs_d]
                if not others:
                    d_rec_only[name] += 1
                if any(q in SAND_AND_GRAVEL for _, q in others):
                    d_rec_sg[name] += 1
                if any(q in SAND for _, q in others):
                    d_rec_sand[name] += 1
                siblings[name][" | ".join(sorted({o or "" for o, _ in others})) or "(none)"] += 1
                defect_rows.append(
                    {
                        "defect": name,
                        "site_id": site_id(*rkey),
                        "source_id": src,
                        "record_id": rid,
                        "file": str(f.relative_to(repo)),
                        "has_gt": int(any(has_gt(i) for i in invs if defect_of(src, i["commodity"].get("observed_name"), i["commodity"].get("normalized_uri")) == name)),
                        "other_commodities": " | ".join(sorted({q for _, q in others if q})),
                    }
                )
            for inv in invs:
                c = inv["commodity"]
                o = (c.get("observed_name") or "").strip()
                if o.upper() in ("PGE", "REE", "HAL"):
                    k = (o, c.get("normalized_uri") is not None, src, c.get("source"))
                    h8[k].add(rkey)
                    h8_inv[k] += 1
            if src == OREGON:
                oregon_patterns[" | ".join(i["commodity"].get("observed_name") or "" for i in invs)] += 1
                obs_set = sorted({i["commodity"].get("observed_name") or "" for i in invs})
                for o in obs_set:
                    oregon_names[o][" | ".join(obs_set)] += 1

    # ---- outputs
    with open(out / "candidates_census.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["folder", "source_id", "matcher", "observed_name", "normalized_qid", "label", "confidence", "inventories", "records", "inventories_with_gt"])
        for key, n in sorted(census.items(), key=lambda kv: -kv[1]):
            folder, src, m, obs, q, conf = key
            w.writerow([folder, src, m, obs, q, labels.get(q, "") if q else "", conf, n, len(census_rec[key]), census_gt[key]])

    # matcher census: graded vs constant
    mstats = collections.defaultdict(lambda: {"matched": 0, "unmatched": 0, "conf_matched": collections.Counter(), "conf_unmatched": collections.Counter()})
    for (folder, src, m, obs, q, conf), n in census.items():
        s = mstats[m]
        if q:
            s["matched"] += n
            s["conf_matched"][conf] += n
        else:
            s["unmatched"] += n
            s["conf_unmatched"][conf] += n
    with open(out / "matchers.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["matcher", "matched", "unmatched", "distinct_conf_matched", "min_conf_matched", "max_conf_matched", "top_conf_matched", "distinct_conf_unmatched", "top_conf_unmatched"])
        for m, s in sorted(mstats.items(), key=lambda kv: -(kv[1]["matched"] + kv[1]["unmatched"])):
            cm, cu = s["conf_matched"], s["conf_unmatched"]
            w.writerow([
                m, s["matched"], s["unmatched"], len(cm),
                min(cm) if cm else "", max(cm) if cm else "",
                "; ".join(f"{k}:{v}" for k, v in cm.most_common(3)),
                len(cu), "; ".join(f"{k}:{v}" for k, v in cu.most_common(3)),
            ])

    with open(big / "defect_records.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(defect_rows[0].keys()))
        w.writeheader()
        w.writerows(defect_rows)

    # random sample for H5, fixed seed so it can be re-drawn
    rng = random.Random(20261020)
    sample = rng.sample(graded_below, 100)
    with open(out / "h5_sample_below_062.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["i", "matcher", "observed_name", "normalized_qid", "label", "confidence", "file", "record_id", "verdict"])
        for i, (m, obs, q, conf, file, rid) in enumerate(sample, 1):
            w.writerow([i, m, obs, q, labels.get(q, ""), round(conf, 4), file, rid, ""])
    below_pairs = collections.Counter((obs, q) for _, obs, q, _, _, _ in graded_below)
    below_conf = {}
    for _, obs, q, conf, _, _ in graded_below:
        below_conf[(obs, q)] = round(conf, 4)
    with open(out / "h5_pairs_below_062.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["observed_name", "normalized_qid", "label", "confidence", "inventories", "verdict"])
        for (obs, q), n in below_pairs.most_common():
            w.writerow([obs, q, labels.get(q, ""), below_conf[(obs, q)], n, ""])

    summary = {
        "files": len(files),
        "records": n_records,
        "inventories": n_inv,
        "inventory_keys": dict(inv_keys),
        "graded_below_floor_inventories": len(graded_below),
        "graded_below_floor_distinct_pairs": len(below_pairs),
        "defects": {
            name: {
                "inventories": d_inv[name],
                "records": len(d_rec[name]),
                "inventories_with_gt": d_inv_gt[name],
                "records_with_gt": len(d_rec_gt[name]),
                "records_no_other_matched_commodity": d_rec_only[name],
                "records_also_sand_and_gravel_Q656": d_rec_sg[name],
                "records_also_sand_Q655_or_Q656": d_rec_sand[name],
                "by_source": {s: n for (nm, s), n in d_by_src.items() if nm == name},
                "top_siblings": siblings[name].most_common(12),
                "example": examples.get(name),
            }
            for name in DEFECTS
        },
        "oregon_cooccurrence": {o: c.most_common(8) for o, c in oregon_names.items()},
        "oregon_code_patterns": {
            k: n for k, n in oregon_patterns.most_common()
            if set(k.split(" | ")) & {"S", "SC", "CS", "SD", "G"}
        },
        "h8": [
            {"code": k[0], "matched": k[1], "source_id": k[2], "matcher": k[3],
             "records": len(v), "inventories": h8_inv[k]}
            for k, v in sorted(h8.items(), key=lambda kv: -len(kv[1]))
        ],
    }
    (out / "p5_scan.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps({k: v for k, v in summary.items() if k != "oregon_cooccurrence"}, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
