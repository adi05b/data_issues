#!/usr/bin/env python3
"""Section 1/2 rates, and section 7 cross-check against Adriana's export."""
import csv, collections, pathlib
import pandas as pd

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-14")
rd = lambda f: list(csv.DictReader((RD / f).open()))

aff   = {r["source"]: int(r["affected"]) for r in rd("p2.1a-affected-by-source.csv")}
tot   = {r["source"]: int(r["total"])    for r in rd("p2.1b-source-totals.csv")}
sxm   = rd("p2.2a-source-x-matcher.csv")
den   = rd("p2.2b-matcher-denominator.csv")
pop   = rd("p2.3-full-population.csv")

print("=== SECTION 1 — by VOLUME ===")
for s, a in sorted(aff.items(), key=lambda kv: -kv[1]):
    print(f"   {a:>6} / {tot[s]:>6}  {100*a/tot[s]:>6.2f}%  {s}")

print("\n=== SECTION 1 — by RATE ===")
for s, a in sorted(aff.items(), key=lambda kv: -(kv[1] / tot[kv[0]])):
    print(f"   {100*a/tot[s]:>6.2f}%  {a:>6} / {tot[s]:>6}  {s}")

print("\n=== SECTION 2 — matcher rates (conflicts / all state candidates) ===")
mden = collections.Counter()
for r in den:
    mden[r["matcher"]] += int(r["candidates"])
maff = collections.Counter()
for r in sxm:
    maff[r["matcher"]] += int(r["affected"])
print(f"{'matcher':<36} {'conflicts':>10} {'candidates':>11} {'rate':>8}")
for m in sorted(mden, key=lambda m: -(maff.get(m, 0) / mden[m] if mden[m] else 0)):
    a, d = maff.get(m, 0), mden[m]
    print(f"{m:<36} {a:>10} {d:>11} {100*a/d:>7.2f}%")

# dominant matcher + sample record ids per source, for the headline table
print("\n=== headline table inputs ===")
dom = {}
for r in sxm:
    s = r["source"]
    if s not in dom or int(r["affected"]) > dom[s][1]:
        dom[s] = (r["matcher"], int(r["affected"]))
bysrc = collections.defaultdict(list)
for r in pop:
    bysrc[r["source"]].append(r)
for s, a in sorted(aff.items(), key=lambda kv: -kv[1]):
    rows = bysrc[s]
    tags = collections.Counter(x["site"].split("__")[-1] for x in rows)
    ids = [x.get("record_id") or x["site"].split("__")[2] for x in rows[:3]]
    print(f"{s}\n    tag={dict(tags)}  dom={dom[s][0]}  ids={ids}")

# ---------- SECTION 7 ----------
print("\n\n=== SECTION 7 — cross-check vs Adriana's export ===")
x = pd.ExcelFile("/Users/adiitii05/Downloads/state_country_disagreements.xlsx")
print("sheets:", x.sheet_names)
df = x.parse(x.sheet_names[0])
print("shape:", df.shape)
print("columns:", list(df.columns))
print(df.head(6).to_string())
