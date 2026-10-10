#!/usr/bin/env python3
"""Section 2: hand-judge every below-0.90 commodity match and size the threshold.

Verdict per (observed -> label) pair. WRONG = the mapping is factually incorrect.
GOOD  = the mapping is correct, just scored low by the string metric.
PART  = defensible but lossy (a specific term flattened to its parent).
"""
import csv, collections, pathlib

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-21")
rows = list(csv.DictReader((RD / "p5-s2d-below90.csv").open()))

WRONG = {
 ("Construction","Strontium"), ("Construc","Cobalt"), ("Halite","Alunite"),
 ("Salt","Aluminum"), ("Water","Slate"), ("Metal","Nonmetal"),
 ("Emery","Gemstone > Emerald"), ("Industrial","Indium"), ("Monazite","Magnesite"),
 ("Soda Ash","Ash"), ("Galena","Gallium"), ("Tripoli","Lithium"),
 ("Tourmaline","Staurolite"), ("Halloysite","Alunite"), ("Vesuvianite","Kyanite"),
 ("Hematite","Diatomite"), ("Gilsonite","Wollastonite"), ("Chalcopyrite","Clay > Chlorite"),
 ("Bornite","Granite"), ("Magnetite","Magnesite"), ("Chlorite","Chlorine"),
 ("Anthophyllite","Pyrophyllite"), ("Clay (Halloysite)","Clay > Chlorite"),
 ("Sillimanite","Silica"), ("Iron Oxide Pigments","Iron > Pig Iron"),
 ("Volcanic Materials","Clay > Bloating Material"),
}
PART = {
 ("Sodium Carbonate","Sodium"), ("Sodium Sulfate","Sodium > Salt"),
 ("Columbite-Tantalite","Tantalum"), ("Beryl","Beryllium"), ("Sandstone","Stone"),
 ("Magnesium Compounds","Magnesium"), ("Molybdenite","Molybdenum"),
 ("Aggregate","Aggregate > Light Weight"),
}

def verdict(obs, lab):
    if not lab:
        return "UNMATCHED"
    k = (obs, lab)
    if k in WRONG: return "WRONG"
    if k in PART:  return "PART"
    return "GOOD"

for r in rows:
    r["conf"] = float(r["conf"]); r["n"] = int(r["records"])
    r["v"] = verdict(r["obs"], r["label"])

tot = sum(r["n"] for r in rows)
print(f"below-0.90 rows: {len(rows)}   records (raw grain): {tot}\n")
agg = collections.Counter()
for r in rows: agg[r["v"]] += r["n"]
for k, v in agg.most_common():
    print(f"  {k:<10} {v:>7} records  ({100*v/tot:.1f}%)")

print("\n=== threshold trade-off (commodity, raw-record grain) ===")
print(f"{'floor':>7} {'records cut':>12} {'WRONG fixed':>12} {'GOOD lost':>11} {'PART lost':>11} {'ratio':>9}")
for t in (0.55, 0.60, 0.62, 0.65, 0.70, 0.72, 0.75, 0.80, 0.85, 0.90):
    cut = [r for r in rows if r["conf"] < t]
    w = sum(r["n"] for r in cut if r["v"] == "WRONG")
    g = sum(r["n"] for r in cut if r["v"] == "GOOD")
    p = sum(r["n"] for r in cut if r["v"] == "PART")
    ratio = f"{w/g:.1f}:1" if g else "inf"
    print(f"{t:>7.2f} {w+g+p:>12} {w:>12} {g:>11} {p:>11} {ratio:>9}")

print("\n=== what a 0.90 floor would destroy (GOOD matches, by volume) ===")
for r in sorted([r for r in rows if r["v"] == "GOOD"], key=lambda r: -r["n"])[:14]:
    print(f"  {r['n']:>6} @ {r['conf']:.4f}  {r['obs'][:30]:<32}-> {r['label']}")

print("\n=== WRONG matches that NO floor below 0.90 catches (conf >= 0.72) ===")
for r in sorted([r for r in rows if r["v"] == "WRONG" and r["conf"] >= 0.72], key=lambda r: -r["n"]):
    print(f"  {r['n']:>6} @ {r['conf']:.4f}  {r['obs'][:30]:<32}-> {r['label']}")

print("\n=== the 0.72 line, both sides ===")
lo = [r for r in rows if r["conf"] < 0.72]
hi = [r for r in rows if r["conf"] >= 0.72]
for nm, s in (("below 0.72", lo), ("0.72-0.90", hi)):
    c = collections.Counter()
    for r in s: c[r["v"]] += r["n"]
    print(f"  {nm:<11} " + "  ".join(f"{k}={v}" for k, v in c.most_common()))
