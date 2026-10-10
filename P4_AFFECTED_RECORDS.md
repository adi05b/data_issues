# P4_AFFECTED_RECORDS.md — the CRS census, the 24, and worked examples

*Aditi Bombe · USC ISI · run 2026-09-21 (third pass — endpoint reachable) · **read-only**. Companion to `P4_DIAGNOSIS.md`.*
*Confidence: 🟢 verified · 🟡 likely · 🔴 assumed. **Raw-record grain** unless stated otherwise.*

---

## Lead: without the PROJ Alaska grid, the fix silently skips the 24 worst-displaced records 🟢

Not "24 records cannot be corrected" — that claim in `NAD27_IMPACT.md` is wrong. They are inside NADCON coverage. Confirmed per point with `get_last_used_operation()`, never off `TransformerGroup[0]`:

| | grids absent | grids present |
|---|---|---|
| PROJ operations available / unavailable | 31 / **48** | **79 / 0** |
| missing grid named by PROJ | **`us_noaa_alaska.tif`** | — |
| operation used for these 24 | `Ballpark geographic offset` | **`NAD27 to WGS 84 (85)`** |
| declared accuracy | **−1.0** (unknown) | **5.0 m** |
| returned the identity | **24 / 24** | **0 / 24** |

They shift **161.5–244.2 m** once corrected, against a corpus median of **126.5 m**. PROJ raises no error — it substitutes a ballpark operation and hands back the input. 🟢 `q4-the24-grid.json`

---

## Section 1 — the full CRS census (raw-record grain) 🟢

`:observed_name` **OPTIONAL**. The required form drops 7,869 records and invents a phantom CRS.

| `observed_name` | `normalized_uri` | EPSG | Records | Sources | Geographic | Affected by this defect? |
|---|---|---|---|---|---|---|
| `EPSG:4326` | Q701 | 4326 | **403,549** | 24 | yes | **no** — it is the target; `geo.py` short-circuits |
| `EPSG:2994` | Q705 | 2994 | 23,316 | 1 | **no** — projected | no — **Problem 1's axis swap** |
| **(absent)** | **Q701** | 4326 | **7,869** | **20** | yes | no — but **assumed, not declared** (below) |
| `EPSG:26912` | Q704 | 26912 | 7,792 | 1 | **no** — projected | no — **Problem 1's axis swap** |
| **`EPSG:4267`** | **Q702** | **4267** | **7,720** | **1** | **yes** | **YES — the defect** |
| `WGS84` | Q701 | 4326 | **1** | 1 | yes | no — literal string, normalizes to 4326 |
| **(no `:crs` node)** | — | — | **1,280** | 15 | — | no — never reaches the transformer |
| | | | **451,527** | | | |

🟢 `q1a-crs-census`, `q1b-no-crs-node`. Reconciles against the LocationInfo total exactly.

**Four CRSs are in use. The `:CoordinateReferenceSystem` vocabulary holds five** — `Q703` = **EPSG:3857** (Web Mercator) exists with **zero records**. It is projected, so data arriving in it would hit Problem 1's transposition, not this no-op: the current code returns `(39.738, −104.977)` — latitude first — for a Denver Web Mercator point. 🟢 `q1c-crs-entities`

### The 7,869 records with no `:observed_name` — never examined before 🟢

**All 7,869 normalize to Q701 (EPSG:4326). EPSG:4326 was assumed, not read from the source.**

| Source | Records | | Source | Records |
|---|---|---|---|---|
| `doi.org/10.5382/econgeo.2018.4590` | 2,301 | | `doi.org/10.3133/pp1802J` | 108 |
| `mrdata.usgs.gov/sir20105090z` | 1,200 | | `doi.org/10.5066/P99RK9SU` | 73 |
| `doi.org/10.1016/j.oregeorev.2016.08.010` | 851 | | `doi.org/10.3390/min10070626` | 28 |
| `mrdata.usgs.gov/sedcu` | 708 | | `doi.org/10.31035/cg2020009` | 20 |
| `mrdata.usgs.gov/porcu` | 690 | | `doi.org/10.3133/fs20243029` | 17 |
| `doi.org/10.5382/econgeo.4950` | 627 | | `minmod.isi.edu/unpublished/lithium-in-nevada…` | 16 |
| `mrdata.usgs.gov/sedznpb` | 506 | | 2 × researchgate | 15 |
| `mrdata.usgs.gov/deposit` | 428 | | `doi.org/10.1007/s00126-023-01161-3` | 6 |
| `doi.org/10.2113/econgeo.110.8.1925` | 267 | | `doi.org/10.3997/2214-4609.20215K2011` | 6 |
| | | | `api.cdr.land/v1/docs/documents` | 2 |

Overwhelmingly DOI/paper sources — the same profile as the Tagaung Taung record in Problem 1 (`econgeo.4950`, no `observed_name`, 4326 defaulted in, coordinates transposed at source). **If any of these are on another datum, the error is present and invisible**, because nothing records that the CRS was a default rather than a reading. 🟡

### The 1,280 with no `:crs` node at all 🟢

`api.cdr.land` 490 · `phosphate` 447 · `ree` 221 · `podchrome` 79 · `mrds` 20 · `major-deposits` 7 · `nfcritresource` 6 · `s00126-023-01161-3` 2 · `pp1802` 2 · and 6 sources with 1 each (`OFR-757`, `295581`, `P9K1HBNT`, `econgeo.4950`, `users/u/jhammars`, `bul/0615`).

---

## Section 2 — the merged entity carries no CRS 🟢

| | Count | Grain |
|---|---|---|
| NAD27 raw records | 7,720 | raw record |
| **distinct dedup entities** | **7,218** | merged entity |
| entities holding >1 NAD27 record | 353 | merged entity |
| largest entity | 16 NAD27 records | merged entity |
| **merged entities exposing a CRS** | **0 of 10 sampled** | merged entity |

The dedup record's complete key list — no CRS, no datum, no EPSG anywhere in the JSON:

```
['deposit_types','discovered_year','grade_tonnage','id','location',
 'mineral_form','modified_at','name','rank','sites','trace','type']

location = {"lat": 61.4187, "lon": -149.3953, "country": ["Q1235"], "state_or_province": ["Q6840"]}
```

🟢 `q2-dedup-crs-check.json`. **A downstream consumer cannot distinguish a NAD27-derived coordinate from a WGS84 one.**

**Entities that did *not* take a NAD27 coordinate:** 7 of 243 sampled (2.9 %), extrapolating to ≈208 of 7,218 — against the CSV's 78. Sample interval ≈1.2–5.9 %, so the CSV sits just below it. Not adjudicated. 🟡 `q2-coord-election-sample.json`

---

## Section 3 — both convergence populations, rebuilt 🟢

| | All pairs | Nearest sibling only |
|---|---|---|
| rows | **2,279** (hers 2,279) | **1,609** (hers 1,602) |
| entities | **1,470** (hers 1,470) | **1,470** (hers 1,470) |
| median before | **174.8 m** (174.2) | **159.2 m** (159.1) |
| median after | **101.4 m** (101.1) | **26.4 m** (32.2) |
| within 50 m before | **5.3 %** (5.3) | **6.5 %** (6.6) |
| within 50 m after | **47.6 %** (47.6) | **64.3 %** (64.7) |
| improving | 1,608 (70.6 %) | **1,234** (1,239) |

**Acceptance test passes on all-pairs.** 🟢 `q3-convergence-clean.json`

**Two exclusions were required, and both are findings:**

| Excluded | Pairs | Why |
|---|---|---|
| `dedup_site__doi-org-10-4095-295581__955__usc` | 10,850 | **1,329 members** spanning Oregon, Virginia and Alaska — a bad merge, not a mine |
| sibling coordinate with \|lat\| > 90 | 10,832 | **Problem 1's transposition**, live in the merged layer |

**677 of that one entity's members are `oregongeology.org` records whose merged coordinate has |lat| > 90.** Problem 1 is unfixed and is contaminating unrelated measurements today. 🟢

**`owl:sameAs` is not the dedup grouping** — it yields 373 pairs across 297 NAD27 records, 16 % of the population. Anyone rebuilding this from SPARQL alone gets the wrong answer. 🟢 `q3-nad27-siblings`

**Pairs that get worse (nearest-only): 360 of 1,609.** By sibling source: `mrds` **327**, `P9K1HBNT` 17, `deposit` 13, three others 1 each. MRDS carries the graph's lowest source score (0.1) and the most coarse coordinates, so the sibling is the likelier culprit. 🟡

---

## Section 4 — the 24, in full

All correct cleanly **with** `us_noaa_alaska.tif`. Listed so the fix can be audited, **never to be force-shifted**. Grids present, `NAD27 to WGS 84 (85)`, 5 m declared accuracy, geodesic shift on WGS84. 🟢

| record_id | site name | stored lon, lat | corrected lon, lat | shift (m) |
|---|---|---|---|---|
| `GI001` | Unnamed (on Gareloi Island) | −178.7700, 51.7600 | −178.772614, 51.758521 | **244.2** |
| `SL004` | Booshu Camp | −171.8230, 63.4580 | −171.825791, 63.457064 | **174.0** |
| `SL005` | Unnamed | −171.8100, 63.4800 | −171.812792, 63.479065 | **173.9** |
| `SL006` | Moghoweyik River | −171.7420, 63.4690 | −171.744788, 63.468067 | **173.6** |
| `SL003` | Kangik River | −171.7200, 63.5700 | −171.722794, 63.569070 | **173.3** |
| `SL009` | Moghoweyik R.; Upper | −171.6100, 63.4500 | −171.612779, 63.449070 | **173.1** |
| `SL011` | Boxer River | −171.5400, 63.3700 | −171.542769, 63.369071 | **173.0** |
| `SL002` | Ikoygak Creek | −171.6600, 63.6800 | −171.662799, 63.679074 | **172.8** |
| `SL008` | Poovookpuk Mountain | −171.5300, 63.4500 | −171.532775, 63.449073 | **172.8** |
| `SL010` | Unnamed | −171.5100, 63.4300 | −171.512772, 63.429073 | **172.7** |
| `SL001` | Tiflighak Bay | −171.6500, 63.7600 | −171.652805, 63.759076 | **172.6** |
| `SL007` | Ikalooksik River | −171.5000, 63.5400 | −171.502780, 63.539076 | **172.4** |
| `SL012` | Okok River | −171.4000, 63.3700 | −171.402761, 63.369075 | **172.4** |
| `SL013` | Unnamed | −171.3710, 63.3310 | −171.373757, 63.330075 | **172.3** |
| `SL014` | Powooiliak Point | −171.2960, 63.3650 | −171.298755, 63.364078 | **171.9** |
| `SL015` | Unnamed | −171.2100, 63.4200 | −171.212754, 63.419082 | **171.4** |
| `SL016` | Unnamed | −171.1200, 63.4400 | −171.122750, 63.439085 | **171.0** |
| `SL017` | Unnamed | −171.0400, 63.5300 | −171.042753, 63.529090 | **170.5** |
| `SL018` | Unnamed | −170.1900, 63.2800 | −170.192680, 63.279111 | **167.1** |
| `SL019` | Ongoveyuk River | −169.8600, 63.3900 | −169.862668, 63.389123 | **165.4** |
| `SL020` | Unnamed | −169.8100, 63.3700 | −169.812663, 63.369124 | **165.2** |
| `SL021` | Myghapowit Mountain | −169.5900, 63.2200 | −169.592636, 63.219128 | **164.4** |
| `SL022` | Kangukhsam Mountain | −168.9500, 63.2900 | −168.952603, 63.289146 | **161.6** |
| `SL023` | Tapisaghak River | −168.9100, 63.2700 | −168.912598, 63.269146 | **161.5** |

All are `ardf` / `https://doi.org/10.5066/P96MMRFD`, team tag `umn`, site id `site__doi-org-10-5066-p96mmrfd__<record_id lowercased>__umn`.

**Every one of these exceeds the corpus median shift.** The records being written off were the ones most in need of correction.

---

## Twenty worked examples, spanning the shift range 🟢

Evenly sampled across the sorted shift distribution. Grids present.

| site_id | record_id | source_id | stored lon, lat | corrected lon, lat | shift (m) |
|---|---|---|---|---|---|
| `site__doi-org-10-5066-p96mmrfd__ib001__umn` | `IB001` | `doi.org/10.5066/P96MMRFD` | −141.1849, 59.8236 | −141.186614, 59.823209 | **105.6** ← min |
| `site__doi-org-10-5066-p96mmrfd__ju242__umn` | `JU242` | `doi.org/10.5066/P96MMRFD` | −134.5995, 58.1418 | −134.601277, 58.141467 | 111.1 |
| `site__doi-org-10-5066-p96mmrfd__pe055__umn` | `PE055` | `doi.org/10.5066/P96MMRFD` | −133.1150, 56.2620 | −133.116710, 56.261641 | 113.3 |
| `site__doi-org-10-5066-p96mmrfd__cr120__umn` | `CR120` | `doi.org/10.5066/P96MMRFD` | −132.5928, 55.3519 | −132.594527, 55.351540 | 114.9 |
| `site__doi-org-10-5066-p96mmrfd__ea044__umn` | `EA044` | `doi.org/10.5066/P96MMRFD` | −142.3136, 64.5348 | −142.315916, 64.534461 | 117.4 |
| `site__doi-org-10-5066-p96mmrfd__mh323__umn` | `MH323` | `doi.org/10.5066/P96MMRFD` | −144.2332, 63.2891 | −144.235450, 63.288724 | 120.4 |
| `site__doi-org-10-5066-p96mmrfd__mc022__umn` | `MC022` | `doi.org/10.5066/P96MMRFD` | −143.9861, 61.7307 | −143.988197, 61.730237 | 122.3 |
| `site__doi-org-10-5066-p96mmrfd__mh053__umn` | `MH053` | `doi.org/10.5066/P96MMRFD` | −146.8284, 63.2472 | −146.830669, 63.246761 | 124.1 |
| `site__doi-org-10-5066-p96mmrfd__va123__umn` | `VA123` | `doi.org/10.5066/P96MMRFD` | −146.6242, 61.2033 | −146.626252, 61.202779 | 124.7 |
| `site__doi-org-10-5066-p96mmrfd__cl013__umn` | `CL013` | `doi.org/10.5066/P96MMRFD` | −152.0000, 68.3000 | −152.002820, 68.299567 | 126.0 |
| `site__doi-org-10-5066-p96mmrfd__mm082__umn` | `MM082` | `doi.org/10.5066/P96MMRFD` | −150.9127, 63.5591 | −150.914988, 63.558595 | 126.9 |
| `site__doi-org-10-5066-p96mmrfd__sr091__umn` | `SR091` | `doi.org/10.5066/P96MMRFD` | −147.9885, 60.9689 | −147.990550, 60.968326 | 128.1 |
| `site__doi-org-10-5066-p96mmrfd__an019__umn` | `AN019` | `doi.org/10.5066/P96MMRFD` | −149.3800, 61.7856 | −149.382216, 61.785073 | 130.9 |
| `site__doi-org-10-5066-p96mmrfd__hw028__umn` | `HW028` | `doi.org/10.5066/P96MMRFD` | −156.9477, 68.6198 | −156.950683, 68.619294 | 133.9 |
| `site__doi-org-10-5066-p96mmrfd__ar047__umn` | `AR047` | `doi.org/10.5066/P96MMRFD` | −158.2027, 67.5595 | −158.205548, 67.558943 | 136.3 |
| `site__doi-org-10-5066-p96mmrfd__ca027__umn` | `CA027` | `doi.org/10.5066/P96MMRFD` | −161.0600, 65.5400 | −161.062656, 65.539331 | 143.6 |
| `site__doi-org-10-5066-p96mmrfd__sm043__umn` | `SM043` | `doi.org/10.5066/P96MMRFD` | −157.6614, 61.5431 | −157.663763, 61.542401 | 147.9 |
| `site__doi-org-10-5066-p96mmrfd__di013__umn` | `DI013` | `doi.org/10.5066/P96MMRFD` | −158.5350, 59.2800 | −158.537200, 59.279258 | 150.2 |
| `site__doi-org-10-5066-p96mmrfd__sb026__umn` | `SB026` | `doi.org/10.5066/P96MMRFD` | −159.3400, 55.9400 | −159.341995, 55.939202 | 153.0 |
| `site__doi-org-10-5066-p96mmrfd__at001__umn` | `AT001` | `doi.org/10.5066/P96MMRFD` | **172.8200**, 52.8500 | 172.816973, 52.848345 | **274.8** ← max |

`AT001` sits at **positive longitude** — the far western Aleutians, across the 180th meridian. It transforms correctly and lands back in Alaska; the antimeridian is not a problem for the fix. 🟢

---

## Population summary

| | Count | Grain | Tag |
|---|---|---|---|
| NAD27 raw records | **7,720** | raw record | 🟢 |
| source / creator / confidence | 1 / 1 / **1.0** | raw record | 🟢 |
| distinct merged entities | **7,218** | merged entity | 🟢 |
| merged entities exposing a CRS | **0 of 10** | merged entity | 🟢 |
| records correctable, grid present | **7,720 (100 %)** | raw record | 🟢 |
| records correctable, grid absent | 7,696 (99.7 %) | raw record | 🟢 |
| shift min / median / max | 105.6 / **126.5** / 274.8 m | raw record | 🟢 |
| convergence, all pairs | **174.8 → 101.4 m**, 2,279 pairs / 1,470 entities | merged entity | 🟢 |

---

## The caveat that must reach the proposal

> **The environment that runs the fix must have the PROJ Alaska grid (`us_noaa_alaska.tif`) available.** Without it, 24 records silently stay put — and they are the 24 *most* displaced in the corpus — while the other 7,696 are corrected by a **12 m** approximation instead of a **5 m** one. PROJ reports no error either way; the absent-grid path declares accuracy `−1.0` and carries on.

Verify grid availability in CI before trusting any corrected output. 🟢
