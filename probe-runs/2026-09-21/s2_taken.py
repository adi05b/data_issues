#!/usr/bin/env python3
"""Does the merged entity publish the NAD27 coordinate? Sampled from the API."""
import json, subprocess, pathlib, random, collections, time

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-21")
API = "https://minmod.isi.edu/api/v1"
sites = json.load((RD / "q2-site-to-dedup.json").open())

ents = collections.defaultdict(list)
for sid, v in sites.items():
    ents[v["dedup_site_uri"]].append((sid, v.get("coordinates")))

random.seed(11)
sample = random.sample(sorted(ents), 250)
took_nad, took_other, no_coord, failed = 0, 0, 0, 0
others = []
for i, u in enumerate(sample, 1):
    did = u.rsplit("/", 1)[-1]
    p = subprocess.run(["curl", "-sS", "-m", "60", f"{API}/dedup-mineral-sites/{did}"],
                       capture_output=True)
    try:
        d = json.loads(p.stdout)
    except Exception:
        failed += 1; continue
    loc = d.get("location") or {}
    elat, elon = loc.get("lat"), loc.get("lon")
    if elat is None:
        no_coord += 1; continue
    members = ents[u]
    hit = any(c and abs(c["lat"] - elat) < 1e-7 and abs(c["lon"] - elon) < 1e-7
              for _, c in members)
    if hit:
        took_nad += 1
    else:
        took_other += 1
        others.append((did, (elon, elat), [(s.split("__")[2], c) for s, c in members][:2],
                       len(d.get("sites", []))))
    if i % 50 == 0:
        print(f"  {i}/{len(sample)}", end="\r", flush=True)
print()
n = took_nad + took_other
print(f"sampled entities            : {len(sample)}  (fetch failed {failed}, no coord {no_coord})")
print(f"entity publishes a NAD27 coord : {took_nad} / {n}  ({100*took_nad/n:.1f}%)")
print(f"entity took a NON-NAD27 coord  : {took_other} / {n}  ({100*took_other/n:.1f}%)")
print(f"\n  extrapolated to 7,218 entities: ~{round(7218*took_nad/n)} take NAD27, "
      f"~{round(7218*took_other/n)} do not   (CSV said 7,140 / 78)")
print("\n  entities that took a non-NAD27 coordinate:")
for did, ec, mem, nsites in others[:12]:
    print(f"    {did[:46]:<46} entity=({ec[0]:.5f},{ec[1]:.5f}) members={nsites} nad27={mem}")
json.dump({"sampled": len(sample), "took_nad27": took_nad, "took_other": took_other,
           "failed": failed, "no_coord": no_coord,
           "others": [o[0] for o in others]},
          (RD / "q2-coord-election-sample.json").open("w"), indent=1)
