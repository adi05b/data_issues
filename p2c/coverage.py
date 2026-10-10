#!/usr/bin/env python3
"""Problem 2, Solution C: what could point-in-shape filling do for the 313 emptied
merged entities and the 338 dropped records? Read-only; writes into p2c/.

Inputs (all reproduced in rerun/, see BOUNDARY_MATCH_v2.md):
  rerun/reports/p2d/dropped_after.jsonl     340 dropped candidates on 338 records
  rerun/reports/p2d/merged_outcomes.json    5,856 conflicted entities, 313 emptied in run C
  rerun/runs/kg-C/data/mineral-sites/merged entity -> member records (run C)
  rerun/data/fork/data/mineral-sites        raw records (location WKT, CRS)
  rerun/scripts/p2c_alias_candidates.py     the per-group notes the reports use
  state_shape_match.csv                     MinMod state <-> gB shape (Step 1)
  geoboundaries_full/<ISO3>_ADM1.geojson    full-resolution gbOpen ADM1

    python coverage.py      (needs shapely and serde, e.g. the .venv-p2 python)

Writes emptied_313.csv, dropped_338.csv, coverage_results.json.
"""

from __future__ import annotations

import collections
import csv
import glob
import json
import re
import sys
from pathlib import Path

import serde.json
from shapely import wkt
from shapely.geometry import MultiPoint, Point, shape
from shapely.ops import unary_union
from shapely.prepared import prep

HERE = Path(__file__).resolve().parent
RR = HERE / "rerun"
FORK = RR / "data/fork/data"
ENT = FORK / "entities"

# p2c_alias_candidates imports p2c_drop_list, which needs minmodkg on the path; only its tables are used here
sys.path.insert(0, str(RR / "scripts"))
import p2c_alias_candidates as ac  # noqa: E402

countries = list(csv.DictReader(open(ENT / "country.csv", newline="", encoding="utf-8")))
cid = {c["minmod_id"]: c for c in countries}
cname = {c["minmod_id"]: c["name"] for c in countries}

# Option A: the four implemented pairs (reports/P2_OPTION_A.md)
OPTION_A = {
    ("Territory Of New Caledonia And Dependencies", "France"): "New Caledonia",
    ("Greenland", "Denmark"): "Greenland",
    ("Territory Of Christmas Island", "Australia"): "Christmas Island",
    ("Montserrat", "United Kingdom"): "Montserrat",
}


def reason(obs: str, country: str) -> tuple[str, str]:
    """Map a (observed name, recorded country) group to the report's reason groups, from the reports' own notes."""
    k = (obs, country)
    if k in OPTION_A:
        return "Option A", OPTION_A[k]
    if obs in ("Katanga", "Katanga Province"):
        return "Katanga", ""
    note = ac.NO_SUGGESTION.get(k) or (ac.REJECTED_ON_COORDINATES.get(k) or (None, None, ""))[2] or ""
    if k in ac.BLOCKED:
        return "other", "blocked, waiting on a decision"
    if k in ac.REJECTED_ON_COORDINATES:
        return "other", "alias rejected on coordinates: " + note
    n = note.lower()
    if country == "Greenland" or "greenland rows" in n:
        return "Greenland", note
    if note.startswith(ac.WRONG_COUNTRY):
        return "wrong recorded country", note
    if re.search(r"\b(a city|a town)\b", n):
        return "city", note
    if re.search(r"\bisland|peninsula", n):
        return "island", note
    if re.search(r"\b(former|abolished|dissolved|merged into|split|historical)\b", n):
        return "abolished unit", note
    if re.search(r"\b(county|district|municipality|constituency|zone of|province inside|province and city)\b", n):
        return "county", note
    return "other", note


# ---- gB shapes and the Step 1 mapping
def load_country(iso3):
    p = HERE / f"geoboundaries_full/{iso3}_ADM1.geojson"
    if not p.exists():
        return None
    feats = json.load(open(p, encoding="utf-8"))["features"]
    return [(f["properties"], prep(shape(f["geometry"])), shape(f["geometry"])) for f in feats]


_cache: dict = {}


def shapes_for(iso3):
    if iso3 not in _cache:
        _cache[iso3] = load_country(iso3)
    return _cache[iso3]


gb_meta = {m["boundaryISO"]: m for m in json.load(open(HERE / "geoboundaries/api_ALL_ADM1.json", encoding="utf-8"))}
match = list(csv.DictReader(open(HERE / "state_shape_match.csv", newline="", encoding="utf-8")))
# (country_code, shapeISO, shapeName) -> MinMod states that matched it, and whether each match is single
claims = collections.defaultdict(list)
for m in match:
    if not m["shapeName"]:
        continue
    single = m["match_tier"] in ("iso", "name", "alt name")
    for iso, name in zip(m["shapeISO"].split(" | "), m["shapeName"].split(" | ")):
        claims[(m["country_code"], iso, name)].append((m["minmod_id"], m["name"], single))


def usable_point(loc: str, crs: str):
    """(geometry, reason): WGS84 or unset CRS, a POINT or MULTIPOINT, not 0,0, not a round placeholder."""
    if not loc:
        return None, "no location"
    if crs not in ("", "Q701"):
        return None, f"not WGS84 ({crs})"
    try:
        g = wkt.loads(loc)
    except Exception:
        return None, "unparseable WKT"
    pts = [g] if isinstance(g, Point) else list(g.geoms) if isinstance(g, MultiPoint) else None
    if not pts:
        return None, f"not a point ({g.geom_type})"
    if all(p.x == 0 and p.y == 0 for p in pts):
        return None, "0,0"
    if all((p.x * 2).is_integer() and (p.y * 2).is_integer() for p in pts):
        return None, "round placeholder"
    return pts, ""


def assess(pts, why, country_ids):
    """The C outcome for one location under its recorded country (or countries)."""
    if pts is None:
        return "no usable point", why, "", ""
    iso3s = [cid[c]["iso3"] for c in country_ids]
    have = [i for i in iso3s if i in gb_meta]
    if not have:
        return "no ADM1 for country", ",".join(iso3s), "", ""
    hits = set()
    for iso3 in have:
        for props, pg, _ in shapes_for(iso3):
            for p in pts:
                if pg.contains(p):
                    hits.add((cid_of_iso3[iso3], props.get("shapeISO") or "", props["shapeName"]))
    shape_per_point = len(hits)
    if not hits:
        return "point outside the recorded country", ",".join(have), "", ""
    if shape_per_point > 1:
        return "multipoint spans shapes", "", " | ".join(h[2] for h in hits), ""
    cc, iso, name = hits.pop()
    states = claims.get((cc, iso, name), [])
    if not states:
        return "point in a shape with no MinMod match", "", name, ""
    if len(states) == 1 and states[0][2]:
        return "fillable", "", name, f"{states[0][0]} {states[0][1]}"
    return "point in an ambiguous shape", "", name, " | ".join(f"{s[0]} {s[1]}" for s in states)


cid_of_iso3 = {c["iso3"]: c["iso2"] for c in countries}

# ---- raw records by site id (only the files we need)
dropped = [json.loads(line) for line in open(RR / "reports/p2d/dropped_after.jsonl", encoding="utf-8")]
assert len(dropped) == 340 and len({d["site_id"] for d in dropped}) == 338


def main():
    # records referenced by the dropped candidates, via their file; matched to site ids with MinMod's own code
    from minmodkg.models.kg.mineral_site import MineralSiteIdent

    want_files = collections.defaultdict(set)
    for d in dropped:
        want_files[d["file"]].add(d["site_id"])

    # entity -> member site ids, run C
    members = collections.defaultdict(list)
    for p in sorted((RR / "runs/kg-C/data/mineral-sites/merged").glob("*/*")):
        for x in serde.json.deser(p)["DedupMineralSite"]:
            for r in x["ranked_sites"]:
                members[x["id"]].append(r["site_id"])
    outcomes = json.load(open(RR / "reports/p2d/merged_outcomes.json", encoding="utf-8"))
    emptied = {e: v for e, v in outcomes.items() if v["outcome"]["C"] == "state emptied"}
    assert len(emptied) == 313

    dropped_ids = {d["site_id"] for d in dropped}
    ent_members = {e: [s for s in dict.fromkeys(members[e]) if s in dropped_ids] for e in emptied}

    recs = {}
    for f, ids in want_files.items():
        for rec in json.load(open(FORK / "mineral-sites" / f, encoding="utf-8")):
            sid = MineralSiteIdent.from_dict(rec).id
            if sid in ids:
                recs[sid] = rec
    assert set(recs) == dropped_ids, len(dropped_ids - set(recs))

    def loc_of(sid):
        li = recs[sid].get("location_info") or {}
        loc = (li.get("location") or "").strip()
        crs = ((li.get("crs") or {}).get("normalized_uri") or "").rsplit("/", 1)[-1]
        return loc, crs

    # ---- dropped_338: one row per record
    by_rec = collections.defaultdict(list)
    for d in dropped:
        by_rec[d["site_id"]].append(d)
    rows_d = []
    for sid, ds in by_rec.items():
        obs = " | ".join(dict.fromkeys(d["observed_name"] or "" for d in ds))
        ctry = ds[0]["recorded_country_names"]
        grp, note = reason(ds[0]["observed_name"] or "", ctry)
        loc, crs = loc_of(sid)
        pts, why = usable_point(loc, crs)
        out, detail, shp, st = assess(pts, why, ds[0]["recorded_countries"])
        rows_d.append({"record_id": sid, "recorded_country": ctry, "observed_state": obs, "dropped_candidates": len(ds),
                       "reason_group": grp, "reason_note": note, "kind": ds[0]["kind"], "location_wkt": loc, "crs": crs,
                       "c_outcome": out, "c_detail": detail, "containing_shape": shp, "would_fill_with": st})

    # ---- emptied_313: one row per merged entity; location from its dropped member(s)
    rows_e = []
    for e, v in emptied.items():
        ms = ent_members[e]
        merged_country = v["C"]["country"]["value"]
        if not ms:
            rows_e.append({"entity_id": e, "recorded_country": " | ".join(cname.get(c, c) for c in merged_country),
                           "observed_state": "", "member_records": 0, "reason_group": "other",
                           "reason_note": "no member in the dropped list", "location_wkt": "", "crs": "",
                           "c_outcome": "no usable point", "c_detail": "no dropped member", "containing_shape": "",
                           "would_fill_with": "", "member_record_used": ""})
            continue
        sid = ms[0]
        d = by_rec[sid][0]
        grp, note = reason(d["observed_name"] or "", d["recorded_country_names"])
        loc, crs = loc_of(sid)
        pts, why = usable_point(loc, crs)
        out, detail, shp, st = assess(pts, why, merged_country)
        rows_e.append({"entity_id": e, "recorded_country": " | ".join(cname.get(c, c) for c in merged_country),
                       "observed_state": d["observed_name"], "member_records": len(ms), "reason_group": grp,
                       "reason_note": note, "location_wkt": loc, "crs": crs, "c_outcome": out, "c_detail": detail,
                       "containing_shape": shp, "would_fill_with": st, "member_record_used": sid})

    for name, rows in (("dropped_338.csv", rows_d), ("emptied_313.csv", rows_e)):
        with open(HERE / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    def tables(rows):
        return {"by_outcome": collections.Counter(r["c_outcome"] for r in rows),
                "by_reason": {g: dict(collections.Counter(r["c_outcome"] for r in rows if r["reason_group"] == g))
                              for g in sorted({r["reason_group"] for r in rows})}}

    res = {"dropped_338": tables(rows_d), "emptied_313": tables(rows_e)}
    for key, rows in (("dropped_338", rows_d), ("emptied_313", rows_e)):
        oa = collections.defaultdict(collections.Counter)
        for r in rows:
            if r["reason_group"] == "Option A":
                oa[f'{r["reason_note"]} (recorded: {r["recorded_country"]})'][r["c_outcome"] + (f' [{r["containing_shape"]}]' if r["containing_shape"] else "")] += 1
        res[key]["option_a"] = {k: dict(v) for k, v in oa.items()}
        res[key]["fillable_by_country"] = dict(collections.Counter(r["recorded_country"] for r in rows if r["c_outcome"] == "fillable"))
    res["emptied_with_multiple_dropped_members"] = sum(1 for r in rows_e if r["member_records"] > 1)
    (HERE / "coverage_results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps({k: {"by_outcome": v["by_outcome"]} for k, v in res.items() if isinstance(v, dict)}, indent=1))


if __name__ == "__main__":
    main()
