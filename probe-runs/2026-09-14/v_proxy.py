#!/usr/bin/env python3
"""Section 2: test the owl:sameAs proxy against the real dedup table via the REST API.

For twenty of the corrected groups:
  - do the elected and best records land in the SAME dedup entity?
  - does the dedup entity's member list match the sameAs component?
  - is the dedup entity's coordinate the one the simulation predicted?
"""
import csv, json, subprocess, pathlib, random, re, time

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-14")
API = "https://minmod.isi.edu/api/v1"
PREFIX = "https://minmod.isi.edu/resource/"
rows = list(csv.DictReader((RD / "v1-election-corrected.csv").open()))

# rebuild sameAs components so we can compare membership
pairs = list(csv.DictReader((RD / "v1b-coord-pairs-full.csv").open()))
parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
for p in pairs:
    a, b = find(p["s"]), find(p["o"])
    if a != b: parent[a] = b
comp = {}
for u in list(parent):
    comp.setdefault(find(u), set()).add(u)

def get(url):
    r = subprocess.run(["curl", "-sS", "-m", "40", url], capture_output=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return None

random.seed(7)
sample = random.sample(rows, 20)
results = []
for i, r in enumerate(sample, 1):
    el_id = r["elected_uri"].replace(PREFIX, "")
    bs_id = r["best_uri"].replace(PREFIX, "")
    el = get(f"{API}/mineral-sites/{el_id}")
    bs = get(f"{API}/mineral-sites/{bs_id}")
    time.sleep(0.3)
    if not el or not bs:
        results.append({"n": i, "status": "API fetch failed"}); continue
    el_ded = el.get("dedup_site_uri", "")
    bs_ded = bs.get("dedup_site_uri", "")
    same_group = el_ded == bs_ded and el_ded != ""
    ded_id = el_ded.rsplit("/", 1)[-1] if el_ded else ""
    ded = get(f"{API}/dedup-mineral-sites/{ded_id}") if ded_id else None
    time.sleep(0.3)
    members, ded_coord = set(), None
    if isinstance(ded, dict):
        for key in ("sites", "site_ids", "mineral_sites"):
            if key in ded and isinstance(ded[key], list):
                for s in ded[key]:
                    sid = s if isinstance(s, str) else (s.get("id") or s.get("uri") or "")
                    members.add(sid.rsplit("/", 1)[-1])
        loc = ded.get("location") or {}
        if isinstance(loc, dict):
            ded_coord = loc.get("lat"), loc.get("lon")
        if ded_coord in (None, (None, None)):
            for k in ("coordinates", "centroid"):
                if k in ded: ded_coord = ded[k]
    sa = {u.replace(PREFIX, "") for u in comp.get(find(r["elected_uri"]), set())}
    results.append({
        "n": i, "status": "ok", "dedup": ded_id, "same_group": same_group,
        "sameAs_members": len(sa), "api_members": len(members),
        "members_match": bool(members) and members == sa,
        "members_subset": bool(members) and sa.issubset(members),
        "ded_coord": ded_coord,
        "pred_elected_wkt": r["elected_wkt"], "best_wkt": r["best_wkt"],
        "el_ded": el_ded, "bs_ded": bs_ded,
    })

print(f"{'#':>3} {'same dedup?':<12}{'sameAs n':>9}{'API n':>7}{'match':>7}{'subset':>8}  dedup coord")
for x in results:
    if x["status"] != "ok":
        print(f"{x['n']:>3} {x['status']}"); continue
    print(f"{x['n']:>3} {str(x['same_group']):<12}{x['sameAs_members']:>9}{x['api_members']:>7}"
          f"{str(x['members_match']):>7}{str(x['members_subset']):>8}  {x['ded_coord']}")

ok = [x for x in results if x["status"] == "ok"]
print(f"\nboth records in the SAME dedup entity : {sum(1 for x in ok if x['same_group'])} / {len(ok)}")
print(f"member lists identical                : {sum(1 for x in ok if x['members_match'])} / {len(ok)}")
print(f"sameAs component is a SUBSET of dedup : {sum(1 for x in ok if x['members_subset'])} / {len(ok)}")

P = re.compile(r"POINT\s*\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)")
def xy(w):
    m = P.search(w or "")
    return (float(m.group(1)), float(m.group(2))) if m else None
match_pred = match_best = 0
print("\n--- predicted elected vs what the dedup entity actually holds ---")
for x in ok:
    dc = x["ded_coord"]
    if not (isinstance(dc, tuple) and dc[0] is not None):
        continue
    lat, lon = float(dc[0]), float(dc[1])
    pe, bw = xy(x["pred_elected_wkt"]), xy(x["best_wkt"])
    hit_pred = pe and abs(lon - pe[0]) < 1e-6 and abs(lat - pe[1]) < 1e-6
    hit_best = bw and abs(lon - bw[0]) < 1e-6 and abs(lat - bw[1]) < 1e-6
    match_pred += bool(hit_pred); match_best += bool(hit_best)
    print(f"  #{x['n']:<3} dedup=({lon:.6f},{lat:.6f})  predicted={pe}  best={bw}  "
          f"{'PREDICTED' if hit_pred else ('BEST' if hit_best else 'NEITHER')}")
print(f"\ndedup coordinate == simulation's predicted elected : {match_pred} / {len(ok)}")
print(f"dedup coordinate == the better one                 : {match_best} / {len(ok)}")

json.dump(results, (RD / "v2-proxy-check.json").open("w"), indent=1, default=str)
print("\nwrote v2-proxy-check.json")
