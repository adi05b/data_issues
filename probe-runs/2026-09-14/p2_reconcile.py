#!/usr/bin/env python3
"""Reconcile the section-3 pull against section 1 BEFORE any classification."""
import csv, collections, pathlib

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-14")

pop = list(csv.DictReader((RD / "p2.3-full-population.csv").open()))
by_src = list(csv.DictReader((RD / "p2.1a-affected-by-source.csv").open()))

print("=== RECONCILIATION (must pass before classifying) ===")
print(f"section 3 rows retrieved     : {len(pop)}")
sites = {r["site"] for r in pop}
print(f"section 3 DISTINCT sites     : {len(sites)}")
s1 = sum(int(r["affected"]) for r in by_src)
print(f"section 1 sum of ?affected   : {s1}")
print(f"match                        : {len(sites) == s1}")

# where does the row>site excess come from?
dupes = collections.Counter(r["site"] for r in pop)
multi = {k: v for k, v in dupes.items() if v > 1}
print(f"\nsites appearing on >1 row    : {len(multi)}  (excess rows = {len(pop)-len(sites)})")
for k, v in list(multi.items())[:10]:
    rows = [r for r in pop if r["site"] == k]
    varying = [f for f in rows[0] if len({r[f] for r in rows}) > 1]
    print(f"   {v}x {k.split('/')[-1][:60]}  varies on: {varying}")

# per-source distinct-site counts must match section 1 source by source
print("\n=== per-source reconciliation ===")
p3 = collections.defaultdict(set)
for r in pop:
    p3[r["source"]].add(r["site"])
ok = True
for r in sorted(by_src, key=lambda r: -int(r["affected"])):
    got, want = len(p3.get(r["source"], ())), int(r["affected"])
    flag = "OK" if got == want else "*** MISMATCH ***"
    if got != want:
        ok = False
    print(f"   {want:>6} vs {got:>6}  {flag}  {r['source']}")
print(f"\nALL SOURCES RECONCILE: {ok}")

# team tags
print("\n=== team tags (from site URI) ===")
tags = collections.Counter(r["site"].split("__")[-1] for r in pop if "__" in r["site"])
for k, v in tags.most_common():
    print(f"   {v:>6}  {k}")
tags_d = collections.Counter(s.split("__")[-1] for s in sites if "__" in s)
print("   (distinct-site basis):", dict(tags_d))

# vocabulary size
vocab = list(csv.DictReader((RD / "p2.4-state-vocabulary.csv").open()))
print(f"\n=== vocabulary ===")
print(f"rows                 : {len(vocab)}")
print(f"distinct entities    : {len({v['ent'] for v in vocab})}")
print(f"distinct labels      : {len({v['label'] for v in vocab})}")
withc = [v for v in vocab if v.get('country')]
print(f"rows with :country   : {len(withc)}")
ents_multi = collections.Counter(v['ent'] for v in vocab)
print(f"entities on >1 row   : {sum(1 for c in ents_multi.values() if c>1)}")
