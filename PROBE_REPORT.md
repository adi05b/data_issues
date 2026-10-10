# PROBE_REPORT.md — MinMod structural probe, step 1 of 4

*Aditi Bombe · run 2026-09-02 · endpoint `https://minmod.isi.edu/sparql` (Apache Jena Fuseki) · **read-only**, 39 queries, nothing written*

Confidence: 🟢 verified from a saved response · 🟡 likely · 🔴 assumed.
Every figure below traces to a file in `probe-runs/2026-09-02/`. Grain is labelled **raw** (SPARQL, 679,781 records) or **dedup** (Adriana's Postgres figures, 419,099 entities) on every count.

---

## Bottom Line

**Problem 1 is not what the ticket says it is, and the fix Adriana proposed would corrupt 31,108 correct records.** 🟢

Of the **31,109 raw records** with latitude outside [−90, 90], **31,108 are correctly-stored coordinates in a projected CRS** — 23,316 in EPSG:2994 (Oregon Lambert) and 7,792 in EPSG:26912 (UTM zone 12N). Their `:crs` is populated and correct. They are out of [−90, 90] because **metres and feet are not degrees**, not because anything is wrong with them. **Exactly one record in the entire graph is a genuine lat/lon transposition.** The brief said "most look like lat/lon flips"; the graph says one does.

The other two problems are real, tractable, and largely as described — with one important correction each:

- **Problem 2 (5,858 dedup / 6,156 raw state↔country conflicts)** is confirmed, the join is verified correct, and every root cause the master plan predicted from the vocabulary CSVs is confirmed against the live graph. New: **matcher confidence is a usable triage signal** — 58.7% of conflicts sit below 0.9 confidence versus 2.5% of all candidates, a ~23× enrichment.
- **Problem 3** is confirmed as informational, but **the probe query does not measure what Adriana's number measures** — raw comes back *lower* than dedup on two of three sub-counts, which is impossible at the same grain. Her counting rule needs to be asked for before this is reported as a source table.

Two of the nine planned probes were **silently broken**. Probe 1a returned **HTTP 200 with zero rows and no error** because it queries a predicate (`:name`) that does not exist in the graph. That is the exact failure mode this probe run existed to catch, and it caught it on the first query.

---

## What

### The endpoint

`https://minmod.isi.edu/sparql`, POST, `Content-Type: application/sparql-query`, **no authentication**. 🟢 The dashboard at `/dashboard/sparqlsearch` is a Plotly Dash UI that runs queries server-side; the endpoint is not referenced in its HTML or bundles and had to be found by direct probing. Server is Apache Jena Fuseki (`fuseki-request-id` header); **the version is not exposed** 🔴, so version-dependent behaviour was established empirically instead (see the trap table).

### Four schema facts that break the plan's queries

Full detail in `DATA_SHAPE.md` §0. In short:

1. **There is no `:name` predicate.** The site name is `rdfs:label`. `:name` has **zero** triples. 🟢
2. **The WKT datatype is `xsd:string`, not `geo:wktLiteral`.** 🟢
3. **The United States is `Q1235`, not `Q1233`.** 🟢
4. **`:crs` is populated on 99.72% of location records** — it is not the optional field the plan treats it as, and it is the single most load-bearing field in Problem 1. 🟢

And one correction in the safe direction: **candidate lists are singletons in practice.** 450,570 of 451,527 sites carry exactly one country candidate; 2 carry two. Row multiplication affects **33 sites total**. The plan's central methodological worry is unfounded. 🟢

### Problem 1 — latitude out of range

**Raw total: 31,109 sites.** 🟢 (`1b`, cross-checked by `1e`; the two agree exactly.)

**Split by CRS** (`1b`) 🟢 — and note there is **no null-CRS bucket at all**; every single out-of-range record carries a fully resolved CRS:

| CRS | Raw sites | Hypothesis | Correct fix |
|---|---|---|---|
| **EPSG:2994** (Oregon Lambert) | **23,316** | **H2 projected** | reproject |
| **EPSG:26912** (UTM 12N) | **7,792** | **H2 projected** | reproject |
| EPSG:4326 (WGS 84) | **1** | **H1 flip** | swap |
| *(no CRS)* | **0** | — | — |

**Magnitude histogram** (`1e`, the new probe) 🟢 — this is the population evidence that 30 sampled rows could not give:

| Bucket | Raw sites | Meaning |
|---|---|---|
| **A: 90 < \|lat\| ≤ 180** | **1** | the transposition signature — a longitude in latitude's slot can only reach 180 |
| B: 180–10³ | 0 | — |
| C: 10³–10⁵ | 20 | Oregon Lambert, near the projection's southern edge |
| **D: 10⁵–10⁷** | **31,088** | **projected metres/feet** |
| E: >10⁷ | 0 | — |

**Bucket A contains exactly one record**, and it is Adriana's own third example:

```
site__doi-org-10-5382-econgeo-4950__tagaung-taung__usc
POINT(23.63453 96.16317)   CRS EPSG:4326   observed country "Myanmar"
```
Latitude 96.16 > 90; swapped to (96.16317, 23.63453) it lands in Myanmar — **and five sibling records for the same place independently sit at lon ≈ 96.1, lat ≈ 23.5** (`1a-alt-tagaung`), corroborating the swap. 🟢 This is a genuine H1 flip and the only one.

**Her flagship example is not a flip.** `1a-alt-harts` 🟢 returns three raw records for Harts Draw:

| Record | WKT | CRS |
|---|---|---|
| `mrds__10228202` | `POINT (-109.4878899999999931 37.9338899999999981)` | EPSG:4326 — **already correct, in range** |
| `mrds__10078772` | `POINT (-109.4879099999999994 37.9338800000000020)` | EPSG:4326 — **already correct, in range** |
| `doi-org-10-34191-ofr-757__0` | **`POINT (632887 4199554)`** | **EPSG:26912** |

The out-of-range record is UTM 12N easting/northing in metres. Reprojecting it lands on ≈ (−109.49, 37.93) — **the value the two MRDS siblings already hold** 🟡 *(arithmetic not run; the agreement to 2 dp is inferred from the sibling records, and `pyproj` should confirm it in step 3)*. Swapping it would produce latitude 4,199,554 — nonsense. **H2 confirmed on the flagship, H1 excluded.** 🟢

`1c` (30 rows) 🟢 returned **30 of 30 from oregongeology.org in EPSG:2994** and was **truncated by its `LIMIT 30`** — it is one page of one source, not a sample of the population. Classification of all 30: **H2, unanimously.** On none of the 30 is `|lon| ≤ 90`, so **no row is flip-consistent**; H1, H3 and H4 are excluded for all 30. `?country_obs` = "United States" and `?state_obs` = "Oregon" are bound on every row, so H4 is falsifiable — and falsified. Decimal-place comparison is not diagnostic here because both values are projected coordinates, not degrees.

**Concentration is total, not partial:** EPSG:2994's 23,316 records are **100.0% of oregongeology.org's 23,316 sites**, and EPSG:26912's 7,792 are **99.99% of OFR-757's 7,793**. 🟢 This is not scattered corruption — it is two entire source feeds stored in their native projection, exactly as they arrived.

### Problem 2 — state's country ≠ normalized country

**The open question is answered:** `:country` on a state entity is a **plain literal** bare Q-id (`"Q1177"`), while `:normalized_uri` is an **IRI**. 🟢 Raw bindings in `DATA_SHAPE.md` §2. **Probe 2b's join is correct as written** and the script can reuse it.

**Raw total: 6,156 conflicting sites** (`2b-total`) vs Adriana's 5,858 dedup. 🟢 Raw > dedup ✓.

**The join reproduces her table** (`2b`) 🟢:

| Pair | Adriana (dedup) | This run (raw) | Ratio |
|---|---|---|---|
| Florida → Puerto Rico, country United States | 1,587 | **1,609** | 1.014 |
| La Paz → La Pampa (Argentina), country Bolivia | 531 | **586** | 1.104 |
| Potosí → Porto (Portugal), country Bolivia | — | 552 | — |
| Bolívar → Colombia, country Venezuela | — | 475 | — |
| Santa Cruz → Argentina, country Bolivia | — | 216 | — |
| Koror (Palau), country Bolivia | — | 191 | — |
| Garissa (Kenya), country India | — | 187 | — |
| Camuy (Puerto Rico), country Cuba | — | 158 | — |
| Tanga (Tanzania), country DR Congo | — | 112 | — |
| Saint Andrew → Barbados, country Jamaica | — | 87 | — |

Both cross-checkable pairs come back raw ≥ dedup with **consistent** ratios (1.01, 1.10). The join is sound. 🟢 *(Both ratios sit well below the global 1.62 — see the reconciliation table.)*

**Every root cause the master plan predicted from the vocabulary CSVs is confirmed live** (`2f-target-existence`) 🟢:

| Observed | Wrongly normalized to | Correct target | Exists live? | Class |
|---|---|---|---|---|
| Florida (US) | Q5307 → Puerto Rico | **Q6850 → United States** | ✅ | true tie (3 Floridas: PR/US/UY) |
| La Paz (Bolivia) | La Pampa → Argentina | **Q2453 La Paz Department** | ✅ | suffix |
| Potosi (Bolivia) | Porto → Portugal | **Q2456 Potosí Department** | ✅ | suffix + diacritic |
| Oruro (Bolivia) | Koror → Palau | **Q2454 Oruro Department** | ✅ | suffix |
| Santa Cruz (Bolivia) | Q2190 → Argentina | **Q2457 Santa Cruz Department** | ✅ | suffix + tie |
| Camaguey (Cuba) | Camuy → Puerto Rico | **Q2887 Camagüey Province** | ✅ | suffix + diacritic |
| Bolivar (Venezuela) | Bolívar → Colombia | **Q6958 Bolívar (Venezuela)** | ✅ | diacritic + tie |
| Saint Andrew (Jamaica) | Q2374 → Barbados | **Q3902 Saint Andrew (Jamaica)** | ✅ | true tie |
| **Orissa (India)** | Garissa → Kenya | **none — only `Odisha` (Q3657)** | ❌ | **vocabulary gap** |
| **Katanga (DR Congo)** | Tanga → Tanzania | **none — only `Haut-Katanga` etc.** | ❌ | **vocabulary gap** |

Note `La Paz Department` itself exists **three times** (Bolivia Q2453, El Salvador Q3132, Honduras Q3556) 🟢 — so suffix-stripping alone is not enough; **candidates must also be constrained to the already-normalized country**, exactly as the plan proposes.

`2c` (duplicate labels, truncated at `LIMIT 50`) 🟢 confirms ties are systemic, not anecdotal: `Central Province`, `Western Province`, `Eastern Province` each resolve to **five** different countries; `Florida` to three. It also surfaced something the plan did not predict: **`Zagreb` has 2 entities under a single country (Q1053)** — a duplicate entity in the vocabulary itself, not a tie. Worth a separate look.

**2d — the new confidence probe — returns an actionable answer.** 🟢 Confidence is **not** a constant, and it **is** discriminative:

| | conflicts | all state candidates | enrichment |
|---|---|---|---|
| confidence < 0.9 | **3,615 of 6,156 (58.7%)** | 10,732 of 421,592 (**2.5%**) | **~23×** |
| confidence ≥ 0.99 | 2,514 (40.8%) | 410,185 (97.3%) | — |

A confidence threshold at 0.9 would flag **3,615 of the 6,156 conflicts (58.7%)** inside a review queue of only **10,732 candidates (33.7% precision)**. That is a genuinely cheap partial win. But it is **not a complete fix**: it misses 2,541 conflicts, including the largest single bucket — **2,058 Florida→Q5307 rows at confidence 0.9999**, and 322 more at exactly 1.0. Four matchers appear (`UMN Matching System-ProcMinev2` dominant, plus `UMN Matching System v1`, `Inferlink Extraction v3`, `UMN Exact Match v1`), and **two different matchers produce two different wrong Floridas** — v1 → Q6920 (Uruguay) at confidence 1.0, ProcMinev2 → Q5307 (Puerto Rico) at 0.9999. 🟢

### Problem 3 — coordinate precision

**This is where the probe queries and Adriana's figures measure different things, and the report should not paper over it.**

**A category error in the query as written:** `3a` ranks `doi.org/10.34191/OFR-757` first with **7,792 rows at "0 dp"**. Those are the **UTM records** — `POINT (632887 4199554)`. Integers because they are *metres*, where 0 dp **is 1-metre precision**. Counting them as coarse is wrong. Re-run restricted to EPSG:4326 (`3a-alt-geographic-only`) 🟢:

| Source | ≤1 dp raw | Source total | % of source |
|---|---|---|---|
| `mrdata.usgs.gov/nicrpge` | **1,843** | 32,998 | 5.59% |
| `mrdata.usgs.gov/major-deposits` | 475 | 5,938 | 8.00% |
| `mrdata.usgs.gov/phosphate` | 246 | 2,790 | 8.82% |
| `mrdata.usgs.gov/ree` | 131 | 1,563 | 8.38% |
| `api.cdr.land/v1/docs/documents` | 131 | 15,421 | 0.85% |
| `mrdata.usgs.gov/sedcu` | 101 | 1,563 | 6.46% |
| `mrdata.usgs.gov/porcu` | 67 | 1,376 | 4.87% |
| `mrdata.usgs.gov/sedexmvt` | 32 | 480 | 6.67% |

**Concentrated, not diffuse** — `nicrpge` alone is 59% of the coarse rows. 🟢 But note the rate is a fairly flat 5–9% across most USGS feeds, so it looks like a shared upstream characteristic rather than one broken extractor. 🟡

**The counting rule does not reconcile.** Adriana: 3,633 dedup at 1 dp. Latitude-only at raw grain gives **2,853** — *lower* than dedup, which is impossible at the same grain and therefore **rules out "latitude only" as her rule**. 🟢 Variants (`3d-alt-precision-variants`):

| Counting rule | Raw | vs her 3,633 |
|---|---|---|
| latitude dp = 1 (what Probe 3a does) | 2,853 | **0.79 — impossible** |
| longitude dp = 1 | 3,081 | 0.85 — impossible |
| **either axis dp = 1** | **5,409** | **1.49 — plausible** |
| both axes ≤ 1 dp | 8,708 | 2.40 |

**"Either axis at exactly 1 dp" is the only tested rule that gives a plausible ratio.** 🟡 Her exact rule needs to be confirmed before a source table is published.

**(0,0) — Null Island** (`3b`) 🟢: **34 raw rows** (Adriana: 29 dedup, ratio 1.17 ✓), and the result is unusually clean:

- **All 34 come from a single source**, `api.cdr.land/v1/docs/documents` (the Inferlink extractor). No other source produces (0,0) anywhere in the graph.
- **29 of 34 carry a bound `?country_obs`** — Madagascar, Romania, Canada ×8, Spain ×3, Zimbabwe, Greenland, Mexico ×3, Côte d'Ivoire, Zambia ×2, Kazakhstan, DR Congo, Finland ×2, Turkey, Russia. These points are scattered across the planet; (0,0) is plainly a null placeholder, not a location.
- 5 carry no country either.
- Stored as `POINT(0 0)` ×27, `POINT(0.0 0.0)` ×6, and **`POINT(-0.0 0.0)`** ×1 (negative zero).

**This confirms the plan's call exactly: clear the location, keep the record and its country. Do not geocode.** 🟢 And because it is one extractor, the durable fix is in that extractor's null handling.

**Uneven precision** (`3c`, `3c-total`): **33,950 raw** vs Adriana's **93,673 dedup** — **raw is 0.36× dedup**, another impossible ratio. 🟢 The probe does not measure her figure.

The mechanism is also not what the plan hypothesised. The plan expects uneven precision to mean "the two axes came from different places". `3c-sample` 🟢 shows otherwise:

```
POINT (-145.59333 63.33)     lon 5 dp, lat 2 dp
POINT (-123.122 41.8218)     lon 3 dp, lat 4 dp
POINT (-136.4225 57.976)     lon 4 dp, lat 3 dp
```

These are **float64 shortest-round-trip serialisations with trailing zeros stripped** — `63.330` stores and prints as `63.33`. The two axes came from the same place; the *representation* lost the trailing digit. 🟡 **Decimal places in this graph are a property of float serialisation, not of measurement precision** — visible most starkly in the MRDS records, which store `-109.4878899999999931` (16 dp) for a value the source publishes at 5 dp. **Counting stored decimal places does not recover source precision.** That is a finding about the method, and it undercuts the premise of Probe 3a for every source that round-trips through a float.

Top uneven sources (`3c`, truncated at `LIMIT 20`): oregongeology 9,593; `doi.org/10.5066/P9HTERGK` 8,487; `nicrpge` 3,644; Virginia Energy 1,798. **Overlap with the ≤1 dp sources is partial** — `nicrpge` is in both, but oregongeology and P9HTERGK are not in the coarse list at all, and MRDS (70% of the graph) is absent from the uneven list entirely. So §5's question "do they share sources?" answers **partially — two different mechanisms**. 🟢

---

## Why It Matters

**A swap script would have been a data-loss event.** The plan's own decision rule reads: *"If Probe 1b shows every out-of-range row is EPSG:4326 or null → H1/H3 only; the script swaps."* The probe shows the **opposite** — 31,108 of 31,109 are projected. Had 1b not been run first, or had it been run without the CRS split, the natural reading of "24,818 latitude errors, most look like flips" leads directly to a swap that destroys two entire source feeds' coordinates. The `:crs` field that prevents this is populated on 99.7% of records and was assumed optional.

**The real defect in Problem 1 is the validator, not the data.** 31,108 records are correctly stored, correctly labelled with their CRS, and internally consistent. What is broken is a range check that reads latitude without reading `:crs`. That reframes the deliverable: the fix is not 31,108 coordinate rewrites, it is (a) a CRS-aware validation rule, and (b) a decision about whether the graph should *store* everything in EPSG:4326 — a normalisation question for Craig, not a correction task.

**Two of nine probes were silently wrong, and neither raised an error.** Probe 1a returned HTTP 200 and zero rows. Probe 3a returned a confident, well-formed ranking whose top entry is a category error. Both would have been reported as findings by anyone who did not pre-flight the schema. The pre-flight probes cost 10 queries and roughly 90 seconds, and they changed the conclusion of the entire exercise.

**Problem 3's premise needs revisiting before it is reported.** Adriana wants a precision figure so she can propagate error when comparing entities. But stored decimal places are float-serialisation artifacts, and no precision field exists anywhere in the schema. Handing her a source table built on decimal counting would give her a number that does not mean what she needs it to mean.

**Problem 2 is ready to proceed** and is the one problem where the plan's analysis survived contact with the graph intact.

---

## Reconciliation table

679,781 raw ÷ 419,099 dedup ≈ **1.62** is the expected expansion.

| Problem | Adriana's count (dedup) | This run (raw) | Ratio | Consistent with ~1.62? | Notes |
|---|---|---|---|---|---|
| **1 — latitude out of range** | 24,818 | **31,109** | **1.25** | **No — low** | Directionally right (raw > dedup) but well under 1.62. Consistent with the whole coordinate-bearing population, which expands at only 446,426 ÷ 400,447 = **1.115** — records *with* coordinates dedup far less than records without. The residual gap is plausibly the Oregon EPSG:2994 feed, whose 23,316 records may merge heavily with MRDS siblings for the same sites. 🟡 |
| **2 — state/country conflict** | 5,858 | **6,156** | **1.05** | **No — low** | Same direction, same explanation: conflict rows all carry a state *and* a country, so they are coordinate- and metadata-rich records that dedup aggressively. Per-pair ratios are internally **consistent** (Florida 1.014, La Paz 1.104), which is the real check that the join is right. 🟢 |
| **3 — ≤1 dp** | 3,633 @1dp + 232 @0dp | **2,853 @1dp** (lat-only, all CRS)<br>**2,638 @1dp** (lat-only, EPSG:4326) | **0.79 / 0.73** | **No — inverted** | **Raw < dedup is impossible at the same grain**, so the probe and her figure are not counting the same thing. "Either axis at exactly 1 dp" gives 5,409 raw = **1.49**, the only tested rule that is even possible. Her rule must be confirmed. 🟡 |
| *3b — (0,0)* | 29 | **34** | **1.17** | No — low | Consistent with the 1.115 coordinate-bearing expansion. ✓ |
| *3c — uneven precision* | 93,673 | **33,950** | **0.36** | **No — badly inverted** | Raw is *one third* of dedup. Strongly suggests dedup coordinates are **recomputed** (a mean over merged records), which would generate uneven decimal lengths that do not exist in any raw record. 🟡 Unresolved — see `OPEN_QUESTIONS.md`. |

**Reading the pattern:** no problem matches 1.62, and all three sit low, because 1.62 is the expansion of the *whole* graph — including the 228,254 sites with no location at all. Every one of these three problems is defined on records that have coordinates, and that subpopulation expands at **1.115**. Measured against 1.115 rather than 1.62, Problem 1 (1.25) and Problem 2 (1.05) both look ordinary; only Problem 3's inversions remain anomalous. 🟡

---

## Trap table — §6 failure modes, each explicitly tested

| Trap | Tested by | Observed? | What was found |
|---|---|---|---|
| **Silent zero from a failed cast** | `P0.5-cast-canary` | **No** 🟢 | All three casts bound, including scientific notation `1.23E5`. `xsd:double` works on this Fuseki build. Probe 1b's counts are trustworthy, and its "1 row for EPSG:4326" is a **real** answer, not a cast failure. |
| **Silent drop from a non-matching regex** | `P0.6-parse-coverage` + `P0.3-wkt-shapes` | **Yes, bounded** 🟢 | 217 of 446,426 rows (0.049%) are invisible to every probe: 215 `MULTIPOINT`, 1 misspelled `MULIPOINT`, 1 `NaN` latitude. Above the §11 95% floor, so the run continued. All counts are lower bounds by ≤217. The two independent methods agree exactly. |
| **Row multiplication from OPTIONAL joins** | `P0.7`, `P0.7b`, rows-per-site on `1a-alt` and `2a` | **Effectively no** 🟢 | 33 sites of 451,527 carry >1 candidate. Rows-per-site is **1.00** on every `1a-alt` and on `2a`. The three Harts Draw rows are **three distinct sites** from three sources, not one site multiplied. |
| **`LIMIT` mistaken for population** | `truncated_by_limit` in every meta block | **Yes** 🟢 | 6 probes hit their limit: `1c` (30/30), `2a` (20/20), `2b` (40/40), `2c` (50/50), `3c` (20/20), `3c-sample` (15/15). **`1c` is the dangerous one** — all 30 rows are one source, and the population picture came from `1e` and `1b` instead. Bare `COUNT` companions were run for `2b` (`2b-total`) and `3c` (`3c-total`). |
| **Timeout returning partial results** | elapsed time + row counts, plus a re-run of `P0.1-locationinfo` | **No** 🟢 | Slowest probe 11.4 s against a 300 s budget; nothing near §11's 10-minute rule. `P0.1-locationinfo` was run twice and returned identical bytes. No truncation header on any response. |
| **Raw-vs-dedup grain confusion** | every count labelled | **Managed** 🟢 | See the reconciliation table. Two of Problem 3's sub-counts come back raw < dedup, which is flagged as a finding rather than reported as agreement. |
| **Prefix drift** | `P0.1` predicate IRIs | **No** 🟢 | Every predicate IRI is under `https://minmod.isi.edu/ontology/` and resources under `https://minmod.isi.edu/resource/`, exactly as the plan assumes. The problem was never the namespace — it was `:name`, a **local name that does not exist** in the correct namespace. |

**One trap the plan did not list, and it fired:** *a predicate that does not exist produces zero rows, not an error.* Probe 1a, HTTP 200, empty. Worth adding to the checklist — it is the failure mode that a namespace check does not catch.

---

## How to Act

### Immediately, before anything else

1. **Do not write a coordinate-swap script.** The premise is wrong for 31,108 of 31,109 records. 🟢
2. **Fix the three broken probe queries** in the plan files before they are reused: `:name` → `rdfs:label` (1a, 1c, 3b), drop any `geo:wktLiteral` assumption, and use `Q1235` for the United States.

### Problem 1 — take to Craig as a scoping decision, not a fix

The queue does not split 50/50 as the plan anticipated; it splits **31,108 reproject / 1 swap**. Three things to decide:

- **Is the out-of-range check itself the bug?** A CRS-aware validation rule (only bound latitude when `:crs` is a geographic CRS) removes 31,108 of the 31,109 "errors" without touching a single record. Cheapest possible fix. 🟢
- **Should the graph normalise everything to EPSG:4326 on ingest?** That is a real improvement for downstream consumers — map view, FuseMine 10 km blocking — but it is an ETL change affecting two whole source feeds, not a data correction. `pyproj` from EPSG:2994 and EPSG:26912 handles it.
- **The one genuine flip** (`site__doi-org-10-5382-econgeo-4950__tagaung-taung__usc`) is the right step-3 dry run for the swap path — it is corroborated by five sibling records and it is the entire H1 population.
- **Propose the SHACL shape anyway**, but bound latitude *conditionally on a geographic CRS*. An unconditional bound would reject two valid source feeds.

Also raise: **Problem 1 is undercounted in a way this probe cannot measure.** A transposition where both magnitudes are under 90 stays in range and is invisible here. With H1's visible population now known to be exactly 1, the invisible population is the *only* remaining flip risk, and it needs the containment test the plan parks as Probe 1d.

### Problem 2 — proceed, this one is ready

- The join is verified; reuse `2b` in the script unchanged.
- **Recommend the matcher change, not row repoints.** Strip `Department`/`Province`/`Parish` suffixes, fold diacritics, and **constrain candidates to the already-normalized country** — the last is essential, since `La Paz Department` alone exists in three countries.
- **Add a confidence < 0.9 review gate now** as an independent cheap win: 58.7% of conflicts, 33.7% precision, ~23× enrichment over base rate. Say plainly that it is partial — it misses the 2,058-row Florida bucket sitting at 0.9999.
- **Two vocabulary aliases** (`Orissa` → Odisha Q3657, `Katanga` → the four successor provinces) as a separate PR. Confirmed live: no correct target exists today.
- **New:** look at `Zagreb` — 2 entities, 1 country. Possible duplicate entity in the vocabulary, unrelated to the matcher.
- Step-3 dry runs stay as planned: one Florida (tie class, repoint Q5307 → **Q6850**), one La Paz (suffix class, repoint → **Q2453**).

### Problem 3 — ask Adriana one question before building the table

- **Ask: what exactly did you count?** Latitude-only does not reproduce 3,633 at any grain. "Either axis at exactly 1 dp" (5,409 raw, ratio 1.49) is the only tested rule that is even arithmetically possible.
- **Report the source table CRS-aware.** OFR-757's 7,792 "0 dp" rows are metres and must not appear in a coarse-precision list.
- **Flag the deeper problem:** stored decimal places are float-serialisation artifacts, not measurement precision. Error propagation cannot be built on them. If Adriana needs a precision number, it has to be captured at extraction time into a field that **does not currently exist** in the schema — that is the real recommendation, and it is an ontology change.
- **(0,0) is a clean, closeable finding.** One extractor (`api.cdr.land`, Inferlink), 34 raw rows, 29 with a real observed country. Clear the location, keep the country, and fix the null handling in that extractor. This is the one part of Problem 3 that is genuinely actionable today. 🟢

### Blocked

**§9's upstream check could not be run** — no `ta2-minmod-data` or `ta2-minmod-kg` checkout exists on this machine, and nothing was cloned. Two questions therefore remain open that would otherwise have been settled here:

- *Does the source file already carry 1 dp, or did the ETL round it?* — the single question that decides between "record a precision field" and "fix the extractor". The float-serialisation finding above makes **"the ETL round-trips through a float and loses trailing digits"** the leading hypothesis 🟡, but it is not confirmed.
- *Do any SHACL shapes already bound latitude?* — unverified. 🔴

Both need the repos checked out. Say the word and I'll run them.

---
---

# ADDENDUM — run 2026-09-02 (later same day)

*31 further read-only queries + offline `pyproj` verification. Record in `probe-runs/2026-09-02-addendum/`. The 2026-09-02 findings above stand unless explicitly corrected here; corrections are marked **CORRECTION**.*

## Addendum bottom line

**The reprojection claim is now verified arithmetically, not circumstantially.** 🟢 Reprojecting the OFR-757 Harts Draw record from its declared EPSG:26912 lands **6.4 m and 7.3 m** from its two MRDS siblings — far inside the ~50 m confirmation threshold. Across 90 records pulled from the bounding-box extremes of both projected feeds, **89 land inside the observed state** under their declared CRS, and the single exception is 123 m outside a box whose edge *is* the state line. The claim that 31,108 records are correctly-stored projected coordinates upgrades from 🟢-on-circumstantial to 🟢-on-arithmetic.

**The declared CRS is trustworthy.** The foot/metre ambiguity is resolved and the graph is right: EPSG:2994 is `NAD83(HARN) / Oregon GIC Lambert (ft)` — **feet** — and under it 50 of 50 Oregon records land in Oregon. Under the metre sibling EPSG:2993 only 10 of 50 do. So the CRS-aware validation rule *would* have worked, and the larger worry raised in Part 4 — that the CRS field itself is wrong — is **excluded**. 🟢

**Two new headline numbers, both arguing for the matcher fix over row repoints:**

- A suffix-stripping + diacritic-folding matcher, constrained to the site's already-normalized country, resolves **5,145 of 6,134 conflicts (83.9%)** to the correct target — including every one of Adriana's ten examples that has a target. 🟢
- The same rule recovers **1,090 of 3,248 sites (33.6%)** in a population the first run did not count at all: state names that failed to normalize entirely. **6,235 sites fixed by one change.** 🟢

**CORRECTION to the first run's "Why It Matters":** the claim that projected coordinates prevent FuseMine-style clustering is **not supported by the evidence available**. Oregon's cross-source link rate (5.93%) is *above* the graph baseline (3.50%). Detail in §A2.1.

---

## A2.3 — Full CRS census, and the `crs.csv` gap 🟢

Every CRS in the graph, over all 451,527 `LocationInfo` nodes:

| Normalized CRS | Observed name | Nodes |
|---|---|---|
| EPSG:4326 | `EPSG:4326` | 403,549 |
| **EPSG:2994** | `EPSG:2994` | **23,316** |
| EPSG:4326 | *(no `:observed_name`)* | 7,869 |
| **EPSG:26912** | `EPSG:26912` | **7,792** |
| EPSG:4267 | `EPSG:4267` | 7,720 |
| *(no `:crs` at all)* | — | 1,280 |
| EPSG:4326 | `WGS84` | 1 |

Sums to 451,527 exactly. **Four distinct CRSs live: 4326, 4267, 26912, 2994.**

**The master plan's read of `crs.csv` is wrong in both directions:**

- **EPSG:3857** is listed in the plan's read of the CSV and appears **zero** times in the graph.
- **EPSG:2994** carries the single largest block of out-of-range records (23,316) and is **absent** from the plan's read.

So the vocabulary CSV as read is not a mirror of the deployed graph. **This puts a caveat on the master plan's whole "root causes already visible from the vocabulary before any query" section** — that section's Problem 2 conclusions happened to hold up under `2f-target-existence`, but the CRS half did not, and the method of reasoning from the CSVs without checking the graph is what produced the wrong CRS list. 🟢

Also worth noting: **no CRS candidate has an `:observed_name` without a `:normalized_uri`.** Every CRS string in the graph normalized successfully, including the single `WGS84`. The 1,280 nodes with no CRS have no candidate at all.

## A2.2 — The one OFR-757 record that isn't out of range 🟢

| Feed | CRS | Status | Sites |
|---|---|---|---|
| OFR-757 | EPSG:26912 | out_of_range | 7,792 |
| OFR-757 | *(none)* | **no_wkt** | **1** |
| oregongeology | EPSG:2994 | out_of_range | **23,316 (100.0%, exactly)** |

The odd record is `site__doi-org-10-34191-ofr-757__4563__umn` — "A&G", record_id 4563, United States / Utah, **`:location_info` present but no `:location`**. It is one of the 5,101 graph-wide LocationInfo nodes with no WKT.

**Benign.** It is not a mislabeled CRS and not a mirror image of Tagaung Taung — that possibility is excluded. 🟢 And oregongeology's 100.0% is exact, not rounded: a single result row, no second bucket.

## A2.1 — The FuseMine question — **CORRECTION** 🟢

The first run's "Why It Matters" asserted that projected coordinates leave records unable to cluster. Testing it changed the answer, and also changed what the test means.

**`owl:sameAs` is mostly not entity resolution.** It is directional and asymmetric — 260,698 triples, 198,132 distinct subjects, 260,698 distinct objects, and **260,696 of those objects never appear as a subject**. Classifying every pair:

| Pair type | Pairs | Share |
|---|---|---|
| **same `record_id`, same source** | **188,253** | **72.2%** |
| different `record_id`, same source | 52,008 | 19.9% |
| **different source** | **20,392** | **7.8%** |

**72% is one source record processed by two different teams** (`…__umn` ↔ `…__sri`) — a pipeline artifact, not a claim about the world. Only 7.8% are cross-source links, and those are the only part resembling what spatial blocking would produce.

The Harts Draw worked example shows it directly:

| Record | WKT | Linked to |
|---|---|---|
| `mrds__10228202__umn` | `POINT (-109.48789 37.93389)` | ← `mrds__10228202__sri` (**its own twin, same record_id**) |
| `mrds__10078772__umn` | `POINT (-109.48791 37.93388)` | ← `mrds__10078772__sri` (**its own twin**) |
| `ofr-757__0__umn` (UTM) | `POINT (632887 4199554)` | **nothing** |

The two MRDS records sit ~20 m apart and are plainly the same place — and they are **not linked to each other**. Whatever produces `owl:sameAs` here is not clustering on coordinates.

**Cross-source link rate** — the only FuseMine-relevant measure — over sites carrying a location:

| Source | Sites w/ location | Cross-source linked | Rate |
|---|---|---|---|
| mrdata.usgs.gov/mrds | 304,622 | 7,429 | 2.44% |
| doi.org/10.5066/P9HTERGK | 42,744 | 2,391 | 5.59% |
| **www.oregongeology.org (EPSG:2994)** | 23,316 | 1,382 | **5.93%** |
| mrdata.usgs.gov/nicrpge | 17,954 | 0 | 0.00% |
| energy.virginia.gov | 9,842 | 283 | 2.88% |
| **doi.org/10.34191/OFR-757 (EPSG:26912)** | 7,792 | 63 | **0.81%** |
| mrdata.usgs.gov/pp577 | 2,181 | 0 | 0.00% |
| **All sources** | **446,426** | **15,632** | **3.50%** |

**Oregon, the largest projected feed, links at nearly twice the graph baseline.** OFR-757 links poorly (0.81%), but so do two geographic feeds at exactly 0.00%. **The hypothesis is not supported.** 🟢

Two honest caveats: whether FuseMine writes `owl:sameAs` at all is **unverified** 🔴, and a 3.5% baseline is low enough that per-source differences are noisy. The right reading is *"no evidence of harm to linkage"*, not *"proven harmless"* — the mechanism argument for reading `:crs` stands on its own, independent of this test.

## A2.4 / A2.5 — The matcher-fix ROI 🟢

**A population the first run did not count.** `DATA_SHAPE.md` §4 recorded 224,586 candidates with an `:observed_name` and no `:normalized_uri`; that figure spans *all* candidate types. Restricted to states:

| Metric | Count |
|---|---|
| Sites whose state candidate never normalized | **3,245** |
| Distinct unmatched state names | **672** |
| Sites whose *country* candidate never normalized | 723 |

The top of that list is the same failure classes as the conflict set, wearing a different symptom: `Camaguey` 216, `Katanga` 148, `Newfoundland` 101, `Orissa` 91, `Neuquen` 62, `Hokkaido` 53, `Holguin` 49, `Goias` 34, `Para` 22. **`Camaguey` appears in both populations** — 216 sites failed to match at all, and a separate 158 sites matched wrongly to `Camuy` (Puerto Rico). One root cause, two symptoms.

**Offline test** (`match_roi.py`, over the full 5,084-label vocabulary): fold diacritics with `unicodedata` NFKD, strip a trailing `Department`/`Province`/`Parish`/`State`/`Region`/`Prefecture`/`Governorate`/`District`/`Oblast`/`County`/`Territory`/`Municipality`, then require a unique hit **within the site's already-normalized country**.

| Population | Sites | Recovered | Rate |
|---|---|---|---|
| **Conflicts** (wrongly matched) | 6,134 | **5,145** | **83.9%** |
| **Unmatched** (never matched) | 3,248 | **1,090** | **33.6%** |
| **Combined** | **9,382** | **6,235** | **66.5%** |

What it resolves in the conflict set — every one of Adriana's examples that has a target, to the right entity:

```
Florida       + Q1235 United States -> Florida            Q6850   1674 sites
La Paz        + Q1025 Bolivia       -> La Paz Department  Q2453    586
Potosi        + Q1025 Bolivia       -> Potosí Department  Q2456    553
Bolivar       + Q1241 Venezuela     -> Bolívar            Q6958    475
Santa Cruz    + Q1025 Bolivia       -> Santa Cruz Dept.   Q2457    220
Oruro         + Q1025 Bolivia       -> Oruro Department   Q2454    191
Camaguey      + Q1054 Cuba          -> Camagüey Province  Q2887    158
Saint Andrew  + Q1108 Jamaica       -> Saint Andrew       Q3902     69
```

Only **15 sites (0.2%)** hit an ambiguous key needing a tiebreak. The rule is close to deterministic.

**What remains after the fix** — genuine vocabulary gaps, 974 sites in the conflict set and 2,153 in the unmatched set:

`Orissa` 187+91 · `Katanga` 93+148 · `Newfoundland` 101 · `Chitinskaya oblast` 83 · `Aqmola` 78 · `Greenland` 67 · `CO` 51 *(a bare abbreviation)* · `Qaraghandy` 51 · `Territory Of New Caledonia And Dependencies` 49

These need vocabulary aliases or a renamed-entity table, not a matcher change — confirming and extending the first run's Orissa/Katanga finding to a class of roughly 3,100 sites.

## A1 — Reprojection verification 🟢

**CRS identities read from the PROJ 9.5.1 database, not from memory:**

| EPSG | Name | Axis unit |
|---|---|---|
| **2994** | NAD83(HARN) / Oregon GIC Lambert | **foot** |
| 2993 | NAD83(HARN) / Oregon LCC | metre |
| **26912** | NAD83 / UTM zone 12N | **metre** |
| 4326 | WGS 84 | degree |
| 4267 | NAD27 | degree |

**Records tested: 90 distinct** — the min/max latitude and longitude extremes of both feeds (8 queries × 10 rows) plus all 20 bucket-C records.

| Source | Declared | Tested as | In expected state | Elsewhere |
|---|---|---|---|---|
| oregongeology | EPSG:2994 | **EPSG:2994 (declared)** | **50** | **0** |
| oregongeology | EPSG:2994 | EPSG:2993 (metre sibling) | 10 | 40 |
| OFR-757 | EPSG:26912 | **EPSG:26912 (declared)** | **39** | **1** |

**The declared CRS is correct.** Under EPSG:2994 (feet) every Oregon record tested lands in Oregon; under the metre variant 40 of 50 land outside. The Part 4 alternative — that the CRS label itself is wrong, which would have meant a CRS-aware validation rule saves nobody — is **excluded**. 🟢

**The single OFR-757 exception** is `School Sec. 36`, `POINT (561170 4094970)` → (−110.31253, **36.99889**). Utah's southern border is exactly 37.0°N; the point is **123.3 m** south of it. That is a site on the Utah/Arizona line falling just outside a hard-edged bounding box, not a reprojection failure. Polygon containment (Probe 1d) would classify it properly; a rectangle cannot.

**Bucket C is settled.** All 20 records are oregongeology / EPSG:2994, and all 20 reproject into Oregon under the declared CRS. The first run's one-sentence "southern edge of the projection" explanation was correct 🟢 — these are small *northings in feet*, not anomalous coordinates.

**Harts Draw — the decisive record:**

```
stored (OFR-757, EPSG:26912) : POINT (632887 4199554)
reprojected to EPSG:4326     : POINT (-109.4878352 37.9338523)

vs Pay Off-Harts Draw   POINT (-109.4878899999999931 37.9338899999999981)  ->  6.4 m
vs Harts Draw Deposits  POINT (-109.4879099999999994 37.9338800000000020)  ->  7.3 m
```

**6.4 m and 7.3 m.** The first run's 🟡 inference that reprojection reproduces the MRDS siblings' value is now **🟢 verified arithmetic**. Problem 1's conclusion does not reopen; it hardens.

## Addendum trap notes

- **The UNION-scoping trap fired again.** `A2.1h` returned **0.00% for every source** — a clean, uniform, plausible-looking table — because `?source`, bound in the enclosing group, is **not in scope inside a `UNION` branch's `FILTER`**. With 20,392 cross-source pairs known to exist, uniform zeros were obviously wrong; without that prior it would have read as a finding. Same class as `3d` in the first run. **Rule for the script: never reference an outer-group variable inside a UNION branch.**
- **One timeout, recorded:** `A2.1h-alt` (correlated `OPTIONAL` subquery) exceeded 120 s and was killed. Superseded by `A2.1i`/`A2.1j`, two uncorrelated directional queries that compute the same figure in under 20 s combined. No partial results were used.
- 31 probes, 30 returned HTTP 200, 1 timed out. 325.4 s total endpoint time.
