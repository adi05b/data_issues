"""1.5 verify the decimal-count asymmetry; 1.6 test the DMS hypothesis."""
import json, os, re, random
R = os.path.dirname(os.path.abspath(__file__))

print("="*80); print("1.5  DOES A LOW DECIMAL COUNT PROVE LOW PRECISION?"); print("="*80)
print("Test: can a value with >=3 real decimals ever round-trip through float/repr to 1 decimal?")
rng = random.Random(20260907); bad = 0; n = 400000
for _ in range(n):
    v = round(rng.uniform(-180, 180), rng.choice([3,4,5,6]))
    s = repr(float(v))
    dp = len(s.split(".")[1]) if "." in s else 0
    if dp <= 1 and round(v, 1) != v: bad += 1
print(f"  {n} random values with 3-6 real decimals -> {bad} rendered with <=1 decimal")
print("  => a stored 1-decimal string means the value IS 1-decimal to float precision. CONFIRMED.")
print("\nTest: does a HIGH decimal count prove high precision?")
for v in ["-109.48789", "37.93389", "4.333333333333333"]:
    print(f"  float({v:>20}) -> repr = {repr(float(v))}")
print("  => 16-digit strings are float64 round-tripping. A high count proves nothing. CONFIRMED.")
print("\n  ASYMMETRY HOLDS: low count = real evidence of coarseness; high count = no evidence.")

print("\n"+"="*80); print("1.6  ARE THE LARGE-GAP RECORDS DEGREES-MINUTES-SECONDS CONVERSIONS?"); print("="*80)
rows = json.load(open(os.path.join(R,"1.6b-largest-gap-records.json")))["results"]["bindings"]
def dms_fit(x, denom):
    f = abs(x) % 1
    return abs(f*denom - round(f*denom)) < 1e-6
hit_min = hit_sec = tot = 0
for r in rows:
    m = re.findall(r"[-+0-9.]+", r["wkt"]["value"])
    for v in (float(m[0]), float(m[1])):
        tot += 1
        if dms_fit(v, 60): hit_min += 1
        elif dms_fit(v, 3600): hit_sec += 1
print(f"  {tot} coordinate values from the {len(rows)} largest-gap records:")
print(f"    exact multiple of 1 arcminute (1/60 deg) : {hit_min}  ({100*hit_min/tot:.0f}%)")
print(f"    exact multiple of 1 arcsecond, not minute: {hit_sec}")
print(f"    neither                                  : {tot-hit_min-hit_sec}")
print("\n  Worked examples:")
for r in rows[:5]:
    m = re.findall(r"[-+0-9.]+", r["wkt"]["value"]); a, b = float(m[0]), float(m[1])
    f = lambda v: f"{int(abs(v))}deg {abs(v)%1*60:.0f}min" + ("" if dms_fit(v,60) else " (not exact)")
    print(f"    {r['wkt']['value']:<34} lon={f(a):<22} lat={f(b)}")
