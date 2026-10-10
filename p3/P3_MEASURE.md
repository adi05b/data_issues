# P3 — Phase A: coordinate precision at merge time (measured)

*Read-only. Main `ab1c352`, merged offline on the p2c base data (`ta2-minmod-data` `3a086a5`). No graph, Postgres or API touched; no repo changes.*

**Run.** The p2c `runs/kg-base` was built before #108, so its `location_view` lat/lon are pre-fix for 38,828 non-WGS84 records. I re-ran the merge with main's code into `p3/run-main/` (fresh cache, 62 s). Then `p3_measure.py` rebuilt every merged site that has ≥ 2 members with a coordinate, plus every site with a `POINT(0 0)` member, using main's own `DedupMineralSite.from_dedup_sites` (as `prep_kgrel_input` does). Main's kept coordinate equals the first coordinate in global `SiteScore` order in **all 23,283** of those sites: the two-stage merge never departs from it.

Two small corrections to the background: `SiteScore`/`SystemCmpKey` live in `minmodkg/models/kgrel/custom_types/site_and_score.py`, not `base.py`. And all non-system users (`/users/u/`, `/users/a/`) get the same `ExpertCmpKey` at 1.0, so "expert" and "curator" are one tier.

## 1 — Precision: definition, and why the raw WKT

**Precision = the minimum number of decimal places over every x and y in `ms.location.coordinates`, as written.** That is the string the data repo shipped. It is carried untouched into the merged files next to its CRS (`location.crs` → `EPSG:n` via the entity service; no CRS means EPSG:4326, as `LocationView.from_location` reads it). `location_view.lat/lon` are floats: they are centroids and may have been reprojected, so their digits say nothing about the source. Z/M ordinates and an `SRID=n;` prefix are ignored.

As written, though, the digits are mostly **formatting**, not survey precision. I also computed *effective* places, which drop trailing zeros and float noise (`28.1180500000000002` → 5):

| | records |
|---|---:|
| MRDS, padded to 16 places (`28.1180500000000002`) | 304,610 (100% of MRDS WKT) |
| NC Geological Survey, padded | 7,008 (100%) |
| Full float prints, ≥ 15 significant digits (`868492.6492782086`): places track magnitude, not precision | 29,266 (Oregon EPSG:2994 23,313 = 100%; Idaho 1,137; podchrome 1,024; vms 1,037) |
| DMS-shaped (below) | 5,119 |

## 2 — A1 tables

679,778 records. **233,353 (34.3%) have no raw WKT.** 446,425 have one, and 2 of those give no lat/lon (`POINT (-68.61328 NaN)`, and a `MULIPOINT(…)` typo).

**Geometry.** POINT 446,209 · MULTIPOINT 215 · POLYGON **0** · other 1 (the typo).

**Written places by CRS** (9 = 9+):

| CRS | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9+ | total |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| EPSG:4326 | 1,134 | 4,912 | 16,296 | 2,360 | 10,913 | 36,618 | 1,560 | 2,666 | 11,523 | 319,174 | 407,157 |
| none (→4326) | 28 | 72 | 46 | 58 | 137 | 44 | 37 | 7 | 9 | 2 | 440 |
| EPSG:4267 (NAD27) | 36 | 250 | 1,091 | 2,057 | 3,867 | 419 | 0 | 0 | 0 | 0 | 7,720 |
| EPSG:26912 (UTM m) | 7,792 | — | — | — | — | — | — | — | — | — | 7,792 |
| EPSG:2994 (Oregon ft) | 23 | 15 | 33 | 51 | 0 | 0 | 0 | 0 | 610 | 22,584 | 23,316 |

Effective places for EPSG:4326 are 1,134 · 5,451 · 17,658 · 8,403 · 70,226 · **274,369** · 4,133 · 7,050 · 11,523 · 7,209: the 9+ bucket collapses from 319,174 to 7,209, mostly into 5. The other CRSs are unchanged. By geometry, MULTIPOINT spreads 19 · 55 · 31 · 21 · 47 · 19 · 19 · 1 · 1 · 2.

**DMS-looking values.** A long decimal (≥ 6 effective places) on the arcsecond grid, e.g. `.1666667` or `29.774722` (= 29°46′29″). A record counts when every axis is DMS-shaped: a long on-grid decimal, or a short decimal that is a whole arcminute (`.25`), with at least one long one. At 6 places a random axis hits the grid with p = 0.0036, so about 0.4 chance hits are expected among the 29,966 degree records with ≥ 6 effective places. Result: **5,119 records (1,954 arcminute, 3,165 arcsecond)**, plus 971 where only one axis is DMS-shaped. The earlier graph figure was 5,287.

| source | DMS-shaped | % of its WKT | + one axis |
|---|--:|--:|--:|
| mrdata `podchrome` | 843 | 81% | 181 |
| mrdata `vms` | 836 | 77% | 201 |
| mrdata `major-deposits` | 637 | 20% | 44 |
| mrdata `sedcu` | 555 | 78% | 60 |
| mrdata `porcu` | 551 | 80% | 74 |
| mrdata `ree` | 470 | 81% | 2 |
| mrdata `phosphate` | 452 | 38% | 25 |
| mrdata `sedznpb` | 407 | 80% | 82 |
| mrdata `laterite` | 99 | 83% | 17 |
| mrdata `sedau` | 96 | 78% | 22 |
| Inferlink (`api.cdr.land`) | 92 | 8% | 13 |
| mrdata `carbonatite` | 46 | 77% | 14 |
| `sir20105090z` · `pp1802` · `deposit` · Virginia · `ofr20151121` | 20 · 11 · 2 · 1 · 1 | ≤ 3% | |

MRDS shows 0 because its values carry only 5 real places, too few to tell DMS from decimal at this threshold.

## 3 — A2: what main keeps, next to the earlier figures

23,283 merged sites have ≥ 2 members with a coordinate.

| | earlier | this run |
|---|--:|--:|
| keeps a coarser coordinate (plan's definition: fewer written places than some member) | — | **6,315** |
| same, like-for-like with the earlier rule (explicit-4326 POINTs, `v_election.py` resolution, > 3×) | **1,269** of 7,362 | **3,815** of 20,856 |
| multi-coordinate sites whose top score is tied | **75.5%** | 79.8% (18,583): **95% broken by `record_id`**, 5% by `source_id` |
| `POINT (0 0)` records | **36** | **37**, all Inferlink (`POINT(0 0)` 27, `POINT(0.0 0.0)` 6, `MULTIPOINT(0 0)` 3, `POINT(-0.0 0.0)` 1; 24 EPSG:4326, 13 no CRS) |
| merged sites with one · keeping it · keeping it while another member has a real coordinate | — · — · 1 | 34 · **29** · **4** |

The earlier groups were `owl:sameAs` components from the live graph. These are the merge's own groups, which also link records automatically by `(source_id, record_id)`. That is why the like-for-like count is 3× higher.

**Why the 6,315 keep a coarser coordinate** (compared with the highest-ranked more-precise member):

| | all | both EPSG:4326 |
|---|--:|--:|
| (a) tie on score: what the fix changes | **923** | 681 |
| (b) kept record has a higher score: left alone | 5,375 | 3,410 |
| (c) kept record is expert/curator: left alone | 17 | 17 |
| kept has a *lower* score | 0 | 0 |

- (a) ties are broken by `record_id` in **724** cases and by `source_id` in 199. These are mostly sibling records of one source inside one merged site, not two sources disagreeing.
- (b) is 5,094 cases of a 0.5 source over **MRDS (0.1)**, plus 0.8/0.7 over MRDS. MRDS "wins" on places only through its 16-place padding. Once padding is dropped, 3,536 of the 5,375 are not coarser at all, and the 6,315 shrinks to about 2,764.

**Sonora Lithium Project: not reproduced on this data.** Its merged site has 7 Inferlink members, all at 0.8, spread from (−110.92, 29.08) to (−109.10, 29.77) to (−110, 31). The `record_id` tie-break keeps `02ec…` → `POINT(-109.103889 29.774722)`, and `POINT(0 0)` (`0205…`) ranks last. So (−109.103889, 29.774722) is in the group and is the coordinate kept. That value is itself DMS-shaped (109°06′14″W 29°46′29″N). The earlier "keeps `POINT (0 0)`" came from a graph sameAs component; I can't check the live graph from here.

## 4 — The fix, simulated

The plan as written: among system records at the top score, take the most written places, otherwise the current order. Experts/curators are never overridden. `POINT(0 0)` (numerically zero, any spelling) is treated as no coordinate. The two variants are the recommendation's inputs.

| | plan | plan + consistency gate | effective/ground precision + gate |
|---|--:|--:|--:|
| merged sites whose coordinate changes | **949** | 193 | 740 |
| · by precision · by Null Island | 920 · 29 | 164 · 29 | 711 · 29 |
| Null Island → no coordinate · → a real member | 25 · 4 | 25 · 4 | 25 · 4 |
| precision changes to strictly more written places | 920 | 164 | 150 |
| precision changes actually finer on the ground | 817 | 151 | 711 |
| distance moved, precision changes: median · p95 · max | **0.74 km · 82 km · 12,378 km** | 6 m · 6.6 km · 133 km | 4 m · 1.15 km · 133 km |
| moves > 50 km (incl. Null Island) | **64** | 5 | 5 |
| precision changes within one source (sibling records) | 720 | 107 | 574 |
| winner is a float print · DMS-shaped · different CRS unit | 312 · 125 · 21 | 36 · 32 · 6 | 43 · 20 · 23 |
| changes in a group led by an expert/curator or a higher score | **0** | 0 | 0 |
| precision change between different scores | 0 | 0 | 0 |

- **Gate:** the new point must lie inside the box that the kept point's own last real decimal allows (√2 × one unit, in km).
- **Ground precision:** effective places, DMS at its grid (arcmin 1.86 km, arcsec 31 m), and units per CRS (degree / m / ft).
- The 5 moves over 50 km left under the gate are the 4 Null Island fallbacks and one 0-place point (`POINT(147 -6)` → 133 km).

**What the plan's 920 precision changes are:** P9HTERGK sibling records 381 (median 0.37 km, 4 → 5 places). Oregon EPSG:2994 siblings 176, all float prints, where places differ only with magnitude (median 2.2 km, max 321 km). `sir20105090z` → `sedcu` 75: mostly 4 places, beaten by 12–13-place float prints that are DMS-shaped (74 of 75), a median 23 m away. Inferlink siblings 50 (median **150 km**). ARDF siblings 43. Only **164 of 920 (18%)** land where the kept coordinate's own digits say the site is.

**Null Island fallbacks:** Munali → MRDS (28.118, −15.897), correct. Lynn Lake → (−99.67, 55.99), Manitoba. **Oropesa (Spain) → `MULTIPOINT(-5.475 -19.00)`** and **Ambatovy (Madagascar) → `MULTIPOINT(48.0 17.5)`**: both are latitude sign flips.

### Every plan change > 50 km (64)

60 precision + 4 Null Island. 58 are siblings within one source, 9 are hemisphere sign flips, 13 winners are DMS-shaped, 8 are float prints. `out/fix_gt_50km_plan.csv` has the site ids in full.

| km | why | dedup site | kept (source, dp, WKT) | would keep (source, dp, WKT) |
|---:|---|---|---|---|
| 12,378 | sign flip, same source | `api-cdr-land-v1-docs-documents__0213afe1…` | inferlink, 1, `POINT(-60.0 55.0)` | inferlink, 3, `POINT(-60.759 -56.316)` |
| 11,039 | sign flip, same source | `api-cdr-land-v1-docs-documents__020ad3e9…` | inferlink, 3, `POINT(-97.098 -49.382)` | inferlink, 4, `POINT(-97.1577 49.8951)` |
| 10,607 | null island, same source | `api-cdr-land-v1-docs-documents__022da331…` | inferlink, 0, `POINT(0 0)` | inferlink, 6, `POINT(-99.667257 55.986045)` |
| 9,318 | sign flip, same source | `api-cdr-land-v1-docs-documents__02b43b4f…` | inferlink, 1, `POINT(-8.617 -41.9)` | inferlink, 5, `POINT(-8.61667 41.90000)` |
| 8,982 | sign flip, same source | `api-cdr-land-v1-docs-documents__029167a0…` | inferlink, 1, `MULTIPOINT(-7.4 40.5)` | inferlink, 3, `MULTIPOINT(-7.485 -40.279)` |
| 8,698 | sign flip, new is DMS, new is float print | `doi-org-10-2113-econgeo-110-8-1925__mrim…` | ree, 2, `POINT (-39.25 -4.4166666666667)` | carbonatite, 13, `POINT (39.2527777777778 -4.48611111111111)` |
| 8,559 | same source | `api-cdr-land-v1-docs-documents__021fd286…` | inferlink, 2, `MULTIPOINT(76.35 50.58)` | inferlink, 4, `POINT(-71.1842 48.6155)` |
| 8,238 | same source | `api-cdr-land-v1-docs-documents__027118b5…` | inferlink, 1, `POINT(27.0 22.0)` | inferlink, 5, `POINT(111.91667 33.26667)` |
| 7,532 | sign flip, same source, new is DMS | `api-cdr-land-v1-docs-documents__02469da6…` | inferlink, 0, `MULTIPOINT(116 33.8667)` | inferlink, 7, `POINT(116.0666667 -33.8666667)` |
| 6,272 | same source | `api-cdr-land-v1-docs-documents__02245690…` | inferlink, 0, `POINT(127 54)` | inferlink, 1, `POINT(-125.4 54.3)` |
| 6,269 | sign flip, same source, new is DMS | `api-cdr-land-v1-docs-documents__02630950…` | inferlink, 4, `POINT(-75.8333 60.3333)` | inferlink, 6, `MULTIPOINT(75.916667 61.366667)` |
| 5,690 | sign flip, same source | `api-cdr-land-v1-docs-documents__02a714ec…` | inferlink, 4, `POINT(26.0917 -10.9542)` | inferlink, 5, `POINT(-26.05861 -10.55333)` |
| 5,598 | null island, same source | `api-cdr-land-v1-docs-documents__022513c3…` | inferlink, 0, `POINT(0 0)` | inferlink, 1, `MULTIPOINT(48.0 17.5)` |
| 4,959 | same source | `mrdata-usgs-gov-phosphate__1134__sri` | phosphate, 1, `POINT (60.416667 -11.1)` | phosphate, 5, `POINT (18.01667 -33.13333)` |
| 4,424 | same source, new is DMS | `mrdata-usgs-gov-phosphate__954__sri` | phosphate, 1, `POINT (177.3 -43.6)` | phosphate, 6, `POINT (139.166667 -19.666667)` |
| 3,900 | same source | `mrdata-usgs-gov-phosphate__1270__sri` | phosphate, 2, `POINT (-73.75 11.01667)` | phosphate, 5, `POINT (-66.18194 45.48417)` |
| 3,556 | null island | `api-cdr-land-v1-docs-documents__0254ffd6…` | inferlink, 1, `POINT(0.0 0.0)` | mrds, 16, `POINT (28.1180500000000002 -15.8971699999999` |
| 3,383 | same source, new is DMS | `mrdata-usgs-gov-phosphate__1068__sri` | phosphate, 1, `POINT (40.5 37.516667)` | phosphate, 6, `POINT (33.216667 67.666667)` |
| 3,378 | same source | `api-cdr-land-v1-docs-documents__02368feb…` | inferlink, 0, `POINT(140 40)` | inferlink, 1, `POINT(100.0 40.0)` |
| 2,196 | null island, same source | `api-cdr-land-v1-docs-documents__021c1446…` | inferlink, 1, `POINT(0.0 0.0)` | inferlink, 2, `MULTIPOINT(-5.475 -19.00)` |
| 2,045 | sign flip, same source | `api-cdr-land-v1-docs-documents__024a6a6f…` | inferlink, 3, `POINT(39.043 8.783)` | inferlink, 4, `MULTIPOINT(39.4219 -9.6004)` |
| 1,551 | new is DMS, new is float print | `doi-org-10-5382-econgeo-2018-4590__squaw…` | sir20105090z, 4, `POINT (-115.9212 48.0928)` | porcu, 12, `POINT (-111.865277777778 34.4802777777778)` |
| 1,240 | same source | `mrdata-usgs-gov-phosphate__1080__sri` | phosphate, 1, `POINT (134.5 55.61667)` | phosphate, 5, `POINT (134.13333 44.46667)` |
| 1,049 | same source | `api-cdr-land-v1-docs-documents__02ad5940…` | inferlink, 3, `MULTIPOINT(-134.209 64.212)` | inferlink, 4, `MULTIPOINT(-113.4025 62.5102)` |
| 825 | same source | `api-cdr-land-v1-docs-documents__024d7e49…` | inferlink, 1, `POINT(104.5 21.4)` | inferlink, 4, `POINT(104.0000 14.0000)` |
| 669 | same source, new is DMS | `api-cdr-land-v1-docs-documents__025d16f7…` | inferlink, 0, `POINT(-121 49.5)` | inferlink, 1, `POINT(-121.633333 43.5)` |
| 619 | same source, new is DMS | `api-cdr-land-v1-docs-documents__0275b5be…` | inferlink, 4, `POINT(-81.6882 48.3801)` | inferlink, 8, `POINT(-88.91666667 45.76666667)` |
| 538 | same source | `api-cdr-land-v1-docs-documents__020810b6…` | inferlink, 4, `MULTIPOINT(-117.9731 62.0556)` | inferlink, 5, `POINT(-128.28333 61.96667)` |
| 437 | same source, new is DMS | `mrdata-usgs-gov-phosphate__1112__sri` | phosphate, 1, `POINT (-17.083333 14.8)` | phosphate, 2, `POINT (-13.05 15.333333)` |
| 426 | same source | `api-cdr-land-v1-docs-documents__024cd226…` | inferlink, 2, `POINT(-83.36 48.68)` | inferlink, 4, `POINT(-89.1334 48.3734)` |
| 392 | same source | `mrdata-usgs-gov-phosphate__1132__sri` | phosphate, 0, `POINT (31.1333 -24)` | phosphate, 5, `POINT (27.51667 -25.28333)` |
| 375 | same source | `mrdata-usgs-gov-phosphate__491__sri` | phosphate, 1, `POINT (35.7 9.25)` | phosphate, 2, `POINT (38.76667 10.75)` |
| 355 | same source, new is DMS | `mrdata-usgs-gov-phosphate__1168__sri` | phosphate, 2, `POINT (24.05 61.716667)` | phosphate, 6, `POINT (27.833333 64.416667)` |
| 321 | same source, new is float print | `www-oregongeology-org__id-01389__umn` | www.oregongeolog, 10, `POINT (868492.6492782086 1274815.4537401646)` | www.oregongeolog, 11, `POINT (503198.03280839324 287846.20078739524` |
| 308 | same source | `api-cdr-land-v1-docs-documents__02ee850d…` | inferlink, 4, `POINT(102.7153 29.6323)` | inferlink, 5, `POINT(99.64444 30.41667)` |
| 291 | same source | `mrdata-usgs-gov-phosphate__1103__sri` | phosphate, 0, `POINT (38 34.23333)` | phosphate, 4, `POINT (38.653056 31.6775)` |
| 289 | same source | `api-cdr-land-v1-docs-documents__025c0855…` | inferlink, 3, `POINT(-116.000 41.396)` | inferlink, 6, `POINT(-116.131385 38.800844)` |
| 263 | same source, new is DMS | `api-cdr-land-v1-docs-documents__0265105a…` | inferlink, 1, `POINT(-135.0833 60.5)` | inferlink, 6, `POINT(-139.533333 61.466667)` |
| 259 | same source | `mrdata-usgs-gov-major-deposits__2915__sr…` | major-deposits, 1, `POINT (20.5 -28.53333)` | major-deposits, 5, `POINT (17.88333 -28.93333)` |
| 175 | same source | `api-cdr-land-v1-docs-documents__021f19d6…` | inferlink, 1, `MULTIPOINT(-76.7 46.817)` | inferlink, 4, `POINT(-75.6667 45.4170)` |
| 173 | same source | `mrdata-usgs-gov-potash__474__sri` | potash, 3, `POINT (58.499 48.6678)` | potash, 4, `POINT (57.4641 50.0657)` |
| 169 | same source, new is DMS | `api-cdr-land-v1-docs-documents__0208a7f2…` | inferlink, 4, `POINT(-97.4253 56.2345)` | inferlink, 7, `POINT(-98.6511111 54.8800000)` |
| 167 | same source | `mrdata-usgs-gov-phosphate__1028__sri` | phosphate, 2, `POINT (29.25 67.75)` | phosphate, 5, `POINT (33.06667 67.38333)` |
| 165 | same source | `api-cdr-land-v1-docs-documents__026d0268…` | inferlink, 5, `POINT(-120.37284 53.77081)` | inferlink, 6, `POINT(-120.003433 52.303861)` |
| 158 | same source | `api-cdr-land-v1-docs-documents__029f4e4c…` | inferlink, 1, `MULTIPOINT(-78.11 49.5)` | inferlink, 6, `POINT(-75.927119 49.632846)` |
| 143 | same source | `api-cdr-land-v1-docs-documents__0279a917…` | inferlink, 1, `MULTIPOINT(25.5 -10.6833)` | inferlink, 4, `MULTIPOINT(26.7625 -11.0125)` |
| 133 | same source | `api-cdr-land-v1-docs-documents__02127a0d…` | inferlink, 0, `POINT(147 -6)` | inferlink, 1, `MULTIPOINT(145.8 -6.1)` |
| 98 | same source, new is float print | `www-oregongeology-org__id-01566__umn` | www.oregongeolog, 10, `POINT (729295.7828083932 531538.5777558982)` | www.oregongeolog, 11, `POINT (509594.45538057387 296961.42322835326` |
| 97 | same source | `mrdata-usgs-gov-phosphate__1211__sri` | phosphate, 2, `POINT (1.58333 7.25)` | phosphate, 5, `POINT (1.44972 6.38722)` |
| 93 | same source | `api-cdr-land-v1-docs-documents__025f5c2a…` | inferlink, 3, `MULTIPOINT(29.256 -1.466)` | inferlink, 4, `POINT(29.2290 -0.6341)` |
| 82 | same source, new is DMS | `mrdata-usgs-gov-phosphate__1322__sri` | phosphate, 2, `POINT (-110.966667 43.45)` | phosphate, 6, `POINT (-110.816667 42.716667)` |
| 80 | same source | `api-cdr-land-v1-docs-documents__020bccd9…` | inferlink, 1, `POINT(-65.0 -24.0)` | inferlink, 4, `POINT(-65.6902 -24.3453)` |
| 74 | same source | `api-cdr-land-v1-docs-documents__022f2ffb…` | inferlink, 1, `POINT(43.72 -23.5)` | inferlink, 4, `POINT(44.3407 -23.1520)` |
| 73 | new is float print | `doi-org-10-5066-p9htergk__32594__umn` | P9HTERGK, 5, `POINT (-123.93305 41.68152)` | www.oregongeolog, 11, `POINT (427045.29363517463 229059.33825458586` |
| 72 | same source | `api-cdr-land-v1-docs-documents__02579c22…` | inferlink, 1, `POINT(144.0 -37.0)` | inferlink, 6, `POINT(144.793888 -36.874167)` |
| 71 | same source | `api-cdr-land-v1-docs-documents__0206bec1…` | inferlink, 4, `POINT(-88.6308 14.8293)` | inferlink, 6, `POINT(-89.211476 14.519588)` |
| 63 | - | `api-cdr-land-v1-docs-documents__0222814d…` | 295581, 5, `POINT(-66.81667 45.43333)` | inferlink, 6, `POINT(-66.373420 45.903780)` |
| 60 | same source | `api-cdr-land-v1-docs-documents__027e7942…` | inferlink, 1, `MULTIPOINT(-65.5 -24.5)` | inferlink, 2, `POINT(-65.43 -23.96)` |
| 60 | same source | `api-cdr-land-v1-docs-documents__02035b7c…` | inferlink, 4, `POINT(-99.5525 41.0312)` | inferlink, 6, `MULTIPOINT(-99.999973 40.610883)` |
| 53 | same source, new is float print | `www-oregongeology-org__id-04713__umn` | www.oregongeolog, 10, `POINT (368257.2283464521 378659.84317585826)` | www.oregongeolog, 11, `POINT (305914.88221785426 215575.87762467563` |
| 52 | same source | `api-cdr-land-v1-docs-documents__0254b900…` | inferlink, 1, `POINT(-127.185 54.5)` | inferlink, 4, `POINT(-127.7125 54.85416667)` |
| 51 | same source | `api-cdr-land-v1-docs-documents__022bc134…` | inferlink, 3, `POINT(-71.059 48.416)` | inferlink, 5, `POINT(-71.60011 48.69945)` |
| 51 | new is float print | `doi-org-10-5066-p9htergk__14818__umn` | P9HTERGK, 5, `POINT (-123.90895 41.83422)` | www.oregongeolog, 10, `POINT (414603.4737532735 213342.8992782086)` |
| 50 | same source, new is float print | `www-oregongeology-org__id-18232__umn` | www.oregongeolog, 9, `POINT (660052.2857611477 432278.039041996)` | www.oregongeolog, 10, `POINT (819230.9983595759 477972.31594488025)` |

## 5 — Recommendation

1. **Don't ship the tie-break on written places.** The plan's own invariant holds (0 changes against an expert/curator or a higher score). But the move distribution does not support it: median 0.74 km, p95 82 km, 64 moves over 50 km, 9 of them hemisphere flips. In 82% of its changes the "more precise" point is not a refinement of the kept one; it is a different point, usually a sibling record of the same source. Written places reward formatting: MRDS's 16-place padding, the float prints (Oregon, 23,313 records, 100%), and 5,119 DMS conversions that look like 6+ places but resolve to 31 m or 1.86 km.
2. **If a precision tie-break goes ahead,** use effective places with DMS at its grid and units per CRS, and only accept a winner that lies inside the kept point's own uncertainty box. Simulated: 711 changes, median 4 m, p95 1.15 km, 0 invariant breaks. Add a per-axis box, or exclude 0-place tops, to remove the single 133 km case. Comparing places across CRSs (degrees vs m vs ft) has to go through ground units; there are 21 such changes in the plan.
3. **Keep the Null Island part, with numeric detection** (`POINT(-0.0 0.0)` exists). It changes 29 sites: 25 lose a meaningless coordinate and keep country/state. But 2 of the 4 fallbacks land in the wrong hemisphere, so I'd consider falling back only to a point that agrees with the record's country.
4. **Non-POINT geometries are a non-issue:** no polygons; 215 MULTIPOINTs (17 plan changes); 1 `MULIPOINT` typo and 1 `NaN`, both already without lat/lon.
5. **New, out of scope:** Inferlink extractions carry hemisphere sign errors (9 among the > 50 km moves, plus Oropesa/Ambatovy). This is worth its own issue next to the Null Island one.
6. **Fix the issue text before posting.** 1,269 → 6,315 (plan definition) or 3,815 (like-for-like). The "~75% decided by `source_id`" claim is wrong: 75.5% was the tied share of *all* multi-record groups, and ties are broken by `record_id` 95% of the time. Of the coarser-kept sites, only 923 (15%) are ties. 36 → 37. Sonora is not reproduced on this data.

## Files

- `p3_measure.py`: A1 + A2 + simulation. It self-checks the parser and DMS rule on start.
  ```
  CFG_FILE=$MAIN/tests/resources/config.yml PYTHONPATH=$MAIN .venv-p2/bin/python p3_measure.py run-main out
  ```
  `run-main/` was made with `../p2c/rerun/scripts/p2d_run_merge.py ../p2c/rerun/scripts/p2_etl.yml run-main ../p2c/rerun/data/base`, using the same env.
- `p3_gt50.py`: the table above.
- `out/p3_measure.json`: every number. Also `out/coarser_kept.csv` (6,315), `out/fix_changes_{plan,plan+gate,ground+gate}.csv`, `out/fix_gt_50km_plan.csv`, `out/null_island.csv`.
