# Problem 3 — coordinates at ≤ 1 decimal place

**Scale:** 3,633 dedup entities at 1 dp, 232 at 0 dp (whole degrees), 29 at exactly (0, 0). Separately, 93,673 (23.4%) store lat and lon at *different* precision.
**Adriana's ask:** informational. A list of sources where this happens, in case extraction should change. She will handle error propagation when comparing two entities of differing precision.

So this is not a fix task. It is a **source attribution** task: which contributors ship coarse coordinates, and is that the source's limit or an extraction loss?

## Why it still matters

| dp | grid | worst case | vs FuseMine 10 km blocking |
|---|---|---|---|
| 0 | ≈110 km | ±70 km | 7× the radius |
| 1 | ≈11 km | ±7 km | wider than the radius |
| 2 | ≈1.1 km | ±0.7 km | fine |
| 5 | ≈1 m | — | the bulk (275,294) |

A 1 dp site cannot be reliably linked to anything, and cannot be reliably *un*linked either. Problem 3 is the reason problems 1 and 2 need a confidence field.

Also: the vocabulary's own state centroids have 19 rows at ≤1 dp and 74 with no coordinates at all, so "fall back to the state centroid" is not a safe default for these rows.

## Probe 3a — precision histogram by source

Counts fractional digits on the latitude string directly. No numeric cast needed, so it cannot silently fail.

```sparql
PREFIX : <https://minmod.isi.edu/ontology/>

SELECT ?source ?lat_dp (COUNT(DISTINCT ?site) AS ?sites)
WHERE {
  ?site a :MineralSite ; :location_info ?li .
  ?li :location ?wkt .
  OPTIONAL { ?site :source_id ?source }
  BIND(REPLACE(STR(?wkt), "^\\s*POINT\\s*\\(\\s*[-+0-9.eE]+\\s+([-+0-9.eE]+)\\s*\\).*$", "$1") AS ?lat_s)
  BIND(IF(CONTAINS(?lat_s, "."), STRLEN(STRAFTER(?lat_s, ".")), 0) AS ?lat_dp)
  FILTER(?lat_dp <= 1)
}
GROUP BY ?source ?lat_dp
ORDER BY DESC(?sites)
LIMIT 40
```

## Probe 3b — the (0, 0) rows

```sparql
PREFIX : <https://minmod.isi.edu/ontology/>

SELECT ?site ?name ?source ?wkt ?country_obs
WHERE {
  ?site a :MineralSite ; :location_info ?li .
  ?li :location ?wkt .
  FILTER(REGEX(STR(?wkt), "^\\s*POINT\\s*\\(\\s*-?0(\\.0+)?\\s+-?0(\\.0+)?\\s*\\)"))
  OPTIONAL { ?site :name ?name }
  OPTIONAL { ?site :source_id ?source }
  OPTIONAL { ?li :country ?cc . ?cc :observed_name ?country_obs }
}
LIMIT 40
```

Null Island is a missing value wearing a coordinate. These should probably have no `:location` at all; the fix is to clear, not to geocode.

## Probe 3c — uneven precision, top sources

```sparql
PREFIX : <https://minmod.isi.edu/ontology/>

SELECT ?source (COUNT(DISTINCT ?site) AS ?sites)
WHERE {
  ?site a :MineralSite ; :location_info ?li .
  ?li :location ?wkt .
  OPTIONAL { ?site :source_id ?source }
  BIND(REPLACE(STR(?wkt), "^\\s*POINT\\s*\\(\\s*([-+0-9.eE]+)\\s+([-+0-9.eE]+)\\s*\\).*$", "$1") AS ?lon_s)
  BIND(REPLACE(STR(?wkt), "^\\s*POINT\\s*\\(\\s*([-+0-9.eE]+)\\s+([-+0-9.eE]+)\\s*\\).*$", "$2") AS ?lat_s)
  BIND(IF(CONTAINS(?lon_s, "."), STRLEN(STRAFTER(?lon_s, ".")), 0) AS ?lon_dp)
  BIND(IF(CONTAINS(?lat_s, "."), STRLEN(STRAFTER(?lat_s, ".")), 0) AS ?lat_dp)
  FILTER(?lon_dp != ?lat_dp)
}
GROUP BY ?source
ORDER BY DESC(?sites)
LIMIT 20
```

Uneven precision usually means the two axes came from different places — one from the source, one from a fallback (a state centroid, a truncated string, a re-rounding). Which sources dominate tells you where to look.

## Record from the probe

- [ ] Sources ranked by count of ≤1 dp rows. Is it concentrated (one or two contributors) or diffuse?
- [ ] For the top source, open two or three source records upstream in `ta2-minmod-data/data/mineral-sites/<team>/`. Does the *source file* already carry 1 dp, or did the ETL round it?
- [ ] Sources for the 29 (0, 0) rows
- [ ] Whether uneven-precision rows and ≤1 dp rows share sources

## Decision after the probe

- Source ships coarse → nothing to fix in extraction. Record an explicit precision field (or the decimal-place count) so downstream consumers can propagate error. Adriana's error calculation needs this number.
- ETL rounds → fix the extractor; the precision was real and was lost.
- (0, 0) → clear the location; keep the record.

## One-row dry run (step 3)

None needed. This problem does not produce a correction. The deliverable is the source table plus a recommendation on where the precision field lives.

## Findings

*(paste probe output and notes here)*

---

### Probe run 2026-09-02 — raw output

*Endpoint `https://minmod.isi.edu/sparql` (Fuseki), read-only. Files in `probe-runs/2026-09-02/`. Grain: **raw** (679,781 records).*

#### Probe 3a — precision histogram by source (32 rows, not truncated)

```
source                                    lat_dp   sites
doi.org/10.34191/OFR-757                    0       7792   <- UTM METRES, not coarse degrees
mrdata.usgs.gov/nicrpge                     1       1604
mrdata.usgs.gov/major-deposits              1        374
mrdata.usgs.gov/nicrpge                     0        239
mrdata.usgs.gov/phosphate                   1        198
doi.org/10.5066/P96MMRFD                    1        152
api.cdr.land/v1/docs/documents              1        144
mrdata.usgs.gov/ree                         1        106
mrdata.usgs.gov/major-deposits              0        101
...
raw totals (all CRS):  0 dp = 8334 · 1 dp = 2853
```

**The top row is a category error.** OFR-757's 7,792 records are `POINT (632887 4199554)` in **EPSG:26912** — integers because they are *metres*, where 0 dp is 1-metre precision. Probe 3a has no CRS filter, so it ranks the most precise source in the graph as the coarsest.

#### Probe 3a-alt — restricted to EPSG:4326 (new)

```
source                                   coarse(<=1dp)   source total   % of source
mrdata.usgs.gov/nicrpge                       1843          32998         5.59%
mrdata.usgs.gov/major-deposits                 475           5938         8.00%
mrdata.usgs.gov/phosphate                      246           2790         8.82%
mrdata.usgs.gov/ree                            131           1563         8.38%
api.cdr.land/v1/docs/documents                 131          15421         0.85%
mrdata.usgs.gov/sedcu                          101           1563         6.46%
mrdata.usgs.gov/porcu                           67           1376         4.87%
mrdata.usgs.gov/sedexmvt                        32            480         6.67%

EPSG:4326-only totals:  1 dp = 2638 · 0 dp = 499
```

#### Probe 3d-alt — counting-rule variants (new)

```
rule                            raw     vs Adriana's 3633 dedup
a_lat_dp_eq_1                  2853     0.79  <- IMPOSSIBLE (raw < dedup)
b_lon_dp_eq_1                  3081     0.85  <- IMPOSSIBLE
c_either_eq_1                  5409     1.49  <- plausible
d_both_le_1                    8708     2.40
e_either_le_1                 14200
f_lat_dp_eq_0                  8334
g_both_eq_0                    7968
```

#### Probe 3b — the (0,0) rows (34 rows, not truncated)

```
source                            rows    country_obs bound
api.cdr.land/v1/docs/documents      34            29 of 34

WKT forms:  POINT(0 0) x27 · POINT(0.0 0.0) x6 · POINT(-0.0 0.0) x1
```

Observed countries on the 29: Canada x8, Spain x3, Mexico x3, Zambia x2, Finland x2, Madagascar, Romania, Zimbabwe, Greenland, Cote d'Ivoire, Kazakhstan, DR Congo, Turkey, Russia. `?name` unbound on all (the `:name` bug — see problem 1's findings). **Every single (0,0) row comes from one source.**

#### Probe 3c — uneven precision, TRUNCATED BY LIMIT (top 10 of 20)

```
source                                              sites
oregongeology.org                                    9593
doi.org/10.5066/P9HTERGK                             8487
mrdata.usgs.gov/nicrpge                              3644
energy.virginia.gov                                  1798
mrdata.usgs.gov/major-deposits                       1443
doi.org/10.5066/P96MMRFD                             1338
idahogeology.org                                     1290
gsa.state.al.us                                      1052
mrdata.usgs.gov/podchrome                             753
mrdata.usgs.gov/phosphate                             590
```

#### Probe 3c-total — the population (new, no limit)

```
uneven_sites
33950            <- vs Adriana's 93,673 dedup. Ratio 0.36.
```

#### Probe 3c-sample — what uneven rows actually look like (new)

```
POINT (-113.8364 40.11243)     lon 4  lat 5
POINT (-116.17597 47.5274)     lon 5  lat 4
POINT (-145.59333 63.33)       lon 5  lat 2
POINT (-136.4225 57.976)       lon 4  lat 3
POINT (-123.997 41.86979)      lon 3  lat 5
```

---

### Notes

1. **Probe 3a as written does not measure coarse precision — it measures short strings.** Without a CRS filter it ranks EPSG:26912 metre coordinates as the coarsest source in the graph. Any source table must be CRS-aware.

2. **Adriana's counting rule is not reproducible and cannot be latitude-only.** Latitude-only gives 2,853 raw against her 3,633 dedup. Raw < dedup is impossible at the same grain, so Probe 3a and her figure are not counting the same thing. "Either axis at exactly 1 dp" (5,409 raw, ratio 1.49) is the only tested rule that is arithmetically possible. **Ask her what she counted before publishing anything.**

3. **Uneven precision is a float-serialisation artifact, not dual provenance.** The plan hypothesises that lat and lon at different precision means "the two axes came from different places". The sample shows plain trailing-zero stripping: `63.330` stores and prints as `63.33`. Same source, same reading, one axis happened to end in a zero.

4. **Stored decimal places do not recover source precision at all.** MRDS stores `-109.4878899999999931` — 16 decimal places for a value the source publishes at 5. Coordinates round-trip through float64 and are re-serialised at shortest-round-trip length. **Counting decimals measures the float, not the measurement.** This undercuts the premise of Probe 3a for every source that passes through a float, and it is the central finding of problem 3.

5. **3c does not measure Adriana's 93,673 either** — 33,950 raw is 0.36x her dedup figure. Since dedup has *fewer* entities, the most likely explanation is that dedup coordinates are **recomputed** (a mean over merged records), generating uneven decimal lengths that exist in no raw record. Unverified — the merge logic is in Postgres, not SPARQL.

6. **(0,0) is the one genuinely closeable part of this problem.** 34 raw rows, **all from a single extractor** (`api.cdr.land/v1/docs/documents`, Inferlink), 29 of them carrying a real observed country scattered across four continents. This confirms the plan's call exactly: **a (0,0) with an observed country of "Madagascar" is a missing value wearing a coordinate — clear the location, keep the record and its country. Do not geocode.** Because it is one extractor, the durable fix is in that extractor's null handling, not in 34 row edits.

7. **There is no precision field anywhere in the schema.** `P0.1` enumerates every predicate on `:MineralSite`, `:LocationInfo` and `:CandidateEntity`; none carries precision, accuracy or a decimal count. Adriana's error propagation has nowhere to live today. Adding one is an ontology change, and it is the real recommendation from this problem.

#### Checklist from "Record from the probe"

- [x] **Sources ranked by <=1 dp** — **concentrated**: `nicrpge` is 1,843 of 3,137 CRS-aware coarse rows (59%). But the *rate* is a flat 5-9% across most USGS feeds, which looks like a shared upstream characteristic rather than one broken extractor.
- [ ] **Upstream check: does the source file carry 1 dp, or did the ETL round it?** — **NOT RUN.** No `ta2-minmod-data` checkout on this machine; nothing was cloned. Finding 4 makes "the ETL round-trips through a float and loses trailing digits" the leading hypothesis, but it is unconfirmed. **This is the single question that decides between "record a precision field" and "fix the extractor".**
- [x] **Sources for the (0,0) rows** — one: `api.cdr.land/v1/docs/documents` (Inferlink). 34 raw / 29 dedup.
- [x] **Do uneven-precision and <=1 dp rows share sources?** — **partially, and that matters.** `nicrpge` is in both. But `oregongeology` and `P9HTERGK` top the uneven list and are absent from the coarse list, and MRDS (70% of the graph) is absent from the uneven list entirely. **Two different mechanisms, two different fixes.**

