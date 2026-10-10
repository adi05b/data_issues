#!/usr/bin/env python3
"""Section 6: re-derive A, B, C and A n B from the raw WKT strings, in Python,
independently of the SPARQL FILTERs that produced them. Plus the MRDS control:
if the DMS detector cannot call MRDS ordinary decimals, nothing downstream holds.
"""
import csv, re, collections, pathlib

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-14")
rd = lambda f: list(csv.DictReader((RD / f).open()))
POINT = re.compile(r"POINT\s*\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)")
TOL = 1e-8

def axes(w):
    m = POINT.search(w)
    return (m.group(1), m.group(2)) if m else None
def dp(s):
    return len(s.split(".")[1]) if "." in s else 0
def grid(v, g):
    return abs(v * g - round(v * g)) < TOL

def dms_class(lon, lat):
    """Return 'arcminute' / 'arcsecond' / None. Coarsest grid first.
    Only meaningful when at least one axis carries >= 6 stored decimals."""
    if max(dp(lon), dp(lat)) < 6:
        return None
    a, b = float(lon), float(lat)
    if grid(a, 60) and grid(b, 60):
        return "arcminute"
    if grid(a, 3600) and grid(b, 3600):
        return "arcsecond"
    return None

# ---------- MRDS CONTROL, first ----------
ctrl = rd("v6-mrds-control.csv")
hits = collections.Counter()
eligible = 0
for r in ctrl:
    a = axes(r["wkt"])
    if not a:
        continue
    lon, lat = a
    if max(dp(lon), dp(lat)) >= 6:
        eligible += 1
        k = dms_class(lon, lat)
        if k:
            hits[k] += 1
tot_hits = sum(hits.values())
print("=== MRDS CONTROL (run before anything else) ===")
print(f"  MRDS records sampled          : {len(ctrl)}  (LIMIT 20000, ORDER BY ?site)")
print(f"  eligible (>=6 stored decimals): {eligible}")
print(f"  falsely classified as DMS     : {tot_hits}  "
      f"(arcmin {hits['arcminute']}, arcsec {hits['arcsecond']})")
print(f"  FALSE-POSITIVE RATE           : {100*tot_hits/eligible:.3f}% of eligible, "
      f"{100*tot_hits/len(ctrl):.3f}% of all sampled")
print("  PRECISION_ANALYSIS.md reported ~1.3% for MRDS.")
verdict = "PASS" if tot_hits / eligible < 0.05 else "FAIL"
print(f"  detector verdict: {verdict} - MRDS reads as ordinary decimals\n")

# ---------- A ----------
A = rd("p3.2a-popA-pull.csv")
recount = 0
for r in A:
    a = axes(r["wkt"])
    if a and min(dp(a[0]), dp(a[1])) <= 1:
        recount += 1
print("=== RE-DERIVED COUNTS (from raw WKT, not the SPARQL filter) ===")
print(f"  A  earlier 6046   re-derived {recount}   sites {len({r['site'] for r in A})}  "
      f"{'MATCH' if recount == 6046 else 'DIFFERS'}")

# ---------- B ----------
B = rd("p3.2b-dms-pull.csv")
bhit, bcls = set(), collections.Counter()
for r in B:
    a = axes(r["wkt"])
    if not a:
        continue
    k = dms_class(a[0], a[1])
    if k:
        bhit.add(r["site"]); bcls[k] += 1
print(f"  B  earlier 5287   re-derived {len(bhit)}   "
      f"(arcmin {bcls['arcminute']}, arcsec {bcls['arcsecond']})  "
      f"{'MATCH' if len(bhit) == 5287 else 'DIFFERS'}")

# ---------- C ----------
C = rd("v3-nullisland-all.csv")
csites = {r["site"] for r in C}
withcrs = {r["site"] for r in C if r["crs_label"]}
print(f"  C  earlier 36     re-derived {len(csites)}   "
      f"(with CRS {len(withcrs)}, without {len(csites)-len(withcrs)})  "
      f"{'MATCH' if len(csites) == 36 else 'DIFFERS'}")

# ---------- A n B ----------
Aset = {r["site"] for r in A if (lambda a: a and min(dp(a[0]), dp(a[1])) <= 1)(axes(r["wkt"]))}
inter = Aset & bhit
print(f"  AnB earlier 463   re-derived {len(inter)}  {'MATCH' if len(inter) == 463 else 'DIFFERS'}")
