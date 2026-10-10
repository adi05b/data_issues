"""Problem 3, Phase A: coordinate precision at merge time. Read-only.

Reads the merged files of an offline ETL run (p2c/rerun/scripts/p2d_run_merge.py,
run with main's code on the base data) and rebuilds each merged site with main's
own DedupMineralSite.from_dedup_sites, exactly as prep_kgrel_input does. Nothing
touches a graph, Postgres or the API.

  A1  precision of every record's raw source WKT (location.coordinates, as the
      data repo wrote it), by geometry type, CRS and source; DMS-looking values
  A2  merged sites with >= 2 member records that have a coordinate: which
      coordinate main keeps, how many keep a coarser one, why, and what the
      proposed fix (precision tie-break on equal score + Null Island as no
      coordinate) would change, simulated on a copy of the selection logic

    CFG_FILE=<main>/tests/resources/config.yml PYTHONPATH=<main> \\
      .venv-p2/bin/python p3_measure.py <run dir> <out dir>
"""

from __future__ import annotations

import collections
import functools
import csv
import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Callable, NamedTuple, Optional

import serde.json
from pyproj import CRS

from minmodkg.models.kgrel.custom_types import SiteScore
from minmodkg.models.kgrel.dedup_mineral_site import DedupMineralSite
from minmodkg.models.kgrel.mineral_site import MineralSiteAndInventory
from minmodkg.services.kgrel_entity import FileEntityService

NUMBER = re.compile(r"[-+]?(\d*)(?:\.(\d*))?(?:[eE]([-+]?\d+))?")
KM_PER_DEGREE = 111.32

# ---------------------------------------------------------------- parsing


def dp(s: str) -> int:
    """Decimal places of a number as written ('45.10' -> 2, '1.5e-3' -> 4)."""
    m = NUMBER.fullmatch(s)
    return max(len(m.group(2) or "") - int(m.group(3) or 0), 0)


def eff_dp(s: str) -> int:
    """Decimal places once trailing zeros and float noise are dropped:
    '45.2500' -> 2, '45.31800000000000017' -> 3, '-71.9588888888888931' -> 13."""
    return min(dp(s), dp(repr(float(s))))


def float_print(s: str) -> bool:
    """15+ significant digits even after dropping noise: a machine float, e.g.
    '868492.6492782086'. Its decimal places say how big the number is, not how
    precise it is."""
    return len(re.sub(r"e.*|[-+.]", "", repr(abs(float(s)))).lstrip("0")) >= 15


def xy_tokens(wkt: str) -> list[tuple[str, str]]:
    """The x and y of every coordinate tuple in a WKT, as written. Z/M dropped,
    an EWKT 'SRID=n;' prefix ignored, 'EMPTY' gives []."""
    wkt = re.sub(r"^\s*SRID=\d+;", "", wkt)
    out = []
    for part in re.split(r"[(),]", wkt):
        toks = part.split()
        if len(toks) >= 2 and all(NUMBER.fullmatch(t) and any(c.isdigit() for c in t) for t in toks):
            out.append((toks[0], toks[1]))
    return out


def on_grid(s: str, per_degree: int) -> bool:
    """A whole number of arcminutes (60) or arcseconds (3600), within what the
    value's own digits can carry."""
    x = abs(float(s)) * per_degree
    return abs(x - round(x)) <= per_degree * 0.5 * 10 ** -eff_dp(s) + 1e-9


def axis_dms(s: str) -> Optional[str]:
    """'long' if a long decimal (>= 6 places after dropping padding) sits on the
    arcsecond grid, e.g. .1666667 or 29.774722 (29d46'29"); 'short' if a short
    decimal (<= 4 places) is a whole arcminute, e.g. .25; else None. At 6 places
    a random value lands on the arcsecond grid with p = 0.0036 per axis."""
    e = eff_dp(s)
    if e >= 6 and on_grid(s, 3600):
        return "long"
    if e <= 4 and on_grid(s, 60):
        return "short"
    return None


def record_dms(nums: list[str]) -> tuple[Optional[str], bool]:
    """(kind, one_axis): kind is 'arcmin'/'arcsec' when every axis is DMS-shaped
    and at least one is a long decimal on the grid; one_axis when some axis is a
    long on-grid decimal but the record as a whole is not DMS-shaped."""
    kinds = [axis_dms(n) for n in nums]
    if "long" not in kinds:
        return None, False
    if not all(kinds):
        return None, True
    return ("arcmin" if all(on_grid(n, 60) for n in nums) else "arcsec"), False


def geom_type(wkt: str) -> str:
    m = re.match(r"\s*(?:SRID=\d+;)?\s*([A-Za-z]+)", wkt)
    t = m.group(1).upper() if m else "?"
    return t if t in ("POINT", "MULTIPOINT", "POLYGON") else f"other:{t}"


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * math.asin(min(1.0, math.sqrt(a)))


def selfcheck():
    assert dp("45") == 0 and dp("45.10") == 2 and dp("-0.0") == 1 and dp("1.5e-3") == 4 and dp("12E2") == 0
    assert eff_dp("45.2500") == 2 and eff_dp("45.31800000000000017") == 3 and eff_dp("-71.9588888888888931") == 13
    assert float_print("868492.6492782086") and float_print("-71.9588888888888931")
    assert not float_print("28.1180500000000002") and not float_print("45.123456")
    assert xy_tokens("POINT (1.5 -2)") == [("1.5", "-2")]
    assert xy_tokens("POINT Z (1 2 3.12345)") == [("1", "2")]
    assert xy_tokens("SRID=4326;MULTIPOINT((1 2),(3.1 4))") == [("1", "2"), ("3.1", "4")]
    assert xy_tokens("POLYGON((0 0, 1 0, 1 1, 0 0))")[1] == ("1", "0")
    assert xy_tokens("POINT EMPTY") == []
    assert record_dms(["-109.1666667", "29.5"]) == ("arcmin", False)
    assert record_dms(["-109.103889", "29.774722"]) == ("arcsec", False)  # Sonora's real coordinate
    assert record_dms(["-39.25", "-4.4166666666667"]) == ("arcmin", False)
    assert record_dms(["-39.123", "-4.4166666666667"]) == (None, True)
    assert record_dms(["45.123456", "10.5"]) == (None, False)
    assert record_dms(["45.2500000000", "10.16667"]) == (None, False)  # 5 places: too short to tell
    assert abs(haversine_km(0, 0, 0, 1) - 111.195) < 0.01


# ---------------------------------------------------------------- records


class Rec(NamedTuple):
    site_id: str
    dedup_id: str
    source_id: str
    record_id: str
    name: Optional[str]
    wkt: str
    crs: str  # 'EPSG:n', or 'none' (read as EPSG:4326)
    geom: str
    prec: Optional[int]  # min written dp over x and y: the definition in the plan
    eff: Optional[int]  # min dp after dropping trailing zeros / float noise
    null_island: bool
    dms: Optional[str]  # 'arcmin' / 'arcsec'
    float_print: bool
    lat: float
    lon: float


def parse_record(ms: dict, crs_names: dict[str, str]):
    """(A1 row, Rec or None). Rec only when the record has a coordinate in its
    location view, i.e. when the merge can keep it."""
    loc = ms.get("location") or {}
    wkt = loc.get("coordinates")
    crs_uri = (loc.get("crs") or {}).get("normalized_uri")
    crs = crs_names.get(crs_uri, f"unmapped:{crs_uri}") if crs_uri else "none"
    lv = ms.get("location_view") or {}
    if wkt is None:
        return {"wkt": False, "crs": crs}, None
    nums = [n for xy in xy_tokens(wkt) for n in xy]
    dms, one_axis = record_dms(nums) if crs in ("EPSG:4326", "EPSG:4267", "none") else (None, False)
    row = {
        "wkt": True, "crs": crs, "geom": geom_type(wkt),
        "prec": min(map(dp, nums)) if nums else None,
        "eff": min(map(eff_dp, nums)) if nums else None,
        "null_island": bool(nums) and all(float(n) == 0 for n in nums),
        "dms": dms, "dms_one_axis": one_axis,
        "padded": any(dp(n) > eff_dp(n) for n in nums),
        "float_print": any(map(float_print, nums)),
        "has_latlon": lv.get("lat") is not None and lv.get("lon") is not None,
    }
    rec = None
    if row["has_latlon"]:
        rec = Rec(ms["site_id"], ms["dedup_site_id"], ms["source_id"], ms["record_id"], ms.get("name"),
                  wkt, crs, row["geom"], row["prec"], row["eff"], row["null_island"], dms,
                  row["float_print"], lv["lat"], lv["lon"])
    return row, rec


# ---------------------------------------------------------------- the fix, simulated


def pick(members: list[Rec], score: dict[str, SiteScore], *, key: Optional[Callable[[Rec], float]],
         null_island: bool, gate: Optional[Callable[[Rec, Rec], bool]] = None) -> Optional[Rec]:
    """Copy of the proposed rule over all members with a coordinate: rank by
    SiteScore (score, then suborder) as main does; if the top one is an expert or
    curator, keep it; otherwise, among system records with the top score, take the
    highest key (precision), ties in the current order. null_island drops
    POINT(0 0) first. gate(top, cand) can veto a candidate. key=None is main's
    order taken over all members at once."""
    cands = sorted((m for m in members if not (null_island and m.null_island)),
                   key=lambda m: score[m.site_id], reverse=True)
    if not cands:
        return None
    top = cands[0]
    if key is None or score[top.site_id].suborder.is_expert:
        return top
    tied = [m for m in cands if not score[m.site_id].suborder.is_expert
            and score[m.site_id].score == score[top.site_id].score
            and (gate is None or m is top or gate(top, m))]
    return max(tied, key=key)  # max keeps the first of equals: the current order


@functools.lru_cache
def km_per_unit(crs: str) -> float:
    c = CRS.from_user_input("EPSG:4326" if crs == "none" else crs)
    return KM_PER_DEGREE if c.is_geographic else c.axis_info[0].unit_conversion_factor / 1000


def ground_res_km(r: Rec) -> float:
    """What the record can actually resolve, in km: DMS values at their grid,
    others at their last real decimal place, in their CRS's unit."""
    if r.dms:
        return KM_PER_DEGREE / (60 if r.dms == "arcmin" else 3600)
    return 10 ** -(r.eff if r.eff is not None else 0) * km_per_unit(r.crs)


def by_written(r: Rec) -> float:
    return -1 if r.prec is None else r.prec


def by_ground(r: Rec) -> float:
    return -ground_res_km(r)


def consistent(top: Rec, cand: Rec) -> bool:
    """The candidate lies inside the box the top record's own digits allow
    (one unit of its last real decimal, either way, on both axes)."""
    return haversine_km(top.lat, top.lon, cand.lat, cand.lon) <= math.sqrt(2) * ground_res_km(top)


# the plan as written; with the consistency gate; and a hardened rule
VARIANTS = {
    "plan": dict(key=by_written, null_island=True),
    "plan+gate": dict(key=by_written, null_island=True, gate=consistent),
    "ground+gate": dict(key=by_ground, null_island=True, gate=consistent),
}


# ---------------------------------------------------------------- earlier rule (probe-runs/2026-09-14/v_election.py)


def v_resolution(s: str) -> float:
    """Ported verbatim from v_election.py, for a like-for-like recount."""
    d = len(s.split(".")[1]) if "." in s else 0
    v = float(s)
    if d <= 6:
        return 10.0 ** (-d)
    if abs(v * 60 - round(v * 60)) < 1e-8:
        return 1.0 / 60
    if abs(v * 3600 - round(v * 3600)) < 1e-8:
        return 1.0 / 3600
    for dd in range(0, 7):
        if abs(round(v, dd) - v) < 1e-9:
            return 10.0 ** (-dd)
    return 1e-6


def v_res(r: Rec) -> Optional[float]:
    m = re.search(r"POINT\s*\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)", r.wkt)
    return max(v_resolution(m.group(1)), v_resolution(m.group(2))) if m else None


# ---------------------------------------------------------------- main


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, math.ceil(q * len(xs)) - 1)] if xs else None


def km_stats(xs):
    return {"n": len(xs), "median": statistics.median(xs) if xs else None,
            "p95": pct(xs, 0.95), "max": max(xs, default=None), "gt_50km": sum(x > 50 for x in xs)}


def load(run: Path):
    """Pass 1 over the merged files: every record (A1) and every record with a
    coordinate (A2), each member's SiteScore, and member counts per merged site."""
    crs_names = FileEntityService(run / "data/entities").get_crs_name()
    files = sorted((run / "data/mineral-sites/merged").glob("*/*"))
    a1 = collections.Counter()
    by_source = collections.defaultdict(collections.Counter)
    recs: dict[str, Rec] = {}
    score: dict[str, SiteScore] = {}
    n_members = collections.Counter()
    for f in files:
        d = serde.json.deser(f)
        for x in d["DedupMineralSite"]:
            for r in x["ranked_sites"]:
                score[r["site_id"]] = SiteScore.from_dict(r["score"])
        for m in d["MineralSiteAndInventory"]:
            ms = m["ms"]
            n_members[ms["dedup_site_id"]] += 1
            row, rec = parse_record(ms, crs_names)
            src = by_source[ms["source_id"]]
            src["records"] += 1
            if not row["wkt"]:
                a1["no raw WKT"] += 1
                continue
            src["with WKT"] += 1
            g, c = row["geom"], row["crs"]
            p = "unparsed" if row["prec"] is None else min(row["prec"], 9)
            e = "unparsed" if row["eff"] is None else min(row["eff"], 9)
            a1[f"geom {g}"] += 1
            a1[f"crs {c}"] += 1
            a1[f"written {g} | {p}"] += 1
            a1[f"written {c} | {p}"] += 1
            a1[f"effective {c} | {e}"] += 1
            if not row["has_latlon"]:
                a1[f"WKT but no lat/lon: {row['geom']} {ms['location']['coordinates'][:40]}"] += 1
            for k in ("null_island", "dms_one_axis", "padded", "float_print"):
                if row[k]:
                    a1[k] += 1
                    src[k] += 1
            if row["dms"]:
                a1[f"dms {row['dms']}"] += 1
                src[f"dms {row['dms']}"] += 1
            if rec:
                recs[rec.site_id] = rec
    return files, crs_names, a1, by_source, recs, score, n_members


def rebuild_kept(files, targets: set[str], recs: dict[str, Rec]) -> dict[str, Optional[Rec]]:
    """Pass 2: the coordinate main keeps for each target merged site, rebuilt
    with main's own DedupMineralSite.from_dedup_sites as prep_kgrel_input does."""
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
    kept: dict[str, Optional[Rec]] = {}
    for e in targets:
        dms_lst = [DedupMineralSite.from_dict(x) for x in partials[e]]
        merged = DedupMineralSite.from_dedup_sites(
            dms_lst, [msis[r.site_id] for d in dms_lst for r in d.ranked_sites], is_site_ranked=True).dms
        kept[e] = recs[merged.coordinates.refid] if merged.coordinates is not None else None
        if kept[e] is not None:  # the merged value is the record's own location view
            assert (merged.coordinates.value.lat, merged.coordinates.value.lon) == (kept[e].lat, kept[e].lon)
    return kept


def main(run: Path, out: Path):
    selfcheck()
    out.mkdir(parents=True, exist_ok=True)
    files, crs_names, a1, by_source, recs, score, n_members = load(run)
    n_records = sum(n_members.values())
    members = collections.defaultdict(list)
    for r in recs.values():
        members[r.dedup_id].append(r)
    multi = {e for e, ms in members.items() if len(ms) >= 2}
    ni_groups = {e for e, ms in members.items() if any(m.null_island for m in ms)}
    targets = multi | ni_groups
    print(f"{n_records} records, {len(recs)} with a coordinate, {len(members)} merged sites with one, "
          f"{len(multi)} with >= 2, {len(ni_groups)} with a POINT(0 0) member", file=sys.stderr)

    kept = rebuild_kept(files, targets, recs)
    main_vs_global = sum(pick(members[e], score, key=None, null_island=False) != kept[e] for e in multi)

    # ---- A2.1/2: keeps a coarser coordinate while a member has a more precise one
    def is_4326(r):
        return r.crs in ("EPSG:4326", "none")

    coarser, cat, cat_4326, tiebreak, b_pairs = [], collections.Counter(), collections.Counter(), \
        collections.Counter(), collections.Counter()
    for e in sorted(multi):
        k = kept[e]
        better = [m for m in members[e] if m.prec is not None and k.prec is not None and m.prec > k.prec]
        if not better:
            continue
        best = max(better, key=lambda m: score[m.site_id])  # the highest-ranked more precise member
        sk, sb = score[k.site_id], score[best.site_id]
        c = ("c expert/curator kept" if sk.suborder.is_expert else
             "a tie on score" if sb.score == sk.score else
             "b kept has higher score" if sk.score > sb.score else
             "d kept has lower score")
        cat[c] += 1
        if is_4326(k) and is_4326(best):
            cat_4326[c] += 1
        if c.startswith("a"):
            tiebreak["source_id" if sk.suborder.source_id != sb.suborder.source_id else
                     "record_id" if sk.suborder.record_id != sb.suborder.record_id else "modified_at"] += 1
        if c.startswith("b"):
            b_pairs[f"{sk.score} over {sb.score} ({best.source_id})"] += 1
        coarser.append({
            "dedup_site_id": e, "category": c, "kept_site": k.site_id, "kept_source": k.source_id,
            "kept_wkt": k.wkt, "kept_crs": k.crs, "kept_prec": k.prec, "kept_score": sk.score,
            "best_site": best.site_id, "best_source": best.source_id, "best_wkt": best.wkt, "best_crs": best.crs,
            "best_prec": best.prec, "best_score": sb.score,
            "km": round(haversine_km(k.lat, k.lon, best.lat, best.lon), 3)})

    # tied top score among the coordinate members: the earlier "75.5%" metric
    tied_top, tied_by = 0, collections.Counter()
    for e in multi:
        ms = sorted(members[e], key=lambda m: score[m.site_id], reverse=True)
        s0, s1 = score[ms[0].site_id], score[ms[1].site_id]
        if s0.score == s1.score and not s0.suborder.is_expert and not s1.suborder.is_expert:
            tied_top += 1
            tied_by["source_id" if s0.suborder.source_id != s1.suborder.source_id else
                    "record_id" if s0.suborder.record_id != s1.suborder.record_id else "modified_at"] += 1

    # like-for-like with the earlier 1,269: explicit EPSG:4326 POINTs only, v_election's
    # resolution and >3x rule, elected by main's order among those members
    v_multi = v_hits = 0
    for e in multi:
        ms = [m for m in members[e] if m.crs == "EPSG:4326" and v_res(m) is not None]
        if len(ms) < 2:
            continue
        v_multi += 1
        el = pick(ms, score, key=None, null_island=False)
        if v_res(el) > 3 * min(map(v_res, ms)):
            v_hits += 1

    # ---- A2.3/4: POINT(0 0), Sonora
    ni = [r for r in recs.values() if r.null_island]
    ni_kept = [e for e in ni_groups if kept[e] is not None and kept[e].null_island]
    ni_kept_with_real = [e for e in ni_kept if any(not m.null_island for m in members[e])]
    sonora = [{"dedup_site_id": e, "kept": kept[e].site_id if kept[e] else None,
               "members": [{"site_id": m.site_id, "source_id": m.source_id, "name": m.name, "wkt": m.wkt,
                            "crs": m.crs, "dms": m.dms, "score": score[m.site_id].to_dict()} for m in members[e]]}
              for e in targets if any("SONORA LITHIUM" in (m.name or "").upper() for m in members[e])]

    # ---- A2.5/6: the fix, simulated, three ways
    proj = {n for n in crs_names.values() if not CRS.from_user_input(n).is_geographic}
    sim, all_changes = {}, {}
    for vname, kw in VARIANTS.items():
        changes, inv = [], collections.Counter()
        for e in sorted(targets):
            old, new = kept[e], pick(members[e], score, **kw)
            if new == old:
                continue
            by_ni = old is not None and old.null_island
            so, sn = (score[old.site_id] if old else None), (score[new.site_id] if new else None)
            top = pick(members[e], score, key=None, null_island=by_ni)
            # invariants: never move off an expert/curator or a higher-scored record
            if so is not None and so.suborder.is_expert:
                inv["moved off an expert/curator record"] += 1
            if top is not None and score[top.site_id].suborder.is_expert:
                inv["changed a group led by an expert/curator"] += 1
            if sn is not None and top is not None and sn.score != score[top.site_id].score:
                inv["new record's score differs from the group's top score"] += 1
            if not by_ni and so is not None and sn is not None and sn.score != so.score:
                inv["precision change between different scores"] += 1
            changes.append({
                "dedup_site_id": e, "driver": "null island" if by_ni else "precision",
                **{f"{p}_{f}": (getattr(r, f) if r else None) for p, r in (("old", old), ("new", new))
                   for f in ("site_id", "source_id", "record_id", "name", "wkt", "crs", "geom", "prec", "eff", "dms",
                             "float_print")},
                "old_score": so.score if so else None, "new_score": sn.score if sn else None,
                "old_res_km": ground_res_km(old) if old else None, "new_res_km": ground_res_km(new) if new else None,
                "km": round(haversine_km(old.lat, old.lon, new.lat, new.lon), 3) if old and new else None})
        prec = [c for c in changes if c["driver"] == "precision"]
        sim[vname] = {
            "changes": len(changes),
            "by_driver": dict(collections.Counter(c["driver"] for c in changes)),
            "null_island_to_none": sum(c["new_site_id"] is None for c in changes),
            "null_island_to_real": sum(c["driver"] == "null island" and c["new_site_id"] is not None for c in changes),
            "precision_point_moved": sum(c["km"] > 0 for c in prec),
            "precision_same_point_other_record": sum(c["km"] == 0 for c in prec),
            "precision_strictly_more_decimals_written": sum(c["new_prec"] > c["old_prec"] for c in prec),
            "precision_finer_on_the_ground": sum(c["new_res_km"] < c["old_res_km"] for c in prec),
            "precision_km": km_stats([c["km"] for c in prec]),
            "precision_same_source": sum(c["old_source_id"] == c["new_source_id"] for c in prec),
            "precision_new_wins_only_by_padding": sum(c["new_eff"] <= c["old_prec"] for c in prec),
            "precision_new_is_dms": sum(c["new_dms"] is not None for c in prec),
            "precision_new_is_float_print": sum(c["new_float_print"] for c in prec),
            "precision_crs_units_differ": sum(km_per_unit(c["old_crs"]) != km_per_unit(c["new_crs"]) for c in prec),
            "precision_involves_projected_crs": sum(c["old_crs"] in proj or c["new_crs"] in proj for c in prec),
            "precision_involves_non_point": sum(c["old_geom"] != "POINT" or c["new_geom"] != "POINT" for c in prec),
            "precision_by_source_pair": dict(collections.Counter(
                f"{c['old_source_id']} -> {c['new_source_id']}" for c in prec).most_common(12)),
            "all_gt_50km": sum(c["km"] is not None and c["km"] > 50 for c in changes),
            "invariant_violations": dict(inv),
        }
        all_changes[vname] = changes

    res = {
        "records": n_records,
        "records_with_coordinate": len(recs),
        "merged_sites_with_coordinate": len(members),
        "merged_sites_with_2plus_coordinate_members": len(multi),
        "main_kept_differs_from_global_order": main_vs_global,
        "A1": dict(sorted(a1.items())),
        "A1_by_source": {s: dict(c) for s, c in sorted(by_source.items(), key=lambda kv: -kv[1]["records"])},
        "A2_coarser_kept": len(coarser),
        "A2_coarser_kept_by_category": dict(cat.most_common()),
        "A2_coarser_kept_both_4326_by_category": dict(cat_4326.most_common()),
        "A2_tie_cases_decided_by": dict(tiebreak.most_common()),
        "A2_b_cases_kept_score_over_best_score": dict(b_pairs.most_common(10)),
        "A2_coarser_kept_separation_gt_50km": sum(c["km"] > 50 for c in coarser),
        "A2_groups_top_score_tied": tied_top,
        "A2_groups_top_score_tied_decided_by": dict(tied_by.most_common()),
        "A2_like_for_like_multi_4326_groups": v_multi,
        "A2_like_for_like_coarser_gt3x": v_hits,
        "A2_null_island_records": len(ni),
        "A2_null_island_by_source": dict(collections.Counter(r.source_id for r in ni).most_common()),
        "A2_null_island_wkt": dict(collections.Counter(r.wkt for r in ni).most_common()),
        "A2_null_island_crs": dict(collections.Counter(r.crs for r in ni).most_common()),
        "A2_null_island_merged_sites": len(ni_groups),
        "A2_null_island_kept": len(ni_kept),
        "A2_null_island_kept_with_real_member": len(ni_kept_with_real),
        "A2_sonora": sonora,
        "sim": sim,
        "projected_crs": sorted(proj),
    }
    (out / "p3_measure.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str))

    def write(name, rows):
        with open(out / name, "w", newline="", encoding="utf-8") as fh:
            if rows:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)

    write("coarser_kept.csv", coarser)
    for vname, changes in all_changes.items():
        write(f"fix_changes_{vname}.csv", changes)
    write("fix_gt_50km_plan.csv", [c for c in all_changes["plan"] if c["km"] is not None and c["km"] > 50])
    write("null_island.csv", [{**r._asdict(), "kept": kept[r.dedup_id] == r,
                               "group_has_real": any(not m.null_island for m in members[r.dedup_id])} for r in ni])
    print(json.dumps({k: v for k, v in res.items() if not k.startswith(("A1", "A2_sonora"))}, indent=2, default=str))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
