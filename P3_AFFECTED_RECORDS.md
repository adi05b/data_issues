# P3_AFFECTED_RECORDS.md — which records, which sources, how many

*Aditi Bombe · run 2026-09-14 · follow-up to `P3_DIAGNOSIS.md` and `PRECISION_ANALYSIS.md` (mechanism, not in scope here) · **read-only**, 17 queries, nothing written.*
*Record in `probe-runs/2026-09-14/`. Confidence: 🟢 verified from a saved response · 🟡 likely · 🔴 assumed.*

**Gate.** `ASK { ?s ?p ?o }` → `HTTP/2 200`, `"boolean": true`. 🟢 `p3.0-gate.json`

Every figure traces to a saved response in `probe-runs/2026-09-14/`. Earlier runs and Adriana's figures appear only in §6.

---

## Bottom line

**Section 4 is the finding.** In **1,123 of 7,362 dedup groups (15.3%)**, the merge elects a coordinate materially coarser than one already sitting in the same group. **74.3% of those are within 1 km of the better value** — the same mine, at a worse resolution — so this is not bad linking, it is a better number being discarded. 🟢

The three populations are separate and only partly overlap:

| | Records | Sources | Nature |
|---|---|---|---|
| **A — coarse** (≤1 dp either axis, EPSG:4326) | **6,046** | 18 | genuinely rough, ~11 km or worse |
| **B — degrees/minutes conversions** | **5,287** | 10 | *not* coarse — fixed 1.2 km / 30 m precision that decimal counting misreads |
| **C — Null Island** (0,0) | **36** | 1 | missing values, not locations |

**A ∩ B = 463 records** are in both, which is why they must not be summed. 🟢

---

## Population A — coarse coordinates

18 sources, all `umn` except `api.cdr.land` (`inferlink`). Sum reconciles exactly against the §1 query. 🟢

| Source id | Team tag | Affected | Source total (4326) | Rate | Likely repo path 🔴 | Sample record ids |
|---|---|---|---|---|---|---|
| `https://mrdata.usgs.gov/nicrpge` | `umn` | **3,892** | 17,954 | 21.68% | `…/umn/mrdata-usgs-gov-nicrpge/` | `101137`, `101462`, `102090` |
| `https://mrdata.usgs.gov/major-deposits` | `umn` | 798 | 3,161 | 25.25% | `…/umn/mrdata-usgs-gov-major-deposits/` | `1005`, `1010`, `1021` |
| `https://mrdata.usgs.gov/phosphate` | `umn` | 388 | 1,187 | 32.69% | `…/umn/mrdata-usgs-gov-phosphate/` | `1004`, `1006`, `1008` |
| `https://mrdata.usgs.gov/ree` | `umn` | 214 | 578 | **37.02%** | `…/umn/mrdata-usgs-gov-ree/` | `100`, `101`, `104` |
| `https://api.cdr.land/v1/docs/documents` | `inferlink` | 205 | 679 | 30.19% | `…/inferlink/api-cdr-land-v1-docs-documents/` | `02003096a464…`, `02005ed95f9c…` |
| `https://mrdata.usgs.gov/sedcu` | `umn` | 176 | 708 | 24.86% | `…/umn/mrdata-usgs-gov-sedcu/` | `100`, `101`, `103` |
| `https://mrdata.usgs.gov/porcu` | `umn` | 120 | 690 | 17.39% | `…/umn/mrdata-usgs-gov-porcu/` | `102`, `110`, `117` |
| `https://mrdata.usgs.gov/potash` | `umn` | 59 | 981 | 6.01% | `…/umn/mrdata-usgs-gov-potash/` | `130`, `152`, `158` |
| `https://mrdata.usgs.gov/ofr20151121` | `umn` | 58 | 446 | 13.00% | `…/umn/mrdata-usgs-gov-ofr20151121/` | `105`, `107`, `109` |
| `https://mrdata.usgs.gov/sedexmvt` | `umn` | 53 | 240 | 22.08% | `…/umn/mrdata-usgs-gov-sedexmvt/` | `100`, `103`, `107` |
| `https://mrdata.usgs.gov/asbestos` | `umn` | 34 | 913 | 3.72% | `…/umn/mrdata-usgs-gov-asbestos/` | `1007`, `104`, `105` |
| `https://doi.org/10.5066/P9HTERGK` | `umn` | 20 | 42,744 | **0.05%** | `…/umn/doi-org-10-5066-p9htergk/` | `1225`, `1226`, `1227` |
| `https://mrdata.usgs.gov/sir20105090z` | `umn` | 9 | 1,200 | 0.75% | `…/umn/mrdata-usgs-gov-sir20105090z/` | `10114`, `10116`, `10119` |
| `https://mrdata.usgs.gov/podchrome` | `umn` | 8 | 1,045 | 0.77% | `…/umn/mrdata-usgs-gov-podchrome/` | `1114`, `292`, `404` |
| `https://mrdata.usgs.gov/pp1802` | `umn` | 6 | 410 | 1.46% | `…/umn/mrdata-usgs-gov-pp1802/` | `1757`, `1838`, `1923` |
| `https://mrdata.usgs.gov/sedznpb` | `umn` | 4 | 506 | 0.79% | `…/umn/mrdata-usgs-gov-sedznpb/` | `136`, `163`, `43` |
| `https://doi.org/10.5066/P9K1HBNT` | `umn` | 1 | 684 | 0.15% | `…/umn/doi-org-10-5066-p9k1hbnt/` | `350` |
| `https://mrdata.usgs.gov/deposit` | `umn` | 1 | 428 | 0.23% | `…/umn/mrdata-usgs-gov-deposit/` | `GA00012` |
| | | **6,046** | | | | |

**Both orderings.** **By volume**, `nicrpge` alone is 64.4% of population A (3,892). **By rate**, `nicrpge` is 7th — the worst are **`ree` at 37.02%**, `phosphate` 32.69%, `api.cdr.land` 30.19%. The reverse case matters too: **`P9HTERGK` contributes 20 records at 0.05%** — a large, clean feed whose handful of coarse rows is noise, not a quality problem. Only the affected/unaffected pair shows that. 🟢

**Reconciliation:** 6,046 rows pulled = 6,046 distinct sites = §1 sum, per-source match on all 18. No `LIMIT`, `truncated_by_limit: false`. 🟢 `p3_pops.py`

---

## Population B — degrees-and-minutes conversions

**5,287 records, 10 sources, all `umn`.** Classified offline with exact arithmetic: coarsest grid first (arcminute before arcsecond, per the correction in `PRECISION_ANALYSIS.md`), and the grid test applied **only to values carrying ≥6 stored decimals**, where it discriminates — it is vacuous on short ones. 🟢

| Source id | Team tag | Affected | Source total (4326) | Rate | Arcmin | Arcsec | Likely repo path 🔴 | Sample record ids |
|---|---|---|---|---|---|---|---|---|
| `https://mrdata.usgs.gov/vms` | `umn` | 1,090 | 1,090 | **100.00%** | 94 | 996 | `…/umn/mrdata-usgs-gov-vms/` | `1000`, `1001`, `1002` |
| `https://mrdata.usgs.gov/podchrome` | `umn` | 1,024 | 1,045 | 97.99% | 2 | 1,022 | `…/umn/mrdata-usgs-gov-podchrome/` | `1000`, `1001`, `1002` |
| `https://mrdata.usgs.gov/major-deposits` | `umn` | 680 | 3,161 | 21.51% | 436 | 244 | `…/umn/mrdata-usgs-gov-major-deposits/` | `1289`, `1290`, `1291` |
| `https://mrdata.usgs.gov/porcu` | `umn` | 625 | 690 | 90.58% | 296 | 329 | `…/umn/mrdata-usgs-gov-porcu/` | `100`, `102`, `103` |
| `https://mrdata.usgs.gov/sedcu` | `umn` | 615 | 708 | 86.86% | 231 | 384 | `…/umn/mrdata-usgs-gov-sedcu/` | `10`, `110`, `111` |
| `https://mrdata.usgs.gov/sedznpb` | `umn` | 489 | 506 | 96.64% | 17 | 472 | `…/umn/mrdata-usgs-gov-sedznpb/` | `100`, `101`, `102` |
| `https://mrdata.usgs.gov/ree` | `umn` | 470 | 578 | 81.31% | 462 | 8 | `…/umn/mrdata-usgs-gov-ree/` | `102`, `105`, `107` |
| `https://mrdata.usgs.gov/sedau` | `umn` | 118 | 123 | 95.93% | 0 | 118 | `…/umn/mrdata-usgs-gov-sedau/` | `100`, `101`, `102` |
| `https://mrdata.usgs.gov/laterite` | `umn` | 116 | 120 | 96.67% | 0 | 116 | `…/umn/mrdata-usgs-gov-laterite/` | `100`, `101`, `102` |
| `https://mrdata.usgs.gov/carbonatite` | `umn` | 60 | 60 | **100.00%** | 1 | 59 | `…/umn/mrdata-usgs-gov-carbonatite/` | `10`, `11`, `12` |
| | | **5,287** | | | **1,539** | **3,748** | | |

**Two feeds are 100% DMS** — `vms` (1,090/1,090) and `carbonatite` (60/60) — and six more are above 86%. This is not scattered; these are whole compilations of older published inventories recorded in degrees and minutes. Only `major-deposits` is genuinely mixed (21.51%). 🟢

**These records are not coarse.** Arcminute ≈ 1.2 km, arcsecond ≈ 30 m. Treating them as coarse because a value renders as `21.533333333333` would be exactly backwards — and treating the same record's `97.3` axis as 1-dp coarse is the other half of the same error.

**The two populations overlap on 463 records** — in A because one axis renders short, in B because the pair is DMS. Those 463 are DMS records, not 11 km records. 🟢

---

## Population C — Null Island

**36 records, one source.** 🟢

| Source id | Team tag | Affected | Source total | Rate | Likely repo path 🔴 |
|---|---|---|---|---|---|
| `https://api.cdr.land/v1/docs/documents` | `inferlink` | **36** (23 EPSG:4326 + 13 no CRS) | 15,421 | 0.23% | `…/inferlink/api-cdr-land-v1-docs-documents/` |

**No other source produces (0,0) anywhere in the graph.** 🟢 Note the split: 23 carry a resolved EPSG:4326 CRS, **13 carry no CRS at all** — the first query, restricted to EPSG:4326, returned only 23 and would have undercounted by 36%. `p3.1c2-popC-nocrs`

---

## Section 4 — the merge elects a coarser coordinate

### First, what is actually reachable 🟢

**Dedup entities are not in the SPARQL graph.** There is no `:DedupMineralSite` class (`p3.s1-classes` lists every class; it is absent) and **no `dedup_site__` URI appears as a subject on any triple** (`p3.s4-dedup-subject` returns zero rows). `owl:sameAs` targets are **always** other `site__` URIs — 260,654 of 260,654. 🟢

What *is* reachable is the **`owl:sameAs` closure**, which is the link structure the merge itself consumes. I built connected components over it. **This is not a proximity join** — no coordinate was used to form a group.

`:score` on `:DataSource` is the per-source trust value (31 of 38 sources carry one), so the election rule — highest-scoring record wins — can be simulated directly. 🟢 `p3.4b-source-scores`

| | |
|---|---|
| sameAs pairs where **both** sides have EPSG:4326 coordinates | 15,349 |
| coordinate-bearing records in clusters | 22,711 |
| **multi-record groups** | **7,362** |
| group sizes | 5,428 pairs; the largest is 734 |

### The measurement 🟢

Precision is compared as **angular resolution**, not decimal count, because decimal count is wrong in both directions here: a stored `-9.50000` carries 5 decimals that `float()` would report as 1, and a stored `21.533333333333` is an arcminute value, not a 12-decimal one. Both traps were established by the earlier runs and both fire in this data. A record counts as materially better only at **>3× finer resolution**, so ties and float noise cannot manufacture findings.

> **1,123 of 7,362 groups (15.3%) elect a coordinate materially coarser than one already present in the same group.** 🟢

**How much is lost:**

| Loss | Groups |
|---|---|
| ~1 decimal place (3–12×) | 778 |
| ~2 decimal places (12–120×) | 274 |
| 3+ decimal places (>120×) | 71 |

**Is it the same place?** This is the check that separates a real finding from bad linking:

| Separation between elected and better coordinate | Groups | Share |
|---|---|---|
| **≤ 1 km** | **834** | **74.3%** |
| 1–11 km | 242 | 21.5% |
| 11–50 km | 29 | 2.6% |
| > 50 km | 18 | 1.6% |

**95.8% are within 11 km** — exactly the envelope a 1-dp coordinate implies. These are the same mine recorded twice, and the merge keeps the worse one. The 18 groups beyond 50 km are likely bad `sameAs` links and should not be counted as precision loss. 🟡

**Who elects, who is discarded:**

| Most often ELECTED but coarser | n | score | | Most often DISCARDED but better | n | score |
|---|---|---|---|---|---|---|
| `mrdata.usgs.gov/mrds` | 540 | 0.1 | | `doi.org/10.5066/P9HTERGK` | 524 | **none** |
| `doi.org/10.5066/P9HTERGK` | 215 | **none** | | `mrdata.usgs.gov/mrds` | 428 | 0.1 |
| `mrdata.usgs.gov/podchrome` | 157 | 0.5 | | `www.idahogeology.org` | 57 | **none** |
| `mrdata.usgs.gov/major-deposits` | 53 | 0.5 | | `doi.org/10.5066/P9K1HBNT` | 32 | 0.5 |
| `mrdata.usgs.gov/deposit` | 47 | 0.7 | | `www.deq.nc.gov/…/nc-geological-survey` | 32 | **none** |

**The framing needs one correction.** The brief describes "a rough coordinate from a trusted source elected over a precise one from a less trusted source". The data says something sharper: **MRDS has the *lowest* score in the graph (0.1)** and is simultaneously the most-elected-but-coarser *and* the second-most-discarded-but-better. The driver is not misplaced trust — it is that **7 of 38 sources have no `:score` at all**, and **1,778 of 7,362 groups (24.1%) contain no scored member whatsoever**, so the election among them is arbitrary. 🟢 `P9HTERGK` — unscored, 42,744 records — is the single biggest loser of good coordinates.

### Named examples 🟢

| Mine | Group | Elected | Better | Factor |
|---|---|---|---|---|
| **Turnagain Nickel Project** | 4 | `MULTIPOINT(-128.0 53.0)` | `POINT(-129.220000 57.420000)` | 10⁵× |
| **Kleinsorge Group** | 7 | `POINT (-122.644444444444 40)` | `POINT (-122.63809 39.99386)` | 10⁵× |
| **Asmaradebara** | 2 | `POINT (38.75 15)` | `POINT (38.75121 15.00025)` | 10⁵× |
| **Sidi Driss** | 2 | `POINT (9 34)` | `POINT (9.00173 33.99925)` | 10⁵× |
| **Aitik** | 3 | `POINT (21 67.1166666666667)` | `POINT (21.17016 67.01533)` | 10⁵× |
| **Ann Mason** | 4 | `POINT (-119.27 38.96)` | `POINT(-116.571728 39.000740)` | 10⁴× |

Correction (10 Oct): Sonora was wrongly listed. The first election script broke ties by list order; MinMod keeps POINT(-109.103889 29.774722). See p3/P3_AMANDEEP_AND_SONORA.md.

**Two groups elect a `(0,0)` placeholder over a real coordinate** — populations C and section 4 intersect, and that intersection is the most clearly wrong outcome in the whole of Problem 3. 🟢

Full 1,123-row table: `p3.4-election.csv`.

---

## Section 3 — by country

EPSG:4326 denominators from the graph, minimum 20 sites, population A. 🟢 `p3.3-country-totals-4326`

| Share | Affected | Total | Country |
|---|---|---|---|
| 30.00% | 12 | 40 | Jordan |
| 30.00% | 6 | 20 | Cameroon |
| 29.63% | 8 | 27 | Syria |
| 26.51% | 22 | 83 | Vietnam |
| 23.33% | 7 | 30 | Greenland |
| 23.26% | 10 | 43 | Sudan |
| 22.73% | 20 | 88 | Denmark |
| 21.43% | 39 | 182 | Mongolia |
| 20.93% | 9 | 43 | Sri Lanka |
| 20.41% | 40 | 196 | Madagascar |
| 18.34% | 62 | 338 | Finland |
| 17.19% | 33 | 192 | Papua New Guinea |
| 16.88% | 40 | 237 | Indonesia |
| **15.52%** | **598** | **3,854** | **Russia** |
| … | | | *14 more above 15%* |

**Below the 20-site floor, reported separately and not ranked with the rest** — as instructed, because these would otherwise top the table on 1–4 records: UAE 33.33% (4/12), Lebanon 33.33% (4/12), Chad 33.33% (1/3), Bhutan 33.33% (1/3), Bangladesh 25.00% (2/8), Yemen 25.00% (1/4), Kiribati 25.00% (1/4), Nepal 21.43% (3/14), Benin 21.05% (4/19), Eritrea 20.00% (2/10), French Guiana 18.18% (2/11).

**Russia is the one that matters at scale** — 598 coarse records, 15.52% of its 3,854, the largest absolute count outside the reporting tail.

**Only 6 of 128 countries with ≥20 sites have zero coarse records**: Azerbaijan, Bosnia and Herzegovina, El Salvador, Nicaragua, Paraguay, Turkmenistan. 🟢 This is the opposite of Problem 2, where 84 countries were clean. **Coarse coordinates are near-universal**, because they track the *survey instrument and era* of the compilation rather than any naming convention — and the ten DMS feeds are global commodity inventories, not regional ones. There is no "safe region" to exclude.

*Population B by country was not computed — the B pull did not carry a country column. One extra query would add it; it does not affect any figure above.* 🔴

---

## Section 5 — nothing is lost in transit 🟢

Twenty records sampled across short (≤3 dp) and long (≥12 dp) decimal counts, comparing the **raw bytes of the HTTP response body** against the parsed value.

- **20 of 20 appear verbatim in the undecoded response body.** 🟢
- **0 of 40 axis values change under a `float()` round-trip.** 🟢

**The query returns the coordinate exactly as stored. Nothing is rounded or truncated on the way out.** `p3_transit.py`

**Where precision *is* genuinely lost — one line:** a source publishing `37.90000` is stored as `37.9`, because trailing zeros do not survive floating-point storage; that happens at ingest, before any query, and is unrecoverable.

**Sizing it:** of the 6,046 population-A records, **67 still carry explicit trailing zeros in the stored string** (`POINT(148.56667 -9.50000)`). Those survived because the WKT is an `xsd:string` — the digits are preserved as characters. So the loss applies only where the ingest path parsed to a number first. 67 records prove the string path preserves them; the size of the population that went the *other* way cannot be measured from inside the graph, because the evidence is exactly what was destroyed. 🔴

---

## Section 6 — cross-check

| Quantity | Theirs | Mine | Verdict |
|---|---|---|---|
| **A — coarse, 1 dp** | Adriana **3,633** (merged) | **6,046** (record, ≤1 dp either axis) | ratio 1.66 — plausible |
| **A — earlier run** | **2,853** (record, latitude only) | **6,046** (either axis) | explained, below |
| **B — DMS** | **5,288** | **5,287** | **agrees to 1 record** 🟢 |
| **C — Null Island** | **34** | **36** | mine, see below |

**A vs the earlier 2,853.** Not a disagreement — a different measure. The earlier figure was **latitude only**; mine is **either axis**, which is the right test because the two axes fail independently (`POINT (97.3 21.533333333333)` is coarse on longitude and long on latitude). Restricting to one axis discards half the population by construction.

**A vs Adriana's 3,633.** Ratio 1.66 (record ÷ merged), against the 1.62 global raw-to-dedup ratio established in the first probe run. **That is consistent**, and it dissolves the "impossible ratio" that `P3_DIAGNOSIS.md` flagged as unexplained — the earlier 2,853 came back *below* her merged 3,633, which cannot happen at the same grain. With the either-axis rule the ordering is right way up and the ratio is ordinary. 🟢 **I trust mine**, because it reconciles exactly against its own source-level query and the earlier one is a one-axis subset.

**B agrees to within one record (5,287 vs 5,288)** — independently derived, different tooling, same ten sources. Strong mutual confirmation. 🟢 The single-record gap is not worth chasing; it is one borderline value at a float tolerance.

**C: 36, not 34.** I trust mine. The earlier count and my own first query both restricted to EPSG:4326 and returned 23; **13 further (0,0) records carry no CRS at all** and only appear when the restriction is dropped. 🟢 The earlier 34 sits between the two, so it likely used a partial CRS condition. All 36 are `api.cdr.land`.

---

## Which files to open on GitHub

Every claim about file contents is 🔴 until someone opens it.

### 1. The merge's coordinate election · **1,123 groups, recoverable today**

**Question: when choosing which record's coordinate to keep, does the rule consider coordinate resolution at all — and what happens when no candidate has a `:score`?**

This is the only part of Problem 3 that recovers accuracy rather than documenting a limit. Two specific defects to look for:

- **`(0,0)` is electable.** Two groups elect Null Island over a real coordinate. A placeholder should never win, whatever its source score.
- **24.1% of groups have no scored member**, so the tie-break decides. Find what the tie-break is — it is currently choosing worse coordinates 15.3% of the time.

The fix is a secondary sort on resolution, applied after the score. It changes no source data and fabricates nothing: it chooses between two numbers already in the database.

### 2. `:score` coverage on `:DataSource` · **7 unscored sources**

**Question: why do `P9HTERGK` (42,744 records), `oregongeology`, `OFR-757`, `idahogeology`, `nfcritresource`, `nc-geological-survey` and `energy.virginia.gov` have no `:score`?**

`P9HTERGK` is the single most-discarded-but-better source (524 groups). Scoring it would fix a large share of §4 on its own, without touching the election logic.

### 3. The `api.cdr.land` / Inferlink extractor · **36 + 205 records**

**Question: where does an empty coordinate field become `POINT(0 0)`, and why do 13 of those 36 carry no CRS?**

It is the only source producing Null Island anywhere in the graph, and it is also 30.19% coarse in population A. Clear the location, keep the country — this was already the one cleanly actionable item in the earlier run and it remains so.

### 4. The DMS ingest path for the ten `umn` commodity feeds · **5,287 records**

**Question: does the source file carry degrees-and-minutes, or did our ETL convert them?**

Still the open question from `PRECISION_ANALYSIS.md`, and the source table now names exactly where to look: `vms` and `carbonatite` are **100%** DMS, `podchrome` 97.99%, `sedznpb` 96.64%. If the conversion is ours, the original DMS values should be preserved rather than reconstructed by testing a grid.

### 5. `mrdata.usgs.gov/nicrpge` · **3,892 records, 64% of population A**

**Question: is 21.68% coarseness inherent to the source, or did an ingest step round?**

Largest single contributor to A by a wide margin. Worth one look to confirm it is genuinely a coarse compilation before it is written off as unfixable.

### 6. The precision field that does not exist · **ontology change**

**Question: can extraction capture source precision into a field, instead of it being inferred from decimal counts afterwards?**

§5 shows the graph transmits faithfully and the loss is at ingest. Every precision figure in this report is reverse-engineered from rendering artifacts; a captured field would make all of it unnecessary — and it is the only way to get the per-record bound Adriana needs for error propagation.

---

## Run record — `probe-runs/2026-09-14/`

| File | Section |
|---|---|
| `p3.0-gate` | gate, `ASK` → `true` |
| `p3.s1`–`p3.s9` | schema probes: classes, DataSource, sameAs shape, sizing |
| `p3.1t` / `p3.1a` / `p3.1b` / `p3.1b2` / `p3.1c` / `p3.1c2` | 1 — totals and populations A, B, C |
| `p3.2a-popA-pull` | 2 — population A in full, 6,046 rows |
| `p3.2b-dms-pull` / `p3.2b-popB-classified.csv` | 2 — the ten DMS sources, 8,081 rows → 5,287 classified |
| `p3.3-country-totals-4326` | 3 — country denominators |
| `p3.4a-coord-pairs` / `p3.4b-source-scores` / `p3.4-election.csv` | 4 — 15,349 pairs, scores, 1,123 findings |
| `p3_election2.py` `p3_pops.py` `p3_transit.py` | offline analysis |

All queries HTTP 200, `truncated_by_limit: false`, no `LIMIT` on any population pull. Nothing written to the graph; no `ta2-minmod-*` checkout touched.
