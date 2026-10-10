"""Part 3 - quantify the error in Adriana's model for DMS-derived records."""
import json, os, collections
R = os.path.dirname(os.path.abspath(__file__))

# Adriana's table, from the three anchors quoted in the brief:
#   0 dp -> +/-70.3 km, 1 dp -> +/-7.0 km, 2 dp -> +/-702.5 m
# => base 70.25 km at a 1-degree grid, divided by 10 per decimal place.
# She caps at 5 dp (her own note: >=6 dp behaves like 5 dp).
BASE_KM = 70.25
CAP = 5
def her_km(dp): return BASE_KM / (10 ** min(dp, CAP))
# True precision on the SAME scale: a grid of g degrees -> BASE_KM * g
TRUE = {"arcminute": BASE_KM / 60.0, "arcsecond": BASE_KM / 3600.0}
FUSEMINE_KM = 10.0   # blocking radius from 03_coordinate_precision.md

rows = json.load(open(os.path.join(R, "P3-dms-dp-distribution.json")))["results"]["bindings"]
MRDS = "https://mrdata.usgs.gov/mrds"
# sources whose DMS rate is far above the control false-positive baseline (see P2 table)
GENUINE = {"vms","carbonatite","podchrome","laterite","sedznpb","sedau","porcu","sedcu","ree","major-deposits"}
def genuine(s): return s.rsplit("/",1)[-1] in GENUINE

def analyse(keep, title):
    over = collections.Counter(); under = collections.Counter()
    exact = 0; n = 0; rescued = 0
    worst_over = worst_under = None
    per_axis = collections.Counter()
    for r in rows:
        s = r["source"]["value"]
        if not keep(s): continue
        c = int(r["sites"]["value"]); grid = r["grid"]["value"]
        lond, latd = int(r["lond"]["value"]), int(r["latd"]["value"])
        t = TRUE[grid]; n += c
        for dp in (lond, latd):
            h = her_km(dp); ratio = h / t
            per_axis[dp] += c
            if ratio > 1.05:
                b = ">=100x" if ratio>=100 else ">=50x" if ratio>=50 else ">=10x" if ratio>=10 else ">=2x" if ratio>=2 else "1-2x"
                over[b] += c
                if worst_over is None or ratio > worst_over[0]: worst_over=(ratio,dp,grid,h,t)
            elif ratio < 0.95:
                inv = 1/ratio
                b = ">=100x" if inv>=100 else ">=50x" if inv>=50 else ">=10x" if inv>=10 else ">=2x" if inv>=2 else "1-2x"
                under[b] += c
                if worst_under is None or inv > worst_under[0]: worst_under=(inv,dp,grid,h,t)
            else: exact += c
        # category change: her model rules the pair out (coarser axis > FuseMine radius) but truth does not
        if her_km(min(lond,latd)) > FUSEMINE_KM and t <= FUSEMINE_KM: rescued += c
    print("="*84); print(title); print("="*84)
    print("DMS-derived records: %d   (axes assessed: %d)"%(n, 2*n))
    print("\nOVERSTATED by her model (she thinks it is worse than it is):")
    for b in [">=100x",">=50x",">=10x",">=2x","1-2x"]:
        if over[b]: print("   %-8s %7d axes"%(b,over[b]))
    print("   total overstated: %d axes"%sum(over.values()))
    print("\nUNDERSTATED (DANGEROUS - treated as more accurate than it is):")
    for b in [">=100x",">=50x",">=10x",">=2x","1-2x"]:
        if under[b]: print("   %-8s %7d axes"%(b,under[b]))
    print("   total understated: %d axes"%sum(under.values()))
    print("   about right (within 5%%): %d axes"%exact)
    if worst_over: print("\n   worst overstatement : %.0fx  (%d dp on an %s pair: her %.1f km vs true %.3f km)"%worst_over)
    if worst_under: print("   worst understatement: %.0fx  (%d dp on an %s pair: her %.4f km vs true %.3f km)"%worst_under)
    print("\nCATEGORY CHANGE (her model rules the site out at the %.0f km FuseMine radius,"%FUSEMINE_KM)
    print("                 but it is actually precise enough to use):  %d records"%rescued)
    return n, rescued

analyse(lambda s: genuine(s), "GENUINE DMS SOURCES (10 USGS deposit databases, control-validated)")
print()
analyse(lambda s: s != MRDS, "ALL SOURCES EXCEPT MRDS (upper bound - includes some baseline false positives)")
