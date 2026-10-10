#!/usr/bin/env python3
"""Section 7: independent cross-check. Her file is a comparison, never a source."""
import csv, collections, pathlib
import pandas as pd

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-14")
PREFIX = "https://minmod.isi.edu/resource/"
pop = list(csv.DictReader((RD / "p2.3-full-population.csv").open()))
mine = {r["site"].replace(PREFIX, "") for r in pop}

df = pd.read_excel("/Users/adiitii05/Downloads/state_country_disagreements.xlsx")
hers_rows = len(df)
hers_refids = set(df["source_refid"].dropna().astype(str))
hers_dedup = set(df["dedup_site_id"].dropna().astype(str))

print(f"her rows (merged entities)   : {hers_rows}")
print(f"her distinct dedup_site_id   : {len(hers_dedup)}")
print(f"her distinct source_refid    : {len(hers_refids)}")
print(f"my distinct sites (records)  : {len(mine)}")
print(f"ratio my/hers (by refid)     : {len(mine)/len(hers_refids):.3f}")

both = mine & hers_refids
only_mine = mine - hers_refids
only_hers = hers_refids - mine
print(f"\nin BOTH                      : {len(both)}")
print(f"only mine (she missed)       : {len(only_mine)}")
print(f"only hers (my query missed)  : {len(only_hers)}")

if only_hers:
    print("\n*** RECORDS SHE FOUND THAT MY QUERY MISSES — my query may be wrong ***")
    sub = df[df["source_refid"].astype(str).isin(list(only_hers))]
    print(f"    {len(sub)} rows, {len(only_hers)} distinct refids")
    print(sub[["source_refid", "source_observed_name", "entity_country",
               "state_assigned", "state_belongs_to", "source_id"]].head(25).to_string())
    print("\n    by source_id:")
    for k, v in sub["source_id"].value_counts().items():
        print(f"      {v:>5}  {k}")

if only_mine:
    print("\n--- records I found that she did not (her check's gap) ---")
    sub = [r for r in pop if r["site"].replace(PREFIX, "") in only_mine]
    print(f"    {len(sub)} rows, {len(only_mine)} distinct sites")
    print("    by source_id:")
    for k, v in collections.Counter(r["source"] for r in sub).most_common():
        print(f"      {v:>5}  {k}")
    print("    by team tag:")
    for k, v in collections.Counter(r["site"].split("__")[-1] for r in sub).most_common():
        print(f"      {v:>5}  {k}")
    print("    sample observed-state strings:")
    for k, v in collections.Counter((r.get("state_obs") or "(none)") for r in sub).most_common(12):
        print(f"      {v:>5}  {k!r}")

# named-case comparison
print("\n=== named cases: hers vs mine ===")
hers_case = collections.Counter(
    (str(a), str(b)) for a, b in zip(df["source_observed_name"], df["state_assigned"]))
mine_case = collections.Counter(
    ((r.get("state_obs") or ""), (r.get("state_label") or "")) for r in pop)
print(f"{'observed -> assigned':<48} {'hers':>6} {'mine':>6} {'ratio':>7}")
for (o, m), hn in hers_case.most_common(15):
    mn = mine_case.get((o, m), 0)
    ratio = f"{mn/hn:.2f}" if hn else "-"
    print(f"{f'{o!r} -> {m!r}':<48} {hn:>6} {mn:>6} {ratio:>7}")
