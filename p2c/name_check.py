#!/usr/bin/env python3
"""Hand judgment of every non-Katanga "fillable" row: does the state the point
would fill agree with the observed state name? Adds a `name_check` column to
emptied_313.csv and dropped_338.csv and writes name_check_results.json.

  agrees       the filled ADM1 contains (or is) the place the name means
  contradicts  the name means a place outside the filled ADM1
  unclear      the observed name cannot be read reliably
  n/a          Katanga: the name is the pre-2015 province, every successor agrees

Judged from the observed name, the reports' notes and general geography; one
judgment per (observed name, filled state). Katanga is not judged per row.
"""

import collections
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
A, C, U = "agrees", "contradicts", "unclear"
J = {
    ("Territory Of Christmas Island", "Q2213 Western Australia"): C,
    ("Territory Of New Caledonia And Dependencies", "Q3235 Auvergne-Rhône-Alpes"): C,
    ("Alto Alentejo", "Q5269 Portalegre"): A,
    ("Cleveland", "Q6679 England"): A,
    ("Eastern Finland", "Q3212 North Karelia"): A,
    ("Irian Jaya", "Q3691 Papua"): A,
    ("Lapland", "Q6047 Norrbotten County"): A,
    ("Limousin", "Q3312 Nouvelle-Aquitaine"): A,
    ("Oriente", "Q2890 Granma Province"): A,
    ("Ostfold", "Q5009 Vestfold og Telemark"): C,  # Østfold is east of the Oslofjord, in Viken
    ("Oulu Laani", "Q3209 Kainuu"): A,
    ("Oulu Laani", "Q3213 Northern Ostrobothnia"): A,
    ("Semipalatinsk", "Q3976 East Kazakhstan Region"): A,
    ("Sidamo", "Q3182 Oromia Region"): A,  # the old province spanned today's Sidama and southern Oromia
    ("Sogn Og Fjordane", "Q5007 Troms og Finnmark"): C,  # western Norway vs the far north
    ("Troms", "Q5007 Troms og Finnmark"): A,
    ("Welega [Walaga]", "Q3182 Oromia Region"): A,
    ("Agadir", "Q4720 Souss-Massa"): A,
    ("Agadir", "Q4655 Béni Mellal-Khénifra"): C,
    ("Oulu", "Q3213 Northern Ostrobothnia"): A,
    ("Turku", "Q3208 Finland Proper"): A,
    ("Buller", "Q4842 West Coast Region"): A,
    ("Copiapó", "Q2732 Atacama"): A,
    ("Elko County", "Q6876 Nevada"): A,
    ("Guarayos", "Q2457 Santa Cruz Department"): A,
    ("Humboldt County", "Q6876 Nevada"): A,  # Humboldt County, Nevada (there is also one in California)
    ("Mirab Gojam", "Q3178 Benishangul-Gumuz Region"): C,  # West Gojjam is a zone of Amhara
    ("Mirab Harerge", "Q3183 Somali Region"): C,  # West Hararghe is a zone of Oromia
    ("Muhanga", "Q5501 Western Province"): C,  # Muhanga district is in Southern Province
    ("Nye", "Q6876 Nevada"): A,
    ("Vila Nova De Cerveira | Caminha", "Q5273 Viana do Castelo"): A,
    ("Vila Nova De Cerveira", "Q5273 Viana do Castelo"): A,
    ("Westland", "Q4842 West Coast Region"): A,
    ("York County", "Q2656 New Brunswick"): A,
    ("Kuril Islands", "Q5476 Sakhalin"): A,
    ("Rapu-Rapu Island", "Q5156 Bicol"): A,
    ("Samar", "Q5184 Eastern Visayas"): A,
    ("Timor Island", "Q3690 Nusa Tenggara Timur"): A,
    ("Viti Levu Island", "Q3189 Central Division"): A,
    # rejected on coordinates in the alias pass: the point already disagreed with the name
    ("Al Balqa'", "Q3960 Aqaba"): C,
    ("Al Buhayrah", "Q3101 Aswan"): C,
    ("Chitinskaya Oblast'", "Q5416 Amur Oblast"): C,
    ("Hwanghae-Namdo", "Q4906 North Hamgyong Province"): C,
    ("Pulau Pinang", "Q4393 Sabah"): C,
    ("BN", "Q4531 Baja California"): U,
    ("BS", "Q4532 Baja California Sur"): U,
    ("CO", "Q4537 Coahuila de Zaragoza"): U,
    ("SB", "Q4532 Baja California Sur"): U,
    ("SI", "Q4554 Sinaloa"): U,
    ("Chicha", "Q5127 Ica"): U,
    ("Eastern Slovakia", "Q5643 Banská Bystrica Region"): C,  # eastern Slovakia is Košice and Prešov
    ("G�vleborg", "Q6040 Gävleborg County"): A,
    ("Sofiya", "Q2528 Plovdiv Province"): C,
    ("Sofiya", "Q2525 Pazardzhik Province"): C,
    ("Sofiya", "Q2536 Sofia Province"): A,
    ("Southeast Alaska", "Q6840 Alaska"): A,
    ("Surigao", "Q5168 Caraga"): A,
    ("Surigao*", "Q5168 Caraga"): A,
    ("Bayern [Bavaria, Germany]", "Q2931 Jihočeský kraj"): C,  # Bavaria is in Germany
    ("Piura", "Q2502 Piauí"): U,  # Piura is in Peru; the points are in Piauí, Brazil: a misspelling of Piauí, or a wrong point
}


def main():
    res = {}
    for name, idcol in (("dropped_338.csv", "record_id"), ("emptied_313.csv", "entity_id")):
        rows = list(csv.DictReader(open(HERE / name, newline="", encoding="utf-8")))
        missing = set()
        for r in rows:
            if r["c_outcome"] != "fillable":
                r["name_check"] = ""
            elif r["reason_group"] == "Katanga":
                r["name_check"] = "n/a"
            else:
                k = (r["observed_state"], r["would_fill_with"])
                if k not in J:
                    missing.add(k)
                r["name_check"] = J.get(k, "NOT JUDGED")
        assert not missing, missing
        with open(HERE / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        fill = [r for r in rows if r["c_outcome"] == "fillable"]
        res[name] = {
            "fillable": len(fill),
            "name_check": dict(collections.Counter(r["name_check"] for r in fill)),
            "by_reason": {g: dict(collections.Counter(r["name_check"] for r in fill if r["reason_group"] == g))
                          for g in sorted({r["reason_group"] for r in fill})},
        }
    (HERE / "name_check_results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
