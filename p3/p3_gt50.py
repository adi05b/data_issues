"""Classify the plan's > 50 km moves (out/fix_gt_50km_plan.csv) and print them as a
Markdown table for P3_MEASURE.md. Run after p3_measure.py; plain python3 is enough.

  sign flip     the two points match within 1.5 deg on |lat| and |lon| but a sign differs
  same source   old and new come from the same source_id (sibling records)
"""
import csv
import re
import sys
from pathlib import Path

out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")


def xy(wkt):
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", re.sub(r"^\s*SRID=\d+;", "", wkt))
    return float(nums[0]), float(nums[1])


def short(src):
    return src.rstrip("/").split("/")[-1].replace("documents", "inferlink")[:16]


rows = sorted(csv.DictReader(open(out / "fix_gt_50km_plan.csv")), key=lambda r: -float(r["km"]))
flags_count = {}
print("| km | why | dedup site | kept (source, dp, WKT) | would keep (source, dp, WKT) |")
print("|---:|---|---|---|---|")
for r in rows:
    flags = []
    if r["driver"] == "null island":
        flags.append("null island")
    elif r["old_crs"] in ("EPSG:4326", "EPSG:4267", "none") and r["new_crs"] in ("EPSG:4326", "EPSG:4267", "none"):
        (x1, y1), (x2, y2) = xy(r["old_wkt"]), xy(r["new_wkt"])
        if abs(abs(x1) - abs(x2)) < 1.5 and abs(abs(y1) - abs(y2)) < 1.5 and (x1 * x2 < 0 or y1 * y2 < 0):
            flags.append("sign flip")
    if r["new_source_id"] and r["old_source_id"] == r["new_source_id"]:
        flags.append("same source")
    if r["new_dms"]:
        flags.append("new is DMS")
    if r["new_float_print"] == "True":
        flags.append("new is float print")
    for f in flags or ["-"]:
        flags_count[f] = flags_count.get(f, 0) + 1
    site = r["dedup_site_id"].replace("dedup_site__", "")
    site = site[:40] + "…" if len(site) > 40 else site
    print(f"| {float(r['km']):,.0f} | {', '.join(flags) or '-'} | `{site}` | {short(r['old_source_id'])}, {r['old_prec']}, "
          f"`{r['old_wkt'][:44]}` | {short(r['new_source_id'])}, {r['new_prec']}, `{r['new_wkt'][:44]}` |")
print()
print(f"{len(rows)} rows; flags: {flags_count}")
