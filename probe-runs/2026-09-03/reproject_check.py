"""Part 4: reproject Part-1 records from their DECLARED CRS to EPSG:4326 and
test against the observed state's bounding box. Also tests the foot/metre
ambiguity (EPSG:2994 vs EPSG:2993) explicitly."""
import json, glob, os
from pyproj import Transformer, CRS
from pyproj.database import query_crs_info

BOX = {  # lon_min, lon_max, lat_min, lat_max
    "Oregon": (-124.6, -116.5, 41.9, 46.3),
    "Utah":   (-114.1, -109.0, 37.0, 42.0),
}
R = os.path.dirname(os.path.abspath(__file__))
tf = {}
def to4326(epsg, x, y):
    if epsg not in tf:
        tf[epsg] = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    return tf[epsg].transform(x, y)

def load(pat):
    out = []
    for f in sorted(glob.glob(os.path.join(R, pat))):
        if f.endswith(".meta.json"): continue
        for b in json.load(open(f))["results"]["bindings"]:
            out.append({k: v["value"] for k, v in b.items()} | {"_file": os.path.basename(f)})
    return out

# --- what are 2994 / 2993 actually? -----------------------------------------
print("="*86)
print("CRS IDENTITY (from the PROJ database, not from memory)")
for code in ("2993", "2994", "26912", "4326", "4267"):
    try:
        c = CRS.from_epsg(int(code))
        unit = c.axis_info[0].unit_name if c.axis_info else "?"
        print(f"  EPSG:{code:<6} {c.name}   [axis unit: {unit}]")
    except Exception as e:
        print(f"  EPSG:{code:<6} ERROR {e}")

# --- corner records ----------------------------------------------------------
rows = load("A1.1-*.json") + load("A1.2-bucketC-full.json")
seen, recs = set(), []
for r in rows:
    if r["site"] in seen: continue
    seen.add(r["site"]); recs.append(r)

print("="*86)
print(f"REPROJECTION TEST — {len(recs)} distinct records (bbox corners + all 20 bucket-C)")
summary = {}
failures = []
for r in recs:
    lon, lat = float(r["lon"]), float(r["lat"])
    declared = r.get("crs_label", "").replace("EPSG:", "")
    state = r.get("state_obs", "?")
    box = BOX.get(state)
    # candidate CRSs: the declared one, plus the unit-variant sibling for Oregon
    cands = [declared] + (["2993"] if declared == "2994" else ["2994"] if declared == "2993" else [])
    for c in cands:
        try: X, Y = to4326(c, lon, lat)
        except Exception as e:
            summary.setdefault((r["source"], declared, c), [0,0])[1] += 1; continue
        inside = box and box[0] <= X <= box[1] and box[2] <= Y <= box[3]
        k = (r["source"], declared, c)
        summary.setdefault(k, [0,0])[0 if inside else 1] += 1
        if c == declared and not inside:
            failures.append((r.get("label","?"), r["source"], declared, r["wkt"], X, Y, state))

print(f"{'source':<34}{'declared':>9}{'tested as':>11}{'in-state':>10}{'elsewhere':>11}")
for (src, dec, c), (ok, bad) in sorted(summary.items()):
    print(f"{src.replace('https://','').replace('http://','')[:34]:<34}{'EPSG:'+dec:>9}{'EPSG:'+c:>11}{ok:>10}{bad:>11}")

if failures:
    print("\nFAILURES under the DECLARED CRS:")
    for f in failures: print("  ", f)
else:
    print("\nNo record failed under its declared CRS.")

# --- Harts Draw distance -----------------------------------------------------
print("="*86)
print("HARTS DRAW — distance between the reprojected OFR-757 point and its MRDS siblings")
hd = json.load(open(os.path.join(R, "A1.3-hartsdraw-exact.json")))["results"]["bindings"]
import re
geod = CRS.from_epsg(4326).get_geod()
utm = [b for b in hd if b["crs_label"]["value"] == "EPSG:26912"][0]
x, y = [float(v) for v in re.findall(r"[-+0-9.]+", utm["wkt"]["value"])]
PX, PY = to4326("26912", x, y)
print(f"  OFR-757 stored : {utm['wkt']['value']}  (EPSG:26912)")
print(f"  reprojected    : POINT ({PX:.7f} {PY:.7f})")
for b in hd:
    if b["crs_label"]["value"] == "EPSG:26912": continue
    mx, my = [float(v) for v in re.findall(r"[-+0-9.]+", b["wkt"]["value"])]
    _, _, d = geod.inv(PX, PY, mx, my)
    print(f"  vs {b['label']['value']:<22} {b['wkt']['value']:<50} -> {d:8.1f} m")
