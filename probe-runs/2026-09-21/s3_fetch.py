#!/usr/bin/env python3
"""Fetch every dedup entity that holds a NAD27 record, with its member list."""
import json, subprocess, pathlib, collections
from concurrent.futures import ThreadPoolExecutor

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-21")
API = "https://minmod.isi.edu/api/v1"
sites = json.load((RD / "q2-site-to-dedup.json").open())
ents = sorted({v["dedup_site_uri"] for v in sites.values()})
print(f"entities to fetch: {len(ents)}", flush=True)

def get(u):
    did = u.rsplit("/", 1)[-1]
    for _ in range(3):
        p = subprocess.run(["curl", "-sS", "-m", "90", f"{API}/dedup-mineral-sites/{did}"],
                           capture_output=True)
        try:
            d = json.loads(p.stdout)
            return did, {"location": d.get("location"),
                         "sites": [s.get("id") if isinstance(s, dict) else s
                                   for s in (d.get("sites") or [])],
                         "n": len(d.get("sites") or [])}
        except Exception:
            continue
    return did, None

out, done = {}, 0
with ThreadPoolExecutor(max_workers=12) as ex:
    for did, d in ex.map(get, ents):
        out[did] = d
        done += 1
        if done % 250 == 0:
            print(f"  {done}/{len(ents)}", flush=True)
ok = sum(1 for v in out.values() if v)
print(f"fetched {ok}/{len(out)}")
json.dump(out, (RD / "q3-dedup-members.json").open("w"))
print("wrote q3-dedup-members.json")
