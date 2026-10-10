#!/usr/bin/env python3
"""Section 2: confirm the merged-entity roll-up from the dedup API, not the CSV."""
import csv, json, subprocess, pathlib, collections, time, sys

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-21")
API = "https://minmod.isi.edu/api/v1"
# site ids come from the GRAPH census, not the CSV
sites = sorted({r["nad"].rsplit("/", 1)[-1]
                for r in csv.DictReader((RD / "q3-nad27-siblings.csv").open())})
# that file only has the 297 with siblings; get the full 7,720 from the graph pull
FULL = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/"
                    "probe-runs/2026-09-14/n2-nad27-coords-all.csv")
sites = sorted({r["site"].rsplit("/", 1)[-1] for r in csv.DictReader(FULL.open())})
print(f"NAD27 site ids (from the 2026-09-14 graph pull): {len(sites)}")

def post(path, body, tries=3):
    for a in range(tries):
        p = subprocess.run(["curl", "-sS", "-m", "120", "-X", "POST", f"{API}{path}",
                            "-H", "Content-Type: application/json", "-d", json.dumps(body)],
                           capture_output=True)
        try:
            return json.loads(p.stdout)
        except Exception:
            time.sleep(2)
    return None

out, B = {}, 400
for i in range(0, len(sites), B):
    chunk = sites[i:i + B]
    d = post("/mineral-sites/find_by_ids", {"ids": chunk})
    if not isinstance(d, dict):
        print(f"  batch {i} FAILED", file=sys.stderr); continue
    out.update(d)
    print(f"  {len(out):>5}/{len(sites)}", end="\r", flush=True)
print()

json.dump({k: {"dedup_site_uri": v.get("dedup_site_uri"),
               "source_id": v.get("source_id"),
               "coordinates": v.get("coordinates")}
           for k, v in out.items()}, (RD / "q2-site-to-dedup.json").open("w"), indent=1)

print(f"sites resolved            : {len(out)}")
ded = collections.Counter(v.get("dedup_site_uri") for v in out.values())
print(f"DISTINCT dedup entities   : {len(ded)}      (CSV said 7,218)")
print(f"entities with >1 NAD27 rec: {sum(1 for n in ded.values() if n > 1)}")
print(f"largest entity            : {max(ded.values())} NAD27 records")

# does the merged entity expose a CRS in any form?
sample = [u for u in ded if u][:10]
print("\n=== 10 merged entities: does the dedup record expose a CRS? ===")
crs_found = 0
for u in sample:
    did = u.rsplit("/", 1)[-1]
    p = subprocess.run(["curl", "-sS", "-m", "60", f"{API}/dedup-mineral-sites/{did}"],
                       capture_output=True)
    try:
        d = json.loads(p.stdout)
    except Exception:
        print(f"  {did[:52]}  <fetch failed>"); continue
    keys = sorted(d.keys())
    hits = [k for k in keys if "crs" in k.lower() or "datum" in k.lower()
            or "srid" in k.lower() or "epsg" in k.lower()]
    blob = json.dumps(d).lower()
    deep = [t for t in ("epsg", "4267", "crs", "datum") if t in blob]
    if hits or deep:
        crs_found += 1
    print(f"  {did[:50]:<50} top-level CRS keys={hits or 'NONE'}  substrings={deep or 'none'}")
    if u == sample[0]:
        print(f"     full key list: {keys}")
        loc = d.get("location_info") or d.get("location") or {}
        print(f"     location payload: {json.dumps(loc)[:200]}")
json.dump({"entities": len(ded), "crs_exposed_in": crs_found},
          (RD / "q2-dedup-crs-check.json").open("w"), indent=1)
print(f"\nmerged entities exposing a CRS: {crs_found} / {len(sample)}")
