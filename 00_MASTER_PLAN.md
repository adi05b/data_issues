# MinMod data correction — master plan

*Aditi Bombe · started 2 Sep 2026 · for Craig Knoblock, Amandeep, Adriana Trejo-Sheu*

Three problems from Adriana's 26 Aug email, one investigation, one eventual script. This file is the plan and the running log. Each problem has its own file with the probe queries, what to record, and the decision to make.

| # | Problem | Scale (dedup) | Adriana's ask | File |
|---|---|---|---|---|
| 1 | Latitude outside [−90, 90] | 24,818 entities (6.2%) | Fix; most look like lat/lon flips; corrected point must land in the observed state/country | `01_latitude_out_of_range.md` |
| 2 | Normalized state's country ≠ normalized country | 5,858 entities | Review the disagreement CSV (column D vs column H) | `02_state_country_conflict.md` |
| 3 | Coordinates at ≤1 decimal place | 3,633 at 1 dp + 232 at 0 dp | Informational: list of sources, in case extraction changes | `03_coordinate_precision.md` |

## Sequence

1. **Probe** — run one query per problem against the live endpoint (`minmod.isi.edu/dashboard/sparqlsearch`). Paste raw output into the problem file. No fixes yet. *(this week)*
2. **Confirm** — for each problem, answer the questions listed in its file from the probe output. Decide fix location and mechanism. Get Craig's sign-off on the mechanism before touching data.
3. **Fix one row by hand** per problem, end to end, and verify it reaches the live graph. This is the dry run for the script.
4. **Script** — one combined script, built from the three confirmed procedures. Not before step 3 is done for all three.

The adjudicator prompt already written (`minmod-adjudicator/`) is a step-4 component for the residue that rules cannot settle. It does not run in steps 1–3.

## What the graph actually looks like (verified against source, 2 Sep)

Read `ta2-minmod-kg/schema/ontology.ttl` and the `minmodkg/models/kg/` dataclasses rather than the paper's figure. The paper simplifies.

```
mr:<site>  a :MineralSite ;
           :name "…" ; :record_id "…" ; :source_id "…" ;
           :location_info mr:<li> .

mr:<li>    a :LocationInfo ;
           :location "POINT(lon lat)"^^geo:wktLiteral ;      # one string; lon FIRST
           :crs  mr:<cand> ;                                   # optional
           :country  mr:<cand> ;                               # a LIST — a site can carry several
           :state_or_province mr:<cand> .                      # also a list

mr:<cand>  a :CandidateEntity ;
           :source "…" ; :confidence 0.9 ;
           :observed_name "Florida" ;                          # raw string from the extractor
           :normalized_uri mr:Q6850 .                          # points at a vocabulary entity

mr:Q6850   a :StateOrProvince ; rdfs:label "Florida" ; :country "Q1233" .   # country id — check whether literal or IRI in probe
mr:Q1233   a :Country ; rdfs:label "United States" .
```

Prefixes: `:` = `https://minmod.isi.edu/ontology/`, `mr:` = `https://minmod.isi.edu/resource/`.

Three consequences for the queries:

- **Latitude is the second number** inside the WKT. Any query has to split the string; there is no `:latitude` predicate.
- **A site can carry more than one country or state candidate** (one per contributing source). "The" country of a site is whichever candidate the dedup/merge elected. A probe that joins naively will multiply rows.
- **The SPARQL endpoint serves raw records** (679,781). Adriana's counts are on `dedup_mineral_site` (419,099), which lives in Postgres and reaches the UI through the REST API, not SPARQL. Expect the raw counts to be higher, and expect one dedup entity to expand into several raw rows.

## Root causes already visible from the vocabulary (before any query)

Pulled `ta2-minmod-data/data/entities/state_or_province.csv` (5,083 rows) and `country.csv`.

**Problem 2 is mostly a fuzzy-match failure against suffixed labels, not name ambiguity.** The vocabulary stores `La Paz Department`, `Potosí Department`, `Oruro Department`, `Santa Cruz Department`, `Camagüey Province`. The extractors observe `La Paz`, `Potosi`, `Oruro`, `Santa Cruz`, `Camaguey`. The matcher scored `La Pampa` (Argentina) above `La Paz Department` (Bolivia), and `Porto` (Portugal) above `Potosí Department`. Suffixes appear on 484 of 5,083 labels (`Department` 97, `Province` 333, `Parish` 54), so this class recurs across every country that uses them. Fixing the 5,858 rows without fixing the matcher means the next ETL run regenerates them.

The Florida row is the exception: three real `Florida` entries exist (Q5307 Puerto Rico, Q6850 United States, Q6920 Uruguay), so that one is a true tie that the matcher broke wrongly. Note that Q5307 and Q6850 carry the *identical* centroid (27.66, −81.52) and Q6920 Uruguay's centroid (28.04, −82.46) is Tampa, Florida. The vocabulary's own coordinates are unreliable for tiebreaking.

Two of Adriana's rows are vocabulary gaps, not matcher errors: `Orissa` (vocabulary has only `Odisha`) and `Katanga` (province split in 2015; vocabulary has `Haut-Katanga`, `Lualaba`, `Tanganyika`, `Haut-Lomami`). No correct target exists, so those rows need a vocabulary alias, not a repoint.

**Problem 1 has a second explanation to rule out.** `crs.csv` has four entries: EPSG:4326, EPSG:4267, EPSG:3857, EPSG:26912. A record declaring 26912 (UTM 12N, metres) will have coordinates in the hundreds of thousands, which also fails the [−90, 90] check but is not a flip. The probe checks whether any out-of-range row carries a non-4326 CRS before anyone swaps anything.

**Problem 1 is undercounted.** A transposed pair whose magnitudes are both under 90 stays in range and never enters the 24,818. Only a containment test (does the point fall in the observed country?) catches those. Worth raising as scope.

## Questions to settle in step 2

| Q | Why it matters |
|---|---|
| Do fixes land as edited JSON in `ta2-minmod-data` + ETL rebuild, or as writes through the editor API (new record + `owl:sameAs` back to the original)? | Different provenance; different script. Editor writes survive the next rebuild, direct JSON edits are the rebuild. |
| Is `:country` on `mr:Q<state>` a literal `"Q1233"` or an IRI `mr:Q1233`? | Determines the join in problem 2's query and script. Probe 2 answers this. |
| Which country/state candidate does dedup elect when a site carries several? | Determines whether we fix the candidate or the election. |
| Why did the SHACL validation (paper §10, "always validate input data") not bound latitude? | A three-line shape stops the class recurring. Cheaper than any of this. |
| For problem 2, does the matcher get fixed (suffix-stripping, diacritic folding) or only the rows? | Rows-only means regeneration on the next ETL. |

## Log

- **2 Sep** — Read paper, field guide, Adriana's slides. Pulled ontology and entity CSVs from GitHub. Wrote 9 probe queries; parse-checked and dry-run against a synthetic graph built to the real ontology shape, all return the expected rows. Not yet run on the live endpoint (unreachable from the sandbox — run them in the dashboard console). Found the suffix root cause in the vocabulary. Wrote adjudicator prompt + 18-case eval for the eventual residue.

- **2 Sep (probe run, step 1 complete)** — Found the live endpoint: **`https://minmod.isi.edu/sparql`**, POST, no auth, Apache Jena Fuseki (version not exposed). The dashboard is a Dash UI and does not reveal it. Ran 39 read-only queries (10 pre-flight, the 9 planned minus parked 1d, plus 20 amendments and new probes). Nothing written. Full record in `probe-runs/2026-09-02/`, shape in `DATA_SHAPE.md`, analysis in `PROBE_REPORT.md`, residue in `OPEN_QUESTIONS.md`.

  **Headline: Problem 1 is not a lat/lon flip problem.** Of 31,109 raw out-of-range records, **31,108 are correctly-stored projected coordinates** — 23,316 in EPSG:2994 (Oregon Lambert, = 100% of oregongeology.org) and 7,792 in EPSG:26912 (UTM 12N, = 99.99% of OFR-757). **Exactly one record in the graph is a genuine transposition** (Tagaung Taung, `POINT(23.63453 96.16317)`). The decision rule in `01_latitude_out_of_range.md` inverts: a swap script would have corrupted 31,108 correct records. Even the flagship Harts Draw example is UTM metres, not a flip — its two MRDS siblings already hold the correct EPSG:4326 value. The real defect is a range check that reads latitude without reading `:crs`, which is populated on 99.7% of records.

  **Four schema corrections to the block above — two of them break the probe queries.** (1) **There is no `:name` predicate** — zero triples; the site name is `rdfs:label`. Probe 1a returned **HTTP 200 with 0 rows and no error**; 1c and 3b ran with `?name` permanently unbound. (2) The WKT datatype is **`xsd:string`**, not `geo:wktLiteral`. (3) The United States is **`Q1235`**, not Q1233. (4) `:crs` is **99.72% populated**, not optional. Also: the WKT is `POINT (lon lat)` **with a space before the paren** on 99.5% of rows; parse coverage is 99.951%, with 217 rows invisible to every probe (215 `MULTIPOINT`, 1 misspelled `MULIPOINT`, 1 `NaN` latitude).

  **The candidate-list worry was unfounded.** Lists are singletons in practice: 450,570 of 451,527 sites carry exactly one country candidate (2 carry two), 421,524 exactly one state candidate (31 carry more). Row multiplication affects **33 sites**, and "which candidate does dedup elect" is moot for 99.99% of sites.

  **Problem 2 is confirmed and ready.** `:country` on a state entity is a **plain literal** bare Q-id, `:normalized_uri` is an IRI — Probe 2b's join is correct as written. Raw total 6,156 vs 5,858 dedup; Florida/PR 1,609 vs 1,587; La Paz/La Pampa 586 vs 531. Every root cause predicted from the vocabulary CSVs is confirmed live, including both vocabulary gaps. New: **matcher confidence is discriminative** — 58.7% of conflicts sit below 0.9 vs 2.5% of all candidates (~23x), so a `< 0.9` review gate is a cheap partial win, though it misses the 2,058-row Florida bucket at 0.9999. New constraint: suffix-stripping alone is insufficient, since `La Paz Department` exists in three countries — candidates must also be constrained to the normalized country.

  **Problem 3's probes do not measure Adriana's figures.** Latitude-only 1 dp gives 2,853 raw against her 3,633 dedup, and uneven precision gives 33,950 raw against her 93,673 — **raw below dedup is impossible at the same grain**. Probe 3a is also CRS-blind and ranks OFR-757's UTM *metres* as the coarsest source in the graph. Deeper: **stored decimal places are float64 serialisation artifacts, not measurement precision** (MRDS stores 16 dp for values published at 5), so error propagation cannot be built on them — and **no precision field exists anywhere in the schema**. The one clean result is (0,0): 34 raw rows, **all from one extractor** (`api.cdr.land`, Inferlink), 29 carrying a real observed country across four continents. Confirms the plan's call — clear the location, keep the country, don't geocode.

  **Not run:** §9's upstream check and the SHACL grep — no `ta2-minmod-data` / `ta2-minmod-kg` checkout on this machine, nothing cloned. The `data-quality-auditor` skill and its `data_profiler.py` are not installed either; CSVs with `<var>_bound` columns are written and ready, and the profiling the report needed was computed from the raw JSON instead.

  **Next:** three questions before step 2 can close — Craig on the fix mechanism (the probe shifts most of the work toward the repo/ETL path), Adriana on what she actually counted for Problem 3, and a decision on whether to promote Probe 1d's containment test, which is now the *only* remaining flip exposure.

- **2 Sep (addendum run)** — 31 further read-only queries plus offline `pyproj` verification; record in `probe-runs/2026-09-02-addendum/`. **Problem 1's reprojection claim is now verified arithmetically:** Harts Draw's UTM record reprojects to within **6.4 m / 7.3 m** of its two MRDS siblings, and 89 of 90 records sampled from the bounding-box extremes of both projected feeds land inside the observed state under their declared CRS (the exception is 123 m outside a rectangle whose edge is the Utah state line). The foot/metre ambiguity is pinned: **EPSG:2994 is the foot variant** and 50/50 Oregon records land in Oregon under it, versus 10/50 under the metre sibling EPSG:2993 — so **the CRS field is trustworthy and a CRS-aware validation rule would work.**

  **The matcher fix is now quantified and it is the highest-value change in the investigation.** Suffix-stripping + diacritic-folding, constrained to the record's normalized country, resolves **5,145 of 6,134 conflicts (83.9%)** to the correct target — every one of Adriana's examples that has a target — with only 15 ambiguous. It also recovers **1,090 of 3,248 sites (33.6%)** in a population the first run never counted: **3,245 sites whose state name failed to normalize at all**, which sit outside the conflict count because a conflict needs both sides matched. **6,235 sites from one change.** Residue is ~3,100 sites needing vocabulary aliases (Orissa 278, Katanga 241, Newfoundland 101, `CO` 51 — a bare abbreviation in a name field).

  **Two corrections to earlier work.** (1) The CRS half of the "root causes visible from the vocabulary" section is wrong: the live graph has exactly four CRSs — 4326, 4267, 26912, **2994** — while `crs.csv` as read lists **3857** (zero occurrences) and omits 2994 (23,316 occurrences). **The entity CSVs are not a mirror of the deployed graph; treat any CSV-derived claim as unverified until queried.** (2) The first report's suggestion that projected coordinates suppress FuseMine-style clustering is **not supported** — Oregon's cross-source link rate is 5.93% against a 3.50% graph baseline. That test also revealed `owl:sameAs` is **72.2% the same source record processed by two teams**, only 7.8% cross-source, so what writes it is now an open question.

  Also closed: OFR-757's odd record out is simply one with no WKT (benign, not a mislabeled CRS), and oregongeology is exactly 100.0% EPSG:2994. The UNION-scoping trap fired a second time — a cross-source query returned a clean uniform 0.00% for all 48 sources because an outer variable is not in scope inside a UNION branch. **Rule for the script: never reference an outer-group variable inside a UNION branch.**

  **Deliverable for circulation: `SUMMARY.md`** — plain-language, standalone, five sections, with options and trade-offs per problem rather than single recommendations.

  **Part 5 (repo checks) still not run** — no `ta2-minmod-*` or `minmodkg` checkout on this machine and I did not clone. Four things remain blocked on it, the most leveraged being **whether the dedup coordinate is elected or recomputed**, which would dissolve both of Problem 3's impossible ratios at once and should be read *before* drafting any question to Adriana.
