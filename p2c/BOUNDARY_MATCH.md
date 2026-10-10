# Problem 2, Solution C: does geoBoundaries ADM1 match MinMod's state table?

*Aditi Bombe · 2026-10-09 · read-only. No live graph or API was queried. No repository was edited.*

## Inputs

**MinMod state table.** `data/entities/state_or_province.csv`, `adi05b/ta2-minmod-data`, branch `add-niamey-ekaterinburg` @ `250abc7`. It was sparse-cloned into `p2c/ta2-minmod-data/`. The file is CRLF.
- It has **5,086 rows, not 5,084.** Upstream main has 5,084, and this branch adds Niamey (Q7085) and Zacapa Department (Q7086).
- All 5,086 were matched, and every percentage below is of 5,086.

**geoBoundaries.** gbOpen ADM1 from the API at `…/gbOpen/ALL/ADM1/`, fetched 2026-10-09.
- All files come from geoBoundaries commit `9469f09`. `buildDate` is Dec 12, 2023 for 193 entries, Feb 21, 2024 for 4, and Jul 05, 2023 for 2.
- **The API lists 199 entries for 198 countries.** India appears twice (an `ADM0` id and an `ADM1` id), but both point to the same file.
- The simplified GeoJSON for each country is in `geoboundaries/`. Licences are in `licenses.csv`.

**Katanga records.** `ta2-minmod-data` main @ `3a086a5` (`~/minmod-p1-p4-fix/minmod_data_issues/data-p2`). This is the same snapshot as the earlier 97/111 measurement.

**Outputs:**
- `boundary_match.py`, the script.
- `state_shape_match.csv`, one row per state.
- `per_country.csv`.
- `centroid_check.csv`.
- `katanga_points.csv`.
- `boundary_match_results.json`.

**geoBoundaries' own data has defects the matcher has to handle:**
- 24 shape names are mojibake (Chile 16, Portugal 6, Seychelles 2; `RegiÃ³n de …`). The script repairs these before folding.
- Seychelles names are cut at 10 characters (`Outer Isla`).
- China's Guangdong is labelled **"Guangzhou Province"**.
- Italy's ADM1 is the 5 NUTS-1 macro-regions, not the 20 regions. Slovenia's is 2 cohesion regions.

## 1. Headline

| result | states | % of 5,086 |
|---|--:|--:|
| matched by ISO code | 2,803 | 55.1% |
| matched by folded name | 167 | 3.3% |
| matched by alt name | 2 | 0.04% |
| **matched, total** | **2,972** | **58.4%** |
| ambiguous (not resolved) | 111 | 2.2% |
| unmatched, country has a shape set | 1,870 | 36.8% |
| unmatched, country has no gbOpen ADM1 | 133 | 2.6% |

**The ambiguous 111 break down as:**
- **102 are two or three MinMod states landing on one shape.** For example, Albania has both `Berat County` and `Berat District` → `AL-01 Berat`. By country: Lithuania 26, Albania 20, Bangladesh 14, Guinea 12, Côte d'Ivoire 8.
- **9 are one state matching two shapes on ISO.**

**Check on the matches.** For the 2,972 single matches, I tested whether the matched shape contains MinMod's own lat/lon for that state:

| result | states |
|---|--:|
| inside, within 5 km | 2,655 |
| outside the shape but in the country | 58 |
| **outside the country entirely** | **212** |
| no lat/lon | 47 |

I hand-checked the 212: the matches are right and MinMod's coordinates are wrong. For example, Helmand sits at 39.30, −76.62 (Baltimore), and the Barbados parishes are placed in Oklahoma and France. **MinMod's state centroids cannot be used to fill or check anything.**

## 2. Per country, worst first

All 78 countries with at least one unmatched state are in `per_country.csv`. These are the top ones and every country with no gbOpen ADM1:

| country | MinMod states | gB ADM1 shapes | matched | ambiguous | unmatched | why |
|---|--:|--:|--:|--:|--:|---|
| United Kingdom | 247 | 4 | 4 | 0 | 243 | MinMod has counties; gB has England/Scotland/Wales/NI |
| Slovenia | 211 | 2 | 0 | 0 | 211 | MinMod has municipalities; gB has 2 cohesion regions |
| Uganda | 125 | 4 | 4 | 0 | 121 | MinMod has districts |
| Italy | 111 | 5 | 0 | 0 | 111 | MinMod has regions + provinces; gB has 5 macro-regions |
| France | 123 | 13 | 13 | 0 | 110 | MinMod also has departments |
| **Puerto Rico** | 88 | — | — | — | 88 | **no gbOpen ADM1** |
| North Macedonia | 84 | 8 | 0 | 0 | 84 | MinMod has municipalities |
| Philippines | 98 | 17 | 16 | 0 | 82 | MinMod also has provinces |
| Latvia | 118 | 43 | 36 | 3 | 79 | mixed levels |
| Czech Republic | 90 | 14 | 14 | 0 | 76 | MinMod also has districts |
| Morocco | 87 | 12 | 12 | 0 | 75 | MinMod also has provinces |
| Azerbaijan | 75 | 2 | 1 | 0 | 74 | gB has 2 units |
| Bangladesh | 70 | 8 | 1 | 14 | 55 | mixed levels |
| Spain | 53 | 19 | 4 | 0 | 49 | MinMod has provinces; gB has communities |
| Burkina Faso | 57 | 13 | 13 | 0 | 44 | MinMod also has provinces |
| Lithuania | 69 | 10 | 0 | 26 | 43 | county + municipality pairs |
| Greece | 38 | 8 | 2 | 0 | 36 | MinMod has regional units |
| **Hong Kong** | 18 | — | — | — | 18 | **no gbOpen ADM1** |
| **Bermuda** | 9 | — | — | — | 9 | **no gbOpen ADM1** |
| **US Minor Outlying Is.** | 9 | — | — | — | 9 | **no gbOpen ADM1** |
| **Bonaire, St Eustatius, Saba** | 3 | — | — | — | 3 | **no gbOpen ADM1** |
| **New Caledonia** | 3 | — | — | — | 3 | **no gbOpen ADM1** |
| **US Virgin Islands** | 3 | — | — | — | 3 | **no gbOpen ADM1** |

**Most of the gap is a level mismatch, not a matching failure.** In 29 countries MinMod has more than twice as many "states" as gB has ADM1 shapes. Those 29 hold **1,730 of the 1,870 unmatched (92.5%)**. ADM1 shapes cannot represent those MinMod rows at all.

**The other 140 unmatched need hand work:**
- Algeria: 10 wilayas created after gB's 48-unit set.
- Seychelles: 16, because of the truncated names.
- US: 10 minor outlying islands.
- China: 5, including the mislabelled Guangdong plus Xinjiang, Xizang, Ningxia and Macau.
- Chile: 4 spelling variants.
- Kosovo: 5.
- The remaining 90 are spread across other countries, led by Bahamas 11, Syria 8, Oman 7, Madagascar 6 and Maldives 6.

115 of the 203 countries match completely.

## 3. Licences

The figures cover 198 unique countries.

| licence | countries | MinMod states in them |
|---|--:|--:|
| **CC BY** (4.0, 3.0, 3.0 IGO, 2.5, 2.5 IN) | **62** | 1,986 |
| **ODbL 1.0** | **84** | **1,736** |
| Public Domain | 27 | 621 |
| CC0 | 7 (BDI, BGD, ECU, HUN, IRQ, LCA, NLD) | 200 |
| CC BY-SA 2.0 / 3.0 | 14 (AUT, BWA, GHA, GRD, JAM, KNA, SLV, TUR, XKX; GAB, GRL, MRT, SYC, WSM) | 232 |
| National licences | 4: Canada OGL 2.0, Switzerland swisstopo, Germany DL-DE-BY 2.0, France Etalab 2.0 | 178 |

**ODbL is the largest group.** It has a share-alike clause for derived databases, so it needs a decision before anything derived from these shapes is redistributed. The ShareAlike group needs the same decision.

## 4. Katanga dry run

**MinMod and gB agree on the post-2015 provinces:**
- gB has 26 DR Congo shapes. **None is Katanga.** The four successors are present: `CD-HK` Haut-Katanga, `CD-LU` Lualaba, `CD-HL` Haut-Lomami and `CD-TA` Tanganyika.
- MinMod's DR Congo table has the same 26 provinces, including all four successors: Q3000, Q3012, Q3001 and Q3021.

**The 111 drop-list records reproduce exactly.** These are the records whose state candidate observes `Katanga`/`Katanga Province` and is normalized to Q6152 Tanga (Tanzania).

| 111 drop-list records | count |
|---|--:|
| no location | 8 |
| round placeholder | 1 |
| point outside DR Congo (gB outline) | **4** |
| point inside DR Congo | **98** |
| ↳ Haut-Katanga | 50 |
| ↳ Lualaba | 43 |
| ↳ Tanganyika | 4 |
| ↳ Haut-Lomami | 1 |

**The earlier run found 97 inside and 5 outside.** That run used Natural Earth's DR Congo outline. It covers the same 102 points, and one near-border point falls on a different side of the two outlines.

**The 4 points outside DR Congo are flagged, not fixed.** Each lands inside DR Congo if one sign is flipped:

| location | source | flag |
|---|---|---|
| `POINT(-26.05861 -10.55333)` | cdr | longitude sign |
| `MULTIPOINT(26.5 10.75)` | cdr | latitude sign |
| `MULTIPOINT(23.499 10.934)` | cdr | latitude sign |
| `POINT (26.2228 10.6202)` | mrds 10400569 | latitude sign |

**Beyond the 111, there are 150 more Katanga records:**
- **148 were never normalized.** All have a point, splitting Haut-Katanga 77 and Lualaba 71.
- **2 are already normalized to Haut-Katanga.** One has no location. The other's point lands in Lualaba, so its point and its state disagree.

## 5. Coverage of the cases C is for

**Skipped: the lists are not available.**
- `reports/P2_PHASE5.md` and `P2_OPTION_A.md` give only counts.
- `reports/p2d/merged.json` gives `state emptied` = 313.
- `reports/p2d/records.json` gives `dropped.after` = 340 candidates / 338 records, split 198 blocked and 142 no suggestion.
- No file holds the entity or record ids.

They could be regenerated by having `investigation/p2d_measure.py` and `p2d_merged.py` write the ids out.

## 6. Verdict

**geoBoundaries ADM1 is good enough for C only where MinMod's "state" really is an ADM1 unit. That is 2,972 of 5,086 states (58.4%) in 115 fully-matched countries plus partial ones.** It is **not** good enough as a single source for the whole table:
- **1,730 states (34%) in 29 countries are finer than ADM1**: counties, districts, municipalities, provinces. No ADM1 shape can confirm or reject a point for them. Covering them would need gbOpen ADM2, which I did not evaluate.
- **133 states in 7 territories have no gbOpen ADM1.** Puerto Rico alone has 88.

**To handle by hand:**
- the 111 ambiguous states, mostly duplicate County/District rows in MinMod's own table;
- the 140 residual unmatched states;
- geoBoundaries' mislabelled, truncated and mojibake names;
- a licence decision for the 84 ODbL and 14 ShareAlike countries.

**For Katanga specifically, C works.** 98 of the 111 records get a successor province from their point, and 4 more are sign-flip candidates for review.
