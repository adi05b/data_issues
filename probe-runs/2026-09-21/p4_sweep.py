#!/usr/bin/env python3
"""Section 3 sweep + the CSV-derived parts of pre-flight, S1, S2 and S5."""
import csv, os, pathlib, collections, statistics, json
SP = pathlib.Path(__file__).parent
os.environ.setdefault("PROJ_USER_WRITABLE_DIRECTORY", str(SP / "projdata"))
import pyproj
from pyproj import CRS, Geod, Transformer

CSVF = pathlib.Path("/Users/adiitii05/Downloads/nad27_stored_as_wgs84 - nad27_stored_as_wgs84.csv")
rows = list(csv.DictReader(CSVF.open()))
GEOD = Geod(ellps="WGS84")

print("=" * 74); print("PRE-FLIGHT / S1 fields, from the real CSV (her extract - grain: raw record)")
print("=" * 74)
for f in ["crs_observed_name", "crs_qid", "crs_epsg", "crs_asserted_by", "crs_confidence",
          "source", "source_id", "state", "country", "passes_wgs84_range_check", "fix_decision"]:
    c = collections.Counter(r[f] for r in rows)
    shown = ", ".join(f"{k!r}x{v}" for k, v in c.most_common(3))
    print(f"  {f:<28} {len(c):>2} distinct | {shown}")

print("\n" + "=" * 74); print("SECTION 2 - merged-entity roll-up (from her dedup_site_id column)")
print("=" * 74)
ded = collections.Counter(r["dedup_site_id"] for r in rows)
print(f"  raw records                 : {len(rows)}")
print(f"  distinct dedup_site_id      : {len(ded)}")
print(f"  entities holding >1 NAD27 rec: {sum(1 for v in ded.values() if v > 1)}")
print(f"  largest entity              : {ded.most_common(1)[0][1]} records")
taken = collections.Counter(r["entity_coord_taken_from_this_record"] for r in rows)
print(f"  entity_coord_taken_from_this_record: {dict(taken)}")
print("  NOTE: this is HER column, at HER grain. The dedup REST API is unreachable,")
print("        so it is not independently verified. Tagged as her figure.")

print("\n" + "=" * 74); print("SECTION 3 - which geographic CRSs silently no-op without always_xy")
print("=" * 74)
# corpus CRSs (archive 2026-09-03) + every candidate the brief names
CORPUS = {"EPSG:4326": 403550, "EPSG:2994": 23316, "EPSG:26912": 7792, "EPSG:4267": 7720}
CANDIDATES = ["EPSG:4326", "EPSG:2994", "EPSG:26912", "EPSG:4267",
              "EPSG:4269", "EPSG:4322", "EPSG:4019", "EPSG:4030", "EPSG:4267",
              "EPSG:4268", "EPSG:4270", "EPSG:4272", "EPSG:4301", "EPSG:4302"]
seen = []
print(f"{'CRS':<11}{'in corpus':>10}  {'geog':<5}{'axis0':<10}{'no-op?':<8}{'median shift':>13}  area of use")
for code in dict.fromkeys(CANDIDATES):
    try:
        c = CRS.from_user_input(code)
    except Exception as e:
        print(f"{code:<11}{'-':>10}  ERROR {e}"); continue
    geog = c.is_geographic
    ax0 = c.axis_info[0].direction if c.axis_info else "?"
    aou = c.area_of_use.bounds if c.area_of_use else None
    n = CORPUS.get(code, 0)
    if not geog or code == "EPSG:4326":
        noop, med = ("n/a - projected" if not geog else "n/a - is target"), None
    else:
        # probe the CRS's own area of use: without always_xy pyproj reads arg1 as lat
        t_bug = Transformer.from_crs(code, 4326)
        t_fix = Transformer.from_crs(code, 4326, always_xy=True)
        lo0, la0, lo1, la1 = aou
        pts = [((lo0 + lo1) / 2, (la0 + la1) / 2), (lo0 + 0.25 * (lo1 - lo0), la0 + 0.25 * (la1 - la0)),
               (lo0 + 0.75 * (lo1 - lo0), la0 + 0.75 * (la1 - la0))]
        noops, shifts = 0, []
        for lon, lat in pts:
            bx, by = t_bug.transform(lon, lat)      # as geo.py is written today
            fx, fy = t_fix.transform(lon, lat)
            if (bx, by) == (lon, lat):
                noops += 1
            _, _, d = GEOD.inv(lon, lat, fx, fy)
            shifts.append(d)
        noop = f"YES {noops}/3" if noops else "no"
        med = statistics.median(shifts)
    seen.append((code, n, geog, noop, med))
    print(f"{code:<11}{n if n else '-':>10}  {str(geog):<5}{ax0:<10}{str(noop):<8}"
          f"{(f'{med:.1f} m' if med is not None else '-'):>13}  {aou}")

print("\n  Corpus CRSs only (what actually matters):")
for code, n, geog, noop, med in seen:
    if n:
        print(f"    {code:<11} {n:>7} nodes  geographic={geog}  silently no-ops={noop}")

print("\n" + "=" * 74); print("SECTION 5 - her convergence claim, as recorded in HER file (not rebuilt)")
print("=" * 74)
sib = [r for r in rows if r.get("sibling_dist_before_m")]
print(f"  rows carrying a non-NAD27 sibling: {len(sib)}")
if sib:
    b = [float(r["sibling_dist_before_m"]) for r in sib]
    a = [float(r["sibling_dist_after_m"]) for r in sib]
    print(f"  median distance before : {statistics.median(b):.1f} m")
    print(f"  median distance after  : {statistics.median(a):.1f} m")
    print(f"  within 50 m before     : {100*sum(1 for x in b if x<=50)/len(b):.1f} %")
    print(f"  within 50 m after      : {100*sum(1 for x in a if x<=50)/len(a):.1f} %")
    imp = sum(1 for x, y in zip(b, a) if y < x)
    print(f"  pairs that improve     : {imp} / {len(sib)} ({100*imp/len(sib):.1f} %)")
    worse = [(r, float(r['sibling_dist_before_m']), float(r['sibling_dist_after_m']))
             for r in sib if float(r['sibling_dist_after_m']) > float(r['sibling_dist_before_m'])]
    print(f"  pairs that get WORSE   : {len(worse)}")
    bysrc = collections.Counter(r["sibling_source"] for r, _, _ in worse)
    for k, v in bysrc.most_common(8):
        print(f"      {v:>4}  {k}")
    flag = collections.Counter(r["sibling_agreement_improved"] for r in sib)
    print(f"  her own improved flag  : {dict(flag)}")
