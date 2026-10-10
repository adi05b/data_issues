#!/usr/bin/env python3
import csv, collections, pathlib
SHEET = pathlib.Path("/Users/adiitii05/Downloads/coord_out_of_range - coord_out_of_range.csv")
rows = list(csv.DictReader(SHEET.open()))

# raw-grain totals from earlier probe snapshots (2026-09-02 1b.csv / P0.8)
RAW_OUT = {"http://www.oregongeology.org": 23316,
           "https://doi.org/10.34191/OFR-757": 7792,
           "https://doi.org/10.5382/econgeo.4950": 1}
RAW_TOTAL = {"http://www.oregongeology.org": 23316,
             "https://doi.org/10.34191/OFR-757": 7793,
             "https://doi.org/10.5382/econgeo.4950": 628}

per = collections.defaultdict(list)
for r in rows:
    per[r["source_id"]].append(r)

def recid(refid):
    p = refid.split("__")
    return p[2] if len(p) > 2 else "?"

print(f"{'source':<40} {'merged':>7} {'raw_out':>8} {'raw_tot':>8} {'%src_out':>9}  samples")
for src, v in sorted(per.items(), key=lambda kv: -len(kv[1])):
    ids = sorted({recid(r["refid"]) for r in v})
    pct = 100.0 * RAW_OUT[src] / RAW_TOTAL[src]
    print(f"{src:<40} {len(v):>7} {RAW_OUT[src]:>8} {RAW_TOTAL[src]:>8} {pct:>8.2f}%  "
          f"{', '.join(ids[:4])}")

print("\n=== dedup compression (raw out-of-range -> merged rows) ===")
for src, v in per.items():
    print(f"{src}: {RAW_OUT[src]} raw -> {len(v)} merged  "
          f"({100.0*len(v)/RAW_OUT[src]:.1f}%)")

print("\n=== named sample records per source (for the lookup table) ===")
for src, v in sorted(per.items(), key=lambda kv: -len(kv[1])):
    named = [r for r in v if r["name_val"] not in ("Unknown", "")][:5]
    print(f"\n{src}")
    for r in named:
        print(f"    record_id={recid(r['refid']):<16} {r['name_val'][:34]:<34} "
              f"stored_lat={float(r['stored_lat']):>11.5f} stored_lon={float(r['stored_lon']):>10.5f}")
