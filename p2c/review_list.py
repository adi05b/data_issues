#!/usr/bin/env python3
"""P2_REVIEW_LIST.csv: every merged entity still emptied in run D (rerun/reports/p2e),
with C's geometry suggestion and name check from emptied_313.csv.

Changes from emptied_313.csv: the recorded country is run D's merged country; BVI and
Cayman are now Option A; a Katanga entity's note says why run D could not fill it.

    python review_list.py      (any python 3)
"""

import collections
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENT = HERE / "rerun/data/fork/data/entities"
cname = {c["minmod_id"]: c["name"] for c in csv.DictReader(open(ENT / "country.csv", encoding="utf-8"))}
c313 = {r["entity_id"]: r for r in csv.DictReader(open(HERE / "emptied_313.csv", encoding="utf-8"))}
outcomes = json.load(open(HERE / "rerun/reports/p2e/merged_outcomes_D.json", encoding="utf-8"))
emptied = sorted(e for e, v in outcomes.items() if v["outcome"]["D"] == "state emptied")
assert len(emptied) == 221 and set(emptied) <= set(c313)

katanga = collections.defaultdict(list)
for k in json.load(open(HERE / "rerun/reports/p2e/records.json", encoding="utf-8"))["katanga_left_empty"]:
    katanga[k["entity"]].append(k["reason"])
NEW_OPTION_A = {("British Virgin Islands", "United Kingdom"), ("Cayman Islands", "United Kingdom")}

rows = []
for e in emptied:
    r = c313[e]
    country = " | ".join(cname[c] for c in outcomes[e]["D"]["country"]["value"])
    group, note = r["reason_group"], r["reason_note"]
    if (r["observed_state"], r["recorded_country"]) in NEW_OPTION_A:
        group, note = "Option A", country
    if group == "Katanga":
        assert katanga[e], e
        note = " | ".join(sorted(set(katanga[e])))
    rows.append({"entity_id": e, "recorded_country": country, "observed_state": r["observed_state"],
                 "reason_group": group, "reason_note": note, "c_outcome": r["c_outcome"],
                 "c_containing_shape": r["containing_shape"], "c_would_fill_with": r["would_fill_with"],
                 "name_check": r["name_check"]})
rows.sort(key=lambda x: (x["reason_group"], x["recorded_country"], x["observed_state"], x["entity_id"]))

out = HERE.parent / "P2_REVIEW_LIST.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(out, len(rows))
print(dict(collections.Counter(r["reason_group"] for r in rows).most_common()))
print("Katanga:", dict(collections.Counter(r["reason_note"] for r in rows if r["reason_group"] == "Katanga")))
print("C suggestion:", dict(collections.Counter(r["c_outcome"] for r in rows).most_common()))
print("fillable by name_check:", dict(collections.Counter(r["name_check"] for r in rows if r["c_outcome"] == "fillable")))
