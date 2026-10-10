#!/usr/bin/env python3
"""Sections 5 and 6, corrected. Classification is applied in the brief's order,
with each test kept narrow; 'Other' is reported in full and then inspected."""
import csv, collections, pathlib, unicodedata, re

RD = pathlib.Path("/Users/adiitii05/Documents/Aditi/ISI_usc/data_issues/probe-runs/2026-09-14")
pop = list(csv.DictReader((RD / "p2.3-full-population.csv").open()))
vocab = list(csv.DictReader((RD / "p2.4-state-vocabulary.csv").open()))
qid2country = {r["qid"]: r["country_label"]
               for r in csv.DictReader((RD / "p2.4b-country-qid-labels.csv").open())}

def defold(s):           # case/whitespace only - diacritics PRESERVED
    return re.sub(r"\s+", " ", (s or "")).strip().lower()

def fold(s):             # case/whitespace + diacritics stripped
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()

SUFFIXES = ("department", "province", "parish", "region", "prefecture", "county")
def strip_suffix(s):
    t = fold(s)
    for suf in SUFFIXES:
        if t.endswith(" " + suf):
            return t[: -(len(suf) + 1)].strip()
    return t

STRAY = re.compile(r"[*\[\]\(\)\"`]")

# vocabulary indexes
by_label   = collections.defaultdict(set)   # folded label      -> {country qid}
by_strip   = collections.defaultdict(set)   # suffix-stripped   -> {country qid}
for v in vocab:
    by_label[fold(v["label"])].add(v["country"])
    by_strip[strip_suffix(v["label"])].add(v["country"])

classified, other_strings, rows_out = collections.Counter(), collections.Counter(), []
examples = collections.defaultdict(list)

for r in pop:
    obs, matched = r.get("state_obs") or "", r.get("state_label") or ""
    if not obs:
        cls = "No observed name"
    elif defold(obs) == defold(matched):
        cls = "Homonym"
    elif fold(obs) == fold(matched):
        cls = "Accent"
    elif strip_suffix(obs) == strip_suffix(matched):
        cls = "Suffix"
    elif len(obs.strip()) == 2:
        cls = "Two-letter code"
    elif STRAY.search(obs):
        cls = "Stray punctuation"
    elif fold(obs) not in by_label and strip_suffix(obs) not in by_strip:
        cls = "Not in the list"
    else:
        cls = "Other"
        other_strings[obs] += 1
    classified[cls] += 1
    if len(examples[cls]) < 4:
        examples[cls].append((obs, matched, r.get("country_label"), r.get("state_country")))
    rows_out.append({**r, "_class": cls})

print(f"=== SECTION 5 — all {len(pop)} rows ===")
for k, v in classified.most_common():
    print(f"   {v:>6}  {100*v/len(pop):>5.2f}%  {k}")

print("\n=== examples ===")
for k, _ in classified.most_common():
    print(f"\n{k}:")
    for o, m, c, sc in examples[k]:
        print(f"    obs={o!r:<32} matched={m!r:<28} record-country={c!r} state-country={sc!r}")

print(f"\n=== EVERY distinct 'Other' string — {len(other_strings)} distinct, "
      f"{sum(other_strings.values())} rows ===")
# does a correct target exist under the record's OWN country?
fixable = 0
for s, n in other_strings.most_common():
    ex = next(r for r in pop if (r.get("state_obs") or "") == s)
    own = ex.get("country_label")
    owners = by_label.get(fold(s), set()) | by_strip.get(strip_suffix(s), set())
    owner_labels = {qid2country.get(q, q) for q in owners}
    hit = own in owner_labels
    if hit:
        fixable += n
    print(f"   {n:>4}  {s!r:<34} -> {ex.get('state_label')!r:<26} "
          f"[{own} -> {ex.get('state_country')}]  correct-target-exists-under-own-country={hit}")
print(f"\nOther rows where the right entry exists under the record's own country: "
      f"{fixable} / {sum(other_strings.values())}")

with (RD / "p2.5-classified.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys()))
    w.writeheader(); w.writerows(rows_out)

# ---------- SECTION 6 ----------
print("\n\n=== SECTION 6 — damage by country ===")
totals = {r["country_label"]: int(r["sites"])
          for r in csv.DictReader((RD / "p2.6-country-totals.csv").open()) if r["country_label"]}
affected = collections.Counter()
for r in pop:
    if r.get("country_label"):
        affected[r["country_label"]] += 1

ranked = []
for c, tot in totals.items():
    a = affected.get(c, 0)
    ranked.append((a / tot if tot else 0, a, tot, c))
ranked.sort(reverse=True)
print(f"{'share':>8} {'affected':>9} {'total':>8}  country")
for sh, a, tot, c in ranked:
    if a:
        print(f"{100*sh:>7.2f}% {a:>9} {tot:>8}  {c}")
zero = [c for sh, a, tot, c in ranked if a == 0]
print(f"\ncountries with ZERO affected records: {len(zero)} of {len(totals)}")
print("   " + ", ".join(sorted(zero)))
