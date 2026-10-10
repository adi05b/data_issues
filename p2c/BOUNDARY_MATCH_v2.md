# Problem 2, Solution C: boundary matching, v2

*Aditi Bombe · 2026-10-09 · read-only. No live graph or API was queried. No repository was edited.*

*`BOUNDARY_MATCH.md` (v1) is kept as written. This file adds the coverage of the 313 and the 338, the full-resolution Katanga run and the licences, then corrects v1's claims (section 4).*

## How the 313 and the 338 were reproduced

The P2 reports kept only counts, and the Phase 5 work directories no longer exist. So I rebuilt everything in `p2c/rerun/` from the same inputs:

**Code: `usc-isi-i2/ta2-minmod-kg`.**
- `83f9b7b` for run base.
- `a888391` for runs A and B, from `origin/fix/p2-state-repair`.
- `cbac0a9` for run C. That commit is not on GitHub, so I applied `minmod_data_issues/patches/0005-problem-2-dependency-mapping.patch` to `a888391`. All three changed files hash to the patch's target blobs (`c132c91`, `cdfde1b`, `32f71ea`).

**Data: `ta2-minmod-data`.**
- `3a086a5` for base and A, cloned from the local `data-p2`.
- `adi05b/ta2-minmod-data@add-niamey-ekaterinburg` = `250abc7` for B and C. Its tree is `399763a7`, the tree `P2_PHASE5.md` cites.

**Scripts.**
- `p2d_measure.py` and `p2d_merged.py` were copied into `p2c/rerun/scripts/` with the helpers they import (`p2_records.py`, `p2c_drop_list.py`, `p2c_alias_candidates.py`, `p2d_run_merge.py`, `p2_etl.yml`, `reference/state_repair.py`).
- Each copy was changed only to **also write ids**: `dropped_after.jsonl` and `merged_outcomes.json`.
- `p2d_measure.py` also sets the `fork` start method, because the original ran on Linux and macOS's default `spawn` re-runs the module.
- Python is `minmod_data_issues/.venv-p2`, with each run's own code on `PYTHONPATH`.

**The counts reproduce exactly before any id is used:**

| | report | rerun |
|---|--:|--:|
| `records.json`: every field | — | identical |
| dropped after: candidates / records | 340 / 338 | **340 / 338** |
| ↳ blocked / no suggestion | 198 / 142 | **198 / 142** |
| `merged.json`: every field | — | identical |
| conflicted in base | 5,856 | **5,856** |
| run C: repointed / **emptied** | 5,543 / 313 | **5,543 / 313** |
| entities rebuilt | 5,936 | **5,936** |

All **313 emptied entities have at least one member among the 338 dropped records.** 10 have more than one; the first one by rank is used for the location.

## 1. Coverage: what C could fill

**Method.** For each record or entity, in order:
1. **Usable point:** CRS EPSG:4326 or unset; a POINT, or a MULTIPOINT whose points all fall in one shape; not 0,0; not a round placeholder (both coordinates on a whole or half degree).
2. **gbOpen ADM1** exists for the recorded country. For the 313 that is the merged entity's country in run C, which after Option A is the dependency.
3. **Point-in-shape** on the **full-resolution** shape (section 2).
4. **Mapping:** the shape maps to **exactly one** MinMod state through a single (not ambiguous) match in `state_shape_match.csv`.

**Reason groups.** The reports have no column with these groups; they come from the reports' own per-group notes (`p2c_alias_candidates.py`):
- **Option A:** the four implemented pairs.
- **Katanga:** the observed name is Katanga or Katanga Province.
- **Greenland:** recorded country Greenland.
- **Wrong recorded country:** the note starts with that phrase.
- **City / island / abolished unit / county:** keywords in the note. County covers counties, districts, municipalities, zones and sub-provinces.
- **Other:** everything else, including the 5 blocked Albania/Guinea groups and the 6 aliases rejected on coordinates.

**Name check.** "Fillable" only means the geometry gives one state. Every non-Katanga fill was hand-judged against the observed name (`name_check.py`): **agrees**, **contradicts** or **unclear**. Katanga is not judged per record, because every successor province agrees with "Katanga".

### Outcomes

| outcome | 338 dropped records | % | 313 emptied entities | % |
|---|--:|--:|--:|--:|
| **fillable** | **191** | 56.5% | **173** | 55.3% |
| ↳ Katanga (successor province) | 98 | | 94 | |
| ↳ name agrees | 59 | | 49 | |
| ↳ **name contradicts** | **25** | | **22** | |
| ↳ name unclear | 9 | | 8 | |
| point in an ambiguous shape | 16 | 4.7% | 16 | 5.1% |
| point in a shape with no MinMod match | 7 | 2.1% | 17 | 5.4% |
| point outside the recorded country | 96 | 28.4% | 26 | 8.3% |
| no ADM1 for country | 0 | — | 55 | 17.6% |
| no usable point | 28 | 8.3% | 26 | 8.3% |
| **total** | **338** | | **313** | |

**Fillable with a fill I would accept (Katanga plus "agrees"): 157 of 338 records (46.4%) and 143 of 313 entities (45.7%).**

- **Ambiguous (16):** the 16 are all Kukës, Korçë, Kankan, Kindia and Boké. MinMod has a County *and* a District row (Albania) or a Prefecture *and* a Region row (Guinea) for the same shape. These are exactly the blocked groups.
- **No MinMod match:** Greenland's gB shapes (MinMod has no Greenland rows), Macedonia-Thrace, Andalucía, Wallonia/Brussels (MinMod has finer units), Australia's "Other Territories", and Jämtlands län (unmatched in Step 1 because `län` is not folded).
- **No usable point:** records = no location 19, round placeholder 8, 0,0 1. Entities = 18, 7, 1.
- **No multipoint** spans more than one shape.

### By reason group: 338 dropped records

| reason | records | fillable (agrees / contradicts / unclear) | ambiguous | no match | outside country | no ADM1 | no point |
|---|--:|---|--:|--:|--:|--:|--:|
| Katanga | 111 | 98 (successor) | | | 4 | | 9 |
| Option A | 72 | 2 (0 / 2 / 0) | | 1 | 69 | | |
| other | 57 | 26 (8 / 12 / 6) | 16 | 4 | 5 | | 6 |
| abolished unit | 33 | 27 (21 / 6 / 0) | | 2 | 3 | | 1 |
| county | 24 | 17 (14 / 3 / 0) | | | 3 | | 4 |
| wrong recorded country | 16 | 4 (0 / 1 / 3) | | | 9 | | 3 |
| island | 14 | 12 (12 / 0 / 0) | | | 1 | | 1 |
| city | 7 | 5 (4 / 1 / 0) | | | | | 2 |
| Greenland | 4 | | | | 2 | | 2 |

### By reason group: 313 emptied entities

| reason | entities | fillable (agrees / contradicts / unclear) | ambiguous | no match | outside country | no ADM1 | no point |
|---|--:|---|--:|--:|--:|--:|--:|
| Katanga | 107 | 94 (successor) | | | 4 | | 9 |
| Option A | 70 | 0 | | 11 | 4 | 55 | |
| other | 53 | 24 (7 / 11 / 6) | 16 | 4 | 4 | | 5 |
| abolished unit | 31 | 25 (19 / 6 / 0) | | 2 | 3 | | 1 |
| county | 14 | 11 (8 / 3 / 0) | | | | | 3 |
| wrong recorded country | 14 | 3 (0 / 1 / 2) | | | 8 | | 3 |
| island | 14 | 12 (12 / 0 / 0) | | | 1 | | 1 |
| city | 6 | 4 (3 / 1 / 0) | | | | | 2 |
| Greenland | 4 | | | | 2 | | 2 |

**The 25 contradicting fills (records):**
- **9 are the aliases already rejected on coordinates**, which come back as fills (Pulau Pinang → Sabah ×5, Al Balqa' → Aqaba, Al Buhayrah → Aswan, Chitinskaya → Amur, Hwanghae-Namdo → North Hamgyong).
- Sogn og Fjordane → Troms og Finnmark ×5.
- Østfold → Vestfold og Telemark.
- Mirab Gojam → Benishangul-Gumuz.
- Mirab Harerge → Somali.
- Muhanga → Western Province (Muhanga is in Southern).
- Agadir → Béni Mellal-Khénifra.
- Eastern Slovakia → Banská Bystrica.
- Sofiya → Plovdiv and → Pazardzhik.
- Bavaria (recorded Czech Republic) → Jihočeský kraj.
- The two Option A fills.

**Unclear (9):** Mexico's BN/BS/CO/SB/SI codes, Chicha (Peru), and Piura recorded under Brazil with points in Piauí, which is either a misspelling of Piauí or a wrong point.

### Option A, explicitly

| dependency | as dropped records (recorded country = sovereign) | as emptied entities (country = dependency, after Option A) |
|---|---|---|
| **New Caledonia** | 49 records under France. 48 lie outside France's gB ADM1, which is the 13 metropolitan regions. 1 lands in Auvergne-Rhône-Alpes, so its point is wrong. | 48 entities. **gbOpen has no ADM1 for New Caledonia**, so C cannot fill. |
| **Greenland** | 15 records under Denmark. All 15 lie outside Denmark. | 15 entities. gbOpen has Greenland shapes: 11 points fall in Sermersooq 5, Kujalleq 3, Avannaata 2 and NE Greenland NP 1. **MinMod has no Greenland rows**, so nothing to fill. 4 points are outside Greenland's shapes. |
| **Christmas Island** | 5 records under Australia. 3 outside, 1 → Western Australia (contradicts), 1 → gB "Other Territories" (no MinMod match). | 4 entities. **No gbOpen ADM1.** |
| **Montserrat** | 3 records under the UK. All outside the UK. | 3 entities. **No gbOpen ADM1.** |

**C fills none of the 70 Option A entities.** Filling them needs MinMod rows for New Caledonia's provinces and Greenland's municipalities, plus a shape source other than gbOpen for New Caledonia, Christmas Island and Montserrat.

## 2. Katanga with full-resolution shapes

DR Congo's full-resolution file has 194,049 vertices against 42,116 in the simplified one, 4.6× more. **No Katanga point changes province.**

| | Haut-Katanga | Lualaba | Tanganyika | Haut-Lomami | outside DR Congo | no location | placeholder |
|---|--:|--:|--:|--:|--:|--:|--:|
| 111 drop-list records | 50 | 43 | 4 | 1 | 4 | 8 | 1 |
| 148 never normalized | 77 | 71 | | | | | |
| 2 already Haut-Katanga | | 1 | | | | 1 | |

- **Distance to the boundary:** 9 of the 247 in-province points lie within 1 km of a provincial boundary, and 32 within 5 km. The closest is 0.1 km (`katanga_boundary_distance.txt`). They stay on the same side in both files, but they are the ones to watch if the boundaries are ever revised.
- **The 4 points outside DR Congo** are unchanged and flagged, not fixed: one longitude-sign flip and three latitude-sign flips, 585–4,280 km from DR Congo.
- **The 98 inside match the 98 Katanga fills in section 1**, which used the same full-resolution file.

## 3. Licences for the countries C would use

`licence_fillable.csv` lists all 32 countries with at least one fillable row. **DR Congo:**
- `boundaryLicense` = **Open Data Commons Open Database License 1.0**
- `boundarySource` = **OpenStreetMap, Wambacher**
- `licenseDetail` = **empty** (`nan`)

| licence | countries | fillable records |
|---|---|--:|
| **ODbL 1.0** | DR Congo, Finland, Malaysia, Cuba, Indonesia, Kazakhstan, Morocco, Portugal, Russia, Egypt, Slovakia | **126** |
| CC BY 3.0 IGO | Philippines, Mexico, Chile, North Korea | 18 |
| CC BY 4.0 | Ethiopia, Norway, New Zealand, Australia, Czech Republic, Rwanda, United Kingdom | 24 |
| CC BY 2.5 / 3.0 | Brazil, Fiji, Jordan; Sweden | 10 |
| Public Domain | United States, Bulgaria, Bolivia, Peru | 9 |
| Open Government Canada 2.0 | Canada | 2 |
| Etalab 2.0 | France | 2 |

**126 of the 191 fillable records, including all 98 Katanga records, rely on ODbL shapes.** Those come from OpenStreetMap. Whether a MinMod state value derived from them carries ODbL's share-alike obligations is a decision for the team, not something these numbers settle.

## 4. Corrections to v1

### 4.1 Step 1 headline: unchanged counts, one new caveat

The counts stand: ISO 2,803, name 167, alt name 2, **matched 2,972 of 5,086 (58.4%)**, ambiguous 111, unmatched 1,870, no gbOpen ADM1 133.

**New: at least 31 of the 2,972 matches are wrong.**
- **Iran 24:** MinMod's Iran `state_code`s do not follow the ISO codes gB uses (Tehran → `IR-23` = Hormozgan, Isfahan → Khuzestan, …).
- **Liberia 2:** River Cess and River Gee are swapped.
- **Republic of Congo 2:** Lékoumou and Likouala are swapped.
- **Papua New Guinea 2:** Western and Western Highlands are swapped.
- **Niger 1:** Tahoua → Tillabéri.

The evidence:
- For 29 of these, another shape in the same country carries the MinMod name exactly.
- For 30 of them, MinMod's own point lies in the correctly named shape (4.3).

371 other ISO matches have names that differ after folding and were **not** reviewed one by one (`iso_match_check.txt`). Most look like language or spelling variants (Latvian `novads`, Swedish `län`, Indonesian and Ukrainian names). **None of the section 1 fills goes through a wrong ISO match:** the 6 fills whose shape name differs from the state are all spelling variants, such as `Gävleborgs län` = Gävleborg County.

### 4.2 The 212 centroids outside the country

**v1 said:** "I hand-checked the 212: the matches are right and MinMod's coordinates are wrong."

**What was actually done in v1:** I read the first 25 of the 270 flagged rows in file order. 21 of them are among the 212.

**Now all 212 are checked by rule** (`centroid_recheck.py`, `centroid_recheck.csv`):
- **The coordinate is wrong in 212 of 212.** MinMod's point lies outside the state's own recorded country. 121 are in the United States, 28 at sea or in a country gB lacks, 11 in Canada, and 52 elsewhere.
- **The match is right in 212 of 212**, on name evidence:
  - 183 names agree after folding.
  - 29 are ISO matches whose names differ only in spelling or language. I read all 29 individually and each is the same place (Adamawa/Adamaoua, Addu Atoll/Addu, Victoria/Rabat Gozo, …).

### 4.3 The 58 "outside the shape but in the country"

**All 58 were checked individually** (`centroid_recheck.csv`).

| verdict | count | detail |
|---|--:|---|
| **match wrong** | **30** | Iran 24, Liberia 2, Republic of Congo 2, Papua New Guinea 1, Niger 1. In 29, MinMod's point lies in the shape that carries the MinMod name. Hamadan's lies in neighbouring Kermanshah, and its match (Sistan and Baluchestan) is wrong either way. |
| match right, coordinate wrong or imprecise | **28** | 7–25 km off, often a capital or city near a border: Neuquén, Crooked Island, Bengo, Sidi Bel Abbès, Bogotá. Or swapped between neighbours: Mayo-Kebbi Est/Ouest, Xagħra/Xgħajra. Or far off: Innlandet in Vestland, Muchinga in Lusaka, Hidalgo at 26.1 N in Texas (inside Mexico's slack). |

### 4.4 Country totals

**v1 said:** 115 fully matched and 78 with unmatched states. That is 193, not 203.

| group | countries |
|---|--:|
| fully matched (no unmatched, no ambiguous) | 115 |
| at least one unmatched state | 71 |
| no gbOpen ADM1 | 7 |
| ambiguous only (CF, EC, GM, IR, LA, LU, MT, MX, MZ, VN) | 10 |
| **total** | **203** |

**v1's 78 was 71 + 7.** "Fully matched" means every state got a single name or ISO match. **It does not mean every match is right:** Iran, for example, falls in "ambiguous only", with 24 wrong single matches.

### 4.5 "Level mismatch"

**v1 said:** level mismatch is "not a matching failure" and explains 1,730 of 1,870 unmatched.

**Correction:** that is an **estimate from a rule**, not a measurement. The rule is "the country has more than twice as many MinMod states as gB ADM1 shapes". It flags 29 countries holding 1,730 of the 1,870 unmatched states (92.5%). I looked at the unmatched names for Italy, Slovenia, Spain, Greece and Nepal, which are provinces, municipalities, provinces, regional units and old zones respectively. I did not verify the admin level of each of the 1,730 rows, and the UK case rests on the counts alone.

### 4.6 Step 3

**v1 said:** skipped because the lists were not available. **It is now done:** see section 1.

### 4.7 Verdict, corrected

**Where geoBoundaries ADM1 works.** It matches **2,972 of 5,086 states (58.4%)**, of which at least 31 are wrong.

**For the cases C is meant for:**
- C could fill a state that I would accept for **157 of the 338 dropped records (46.4%)** and **143 of the 313 emptied entities (45.7%)**.
- Katanga accounts for 98 and 94 of those.
- C is no help for:
  - **Option A (0 of 70 entities):** no gbOpen shapes, or no MinMod rows.
  - the 16 Albania/Guinea records, whose shapes are ambiguous in MinMod's own table;
  - the 96 records whose point is outside their recorded country.
- **47 geometry-only fills contradict the observed name** (25 records, 22 entities), so **C should not fill without a name check or a review step.**

**By hand:**
- the 25/22 contradicting fills;
- the 9/8 unclear ones;
- the wrong ISO matches (Iran first);
- the Albania/Guinea duplicate rows;
- the ODbL decision covering 126 of the 191 fillable records.

## Files

| file | what |
|---|---|
| `emptied_313.csv`, `dropped_338.csv` | one row per entity / record: id, recorded country, observed state, reason group and note, WKT, CRS, C outcome, containing shape, the state it would fill, `name_check` |
| `coverage.py`, `name_check.py` | the section 1 analysis and the hand judgments |
| `coverage_results.json`, `name_check_results.json` | the tables above |
| `katanga_fullres.py`, `katanga_points_fullres.csv`, `katanga_fullres_results.json`, `katanga_boundary_distance.txt` | section 2 |
| `licence_fillable.csv`, `licence_fillable.txt` | section 3 |
| `centroid_recheck.py`, `centroid_recheck.csv`, `iso_match_check.txt` | section 4 |
| `fetch_full_res.py`, `geoboundaries_full/` | the full-resolution shapes: 48 countries; New Caledonia, Christmas Island, Montserrat, BVI and Cayman have no gbOpen ADM1. Namibia's full file has 13 shapes against the simplified file's 14; no Task 1 row is affected. |
| `rerun/` | code, data, script copies, the four ETL runs, `reports/p2d/` (records.json, merged.json, ids) |
