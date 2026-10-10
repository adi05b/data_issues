#!/usr/bin/env python3
"""Populations A / B / C: reconcile, classify B offline, team tags, by-country."""
import csv, re, collections, pathlib

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-14")
rd = lambda f: list(csv.DictReader((RD / f).open()))
POINT = re.compile(r"POINT\s*\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)")
TOL = 1e-8

def axes(wkt):
    m = POINT.search(wkt)
    return (m.group(1), m.group(2)) if m else None

def dp(s):
    return len(s.split(".")[1]) if "." in s else 0

def grid(v, g):
    return abs(v * g - round(v * g)) < TOL

# ---------- A ----------
A = rd("p3.2a-popA-pull.csv")
A1 = {r["source"]: int(r["affected"]) for r in rd("p3.1a-popA-by-source.csv")}
print("=== POPULATION A reconciliation ===")
print(f"  rows pulled      : {len(A)}")
print(f"  distinct sites   : {len({r['site'] for r in A})}")
print(f"  section 1 sum    : {sum(A1.values())}")
per = collections.defaultdict(set)
for r in A: per[r["source"]].add(r["site"])
print(f"  per-source match : {all(len(per[s]) == n for s, n in A1.items())}")
print("  team tags        :", dict(collections.Counter(r["site"].split("__")[-1] for r in A).most_common()))

# ---------- B, classified offline ----------
Bsrc = rd("p3.2b-dms-pull.csv")
print(f"\n=== POPULATION B — {len(Bsrc)} records from the ten candidate sources ===")
bcls = collections.Counter()
bysrc = collections.defaultdict(collections.Counter)
Brecords = []
for r in Bsrc:
    a = axes(r["wkt"])
    if not a:
        continue
    lon, lat = a
    # the test discriminates only on long values; vacuous on short ones
    if max(dp(lon), dp(lat)) < 6:
        bcls["short (test vacuous)"] += 1
        bysrc[r["source"]]["short"] += 1
        continue
    vlon, vlat = float(lon), float(lat)
    if grid(vlon, 60) and grid(vlat, 60):          # coarsest grid first
        k = "arcminute"
    elif grid(vlon, 3600) and grid(vlat, 3600):
        k = "arcsecond"
    else:
        k = "not DMS"
    bcls[k] += 1
    bysrc[r["source"]][k] += 1
    if k in ("arcminute", "arcsecond"):
        Brecords.append({**r, "grid": k})
for k, v in bcls.most_common():
    print(f"   {v:>6}  {k}")
print(f"\n   POPULATION B (arcminute + arcsecond) = {len(Brecords)}")
print(f"\n{'source':<44}{'arcmin':>8}{'arcsec':>8}{'notDMS':>8}{'short':>7}{'B rate':>9}")
tot4326 = {r["source"]: int(r["total_4326"]) for r in rd("p3.1t-source-totals-4326.csv")}
for s, c in sorted(bysrc.items(), key=lambda kv: -(kv[1]["arcminute"] + kv[1]["arcsecond"])):
    b = c["arcminute"] + c["arcsecond"]
    t = tot4326.get(s, 0)
    print(f"{s.split('//')[-1]:<44}{c['arcminute']:>8}{c['arcsecond']:>8}{c['not DMS']:>8}{c['short']:>7}"
          f"{(100*b/t if t else 0):>8.2f}%")
print("  team tags:", dict(collections.Counter(r["site"].split("__")[-1] for r in Brecords).most_common()))

# overlap A n B
Aset, Bset = {r["site"] for r in A}, {r["site"] for r in Brecords}
print(f"\n  A n B overlap: {len(Aset & Bset)} records are in BOTH A and B")

with (RD / "p3.2b-popB-classified.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(Brecords[0].keys()))
    w.writeheader(); w.writerows(Brecords)

# ---------- 3: by country ----------
print("\n=== SECTION 3 — by country (EPSG:4326 denominators) ===")
ctot = {r["country_label"]: int(r["sites"]) for r in rd("p3.3-country-totals-4326.csv") if r["country_label"]}
ca = collections.Counter(r["country_label"] for r in A if r.get("country_label"))
MIN = 20
big = sorted(((ca.get(c, 0) / t, ca.get(c, 0), t, c) for c, t in ctot.items() if t >= MIN and ca.get(c, 0)),
             reverse=True)
small = sorted(((ca.get(c, 0) / t, ca.get(c, 0), t, c) for c, t in ctot.items() if t < MIN and ca.get(c, 0)),
               reverse=True)
print(f"\n-- A, countries with >= {MIN} sites --")
print(f"{'share':>8}{'aff':>7}{'total':>8}  country")
for sh, a, t, c in big[:28]:
    print(f"{100*sh:>7.2f}%{a:>7}{t:>8}  {c}")
print(f"\n-- below the {MIN}-site floor (reported separately, not ranked with the rest) --")
for sh, a, t, c in small:
    print(f"{100*sh:>7.2f}%{a:>7}{t:>8}  {c}")
zero = [c for c, t in ctot.items() if not ca.get(c, 0) and t >= MIN]
print(f"\ncountries with >= {MIN} sites and ZERO coarse records: {len(zero)} of "
      f"{sum(1 for t in ctot.values() if t >= MIN)}")
print("   " + ", ".join(sorted(zero)[:45]))
