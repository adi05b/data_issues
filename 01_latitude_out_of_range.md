# Problem 1 — latitude outside [−90, 90]

**Scale:** 24,818 dedup entities (6.2% of 400,447 with coordinates). Longitude out of range: 0. Lat or lon missing: 0.
**Adriana's ask:** update the coordinates; most look like a lat/lon flip; the corrected point should match the observed state/country.
**Her example rows:** Harts Draw Deposits (−109.48784, 37.93385 → Utah, EPSG:26912), Little Baby prospect (−117.51086, 44.92669 → Oregon), Tagaung Taung (96.16317, 23.63453 → Myanmar).

## Hypotheses to separate

| H | What it looks like | Fix |
|---|---|---|
| **H1 flip** | \|lat\| > 90, \|lon\| ≤ 90, swapped point lands in the observed country | swap |
| **H2 projected CRS** | values in the 10⁵–10⁷ range, `:crs` names EPSG:26912 / 3857 / 4267 | reproject, never swap |
| **H3 sign error** | flip alone lands in the wrong hemisphere; flip + negate lands correctly | swap and negate |
| **H4 garbage** | no transform lands in the observed country | flag, do not touch |

The slides list "EPSG:26912" next to Harts Draw, so H2 is live even on her flagship example. Rule it out first.

## Probe 1a — one known row, see the raw shape

Run first. Confirms predicate names, WKT format, whether `:crs` is populated, and how many country/state candidates one site carries.

```sparql
PREFIX : <https://minmod.isi.edu/ontology/>
PREFIX mr: <https://minmod.isi.edu/resource/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?site ?name ?source ?wkt ?crs_obs ?crs_label ?country_obs ?country_ent ?state_obs ?state_ent
WHERE {
  ?site a :MineralSite ;
        :name ?name ;
        :location_info ?li .
  FILTER(CONTAINS(LCASE(STR(?name)), "harts draw"))
  OPTIONAL { ?site :source_id ?source }
  OPTIONAL { ?li :location ?wkt }
  OPTIONAL { ?li :crs ?crsc .
             OPTIONAL { ?crsc :observed_name ?crs_obs }
             OPTIONAL { ?crsc :normalized_uri ?crs_ent . ?crs_ent rdfs:label ?crs_label } }
  OPTIONAL { ?li :country ?cc .
             OPTIONAL { ?cc :observed_name ?country_obs }
             OPTIONAL { ?cc :normalized_uri ?country_ent } }
  OPTIONAL { ?li :state_or_province ?sc .
             OPTIONAL { ?sc :observed_name ?state_obs }
             OPTIONAL { ?sc :normalized_uri ?state_ent } }
}
LIMIT 20
```

Repeat with `"little baby"` and `"tagaung"`.

## Probe 1b — how many raw records, split by CRS

Separates H1/H3 from H2 in one query. The regex pulls the two numbers out of `POINT(lon lat)`.

```sparql
PREFIX : <https://minmod.isi.edu/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?crs_label (COUNT(DISTINCT ?site) AS ?sites)
WHERE {
  ?site a :MineralSite ; :location_info ?li .
  ?li :location ?wkt .
  BIND(REPLACE(STR(?wkt), "^\\s*POINT\\s*\\(\\s*([-+0-9.eE]+)\\s+([-+0-9.eE]+)\\s*\\).*$", "$2") AS ?lat_s)
  BIND(xsd:double(?lat_s) AS ?lat)
  FILTER(BOUND(?lat) && (?lat > 90 || ?lat < -90))
  OPTIONAL { ?li :crs ?crsc . ?crsc :normalized_uri ?crs_ent . ?crs_ent rdfs:label ?crs_label }
}
GROUP BY ?crs_label
ORDER BY DESC(?sites)
```

If `xsd:double` refuses the cast on this Fuseki build, the FILTER silently drops every row and the count comes back 0. If that happens, fall back to Probe 1c, which lists raw strings and lets you eyeball.

## Probe 1c — 30 rows with everything needed to test the swap

```sparql
PREFIX : <https://minmod.isi.edu/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?site ?name ?source ?lon ?lat ?crs_label ?country_obs ?state_obs
WHERE {
  ?site a :MineralSite ; :location_info ?li .
  ?li :location ?wkt .
  BIND(REPLACE(STR(?wkt), "^\\s*POINT\\s*\\(\\s*([-+0-9.eE]+)\\s+([-+0-9.eE]+)\\s*\\).*$", "$1") AS ?lon_s)
  BIND(REPLACE(STR(?wkt), "^\\s*POINT\\s*\\(\\s*([-+0-9.eE]+)\\s+([-+0-9.eE]+)\\s*\\).*$", "$2") AS ?lat_s)
  BIND(xsd:double(?lon_s) AS ?lon)
  BIND(xsd:double(?lat_s) AS ?lat)
  FILTER(BOUND(?lat) && (?lat > 90 || ?lat < -90))
  OPTIONAL { ?site :name ?name }
  OPTIONAL { ?site :source_id ?source }
  OPTIONAL { ?li :crs ?crsc . ?crsc :normalized_uri ?crs_ent . ?crs_ent rdfs:label ?crs_label }
  OPTIONAL { ?li :country ?cc . ?cc :observed_name ?country_obs }
  OPTIONAL { ?li :state_or_province ?sc . ?sc :observed_name ?state_obs }
}
LIMIT 30
```

## Probe 1d — the undercount check (optional, after 1a–1c)

Rows whose latitude is in range but whose *longitude* magnitude is under 90 and whose observed country is one where a flip would also be in range. Cannot be done in SPARQL alone; needs the country polygon test in the script. Note it as scope, do not chase it this week.

## Record from the probe

- [ ] WKT format exactly as stored (spacing, `POINT` vs `POINT Z`, any `<http://www.opengis.net/def/crs/…>` prefix inside the literal)
- [ ] Whether `:crs` is populated on out-of-range rows, and which EPSG codes appear
- [ ] Number of raw sites out of range (compare to 24,818 dedup)
- [ ] Number of country candidates on Harts Draw (1, or several?)
- [ ] Sources that dominate the out-of-range set (from `?source`)

## Decision after the probe

- If Probe 1b shows every out-of-range row is EPSG:4326 or null → H1/H3 only; the script swaps, geocodes, checks containment.
- If non-4326 rows appear → split the queue. Reproject those with `pyproj` from the declared CRS; swap the rest.
- Either way, propose a SHACL shape bounding latitude so the class stops recurring.

## One-row dry run (step 3)

Harts Draw. Swap to (37.93385, −109.48784), confirm it geocodes to Utah, apply through whichever mechanism Craig approves, confirm the live graph and the map view both reflect it, and check whether the fix survives (editor path) or *is* (data-repo path) the next ETL.

## Findings

*(paste probe output and notes here)*

---

### Probe run 2026-09-02 — raw output

*Endpoint `https://minmod.isi.edu/sparql` (Fuseki), read-only. Files in `probe-runs/2026-09-02/`. Grain: **raw** (679,781 records).*

#### Probe 1a — RETURNED ZERO ROWS

```
HTTP 200 · 0 rows · 2155 ms · no error
```

**The query is broken, not the data.** `?site :name ?name` is a *required* pattern, and **`:name` does not exist in this graph** — `P0.1-mineralsite` lists every predicate on `:MineralSite` and `:name` is absent; `P0.1b-name-check` returns `COUNT = 0`. The site name is **`rdfs:label`** (438,655 of 679,781 sites). A non-existent predicate yields an empty result with HTTP 200 and no error.

Amended as **`1a-alt`** (sole change: `:name` -> `rdfs:label`), run for all three names.

#### Probe 1a-alt-harts — 3 rows

```
site                                              label                wkt                                                crs
site__mrdata-usgs-gov-mrds__10228202__umn         Pay Off-Harts Draw   POINT (-109.4878899999999931 37.9338899999999981)  EPSG:4326
site__mrdata-usgs-gov-mrds__10078772__umn         Harts Draw Deposits  POINT (-109.4879099999999994 37.9338800000000020)  EPSG:4326
site__doi-org-10-34191-ofr-757__0__umn            Harts Draw Deposits  POINT (632887 4199554)                             EPSG:26912
```

All three: `country_obs` = "United States" -> `Q1235`; `state_obs` = "Utah" -> `Q6897`. One country and one state candidate each (rows-per-site = 1.00).

WKT hexdump (record 1) — no leading/trailing whitespace, pure ASCII, plain literal:
`50 4f 49 4e 54 20 28 2d 31 30 39 2e ... 38 31 29`

#### Probe 1a-alt-tagaung — 6 rows (abridged)

```
site__doi-org-10-5382-econgeo-4950__tagaung-taung__usc   POINT(23.63453 96.16317)              EPSG:4326  Myanmar
site__mrdata-usgs-gov-laterite__74__umn                  POINT (96.1588888888889 23.5611111111111)  EPSG:4326  Myanmar (Burma)
site__mrdata-usgs-gov-mrds__10003940__umn                POINT (96.1821300000000008 23.5729199999999999)  EPSG:4326  Burma
site__mrdata-usgs-gov-nicrpge__207006__umn               POINT (96.15 23.48)                   EPSG:4326  Myanmar
site__mrdata-usgs-gov-nicrpge__58343__umn                POINT (96.15 23.39)                   EPSG:4326  Myanmar
site__mrdata-usgs-gov-nicrpge__58539__umn                POINT (96.18 23.57)                   EPSG:4326  Myanmar
```

On the `usc` row `?crs_obs` is UNBOUND while `?crs_label` is BOUND — the ":crs candidate present, `:normalized_uri` resolves, but no `:observed_name`" case. On the laterite row `?country_obs` = "Myanmar (Burma)" is bound but `?country_ent` is UNBOUND (normalization failure).

#### Probe 1b — out-of-range split by CRS

```
crs_label     sites
EPSG:2994     23316
EPSG:26912     7792
EPSG:4326         1
              -----
              31109
```

**No null-`?crs_label` bucket at all** — every out-of-range record carries a `:crs` with a resolved `:normalized_uri` and an `rdfs:label`. The three-way distinction the plan asks for (no candidate / no normalized_uri / no label) is therefore **moot: none of the three cases occurs**.

Zero is **not** a cast failure here: `P0.5-cast-canary` bound all three test doubles, so `xsd:double` works on this build and "EPSG:4326 = 1" is a real count.

#### Probe 1c — 30 rows, TRUNCATED BY LIMIT

All 30 rows are `oregongeology.org` / EPSG:2994. `?name` unbound on every row (the `:name` bug; harmless here as it is under OPTIONAL). This is one page of one source, **not a sample of the population**.

| Classification of all 30 | Count |
|---|---|
| **H2 projected CRS** | **30** |
| H1 flip | 0 |
| H3 sign error | 0 |
| H4 garbage | 0 |

- `\|lon\| <= 90` on **0 of 30** -> **no row is flip-consistent**; H1 excluded for all 30.
- Decimal-place comparison is not diagnostic: both values are projected coordinates, not degrees.
- `?country_obs` ("United States") and `?state_obs` ("Oregon") are **bound on all 30**, so H4 is falsifiable — and falsified.

#### Probe 1e — magnitude histogram (new)

```
bucket          sites
A_90_to_180         1     <- the transposition signature
C_1e3_to_1e5       20     (Oregon Lambert, southern edge)
D_1e5_to_1e7    31088     <- projected metres/feet
                -----
                31109
```

Bucket B (180-1e3) and E (>1e7) are empty. Agrees exactly with Probe 1b's total.

#### Probe 1f — the single bucket-A row

```
site__doi-org-10-5382-econgeo-4950__tagaung-taung__usc
Tagaung Taung | doi.org/10.5382/econgeo.4950 | POINT(23.63453 96.16317) | EPSG:4326 | Myanmar
```

---

### Notes

1. **H2 is the population story; H1 is a population of one.** 31,108 of 31,109 out-of-range records are correctly-stored projected coordinates whose `:crs` is populated and correct. They fail the [-90, 90] check because metres and feet are not degrees.

2. **The plan's decision rule inverts.** It reads *"If Probe 1b shows every out-of-range row is EPSG:4326 or null -> H1/H3 only; the script swaps."* The observed answer is the opposite. **A swap script would corrupt 31,108 correct records.**

3. **The flagship example kills H1 rather than promoting it.** Harts Draw's out-of-range record is UTM 12N metres. Its two MRDS siblings already hold the correct EPSG:4326 value (-109.4879, 37.9339), which is what reprojecting (632887, 4199554) should produce — swapping would yield latitude 4,199,554.

4. **Concentration is total.** EPSG:2994 = 100.0% of oregongeology.org's 23,316 sites; EPSG:26912 = 99.99% of OFR-757's 7,793. Two entire source feeds stored in their native projection, not scattered corruption.

5. **EPSG:2994 is not in the plan's CRS list.** `crs.csv` was read as four entries (4326/4267/3857/26912). EPSG:2994 (Oregon Lambert) carries the single largest block of out-of-range records. The CRS vocabulary is wider than assumed and the script must not hard-code four codes.

6. **The real defect is the validator, not the data.** A range check that reads latitude without reading `:crs` — populated on 99.72% of records — manufactures 31,108 false positives. A CRS-aware rule removes them without touching a record.

7. **Recommended SHACL shape must be conditional.** Bound latitude to [-90, 90] *only when `:crs` resolves to a geographic CRS*. An unconditional bound rejects two valid source feeds.

8. **The undercount is now the main flip risk.** With H1's visible population known to be exactly 1, transpositions where both magnitudes are under 90 are the only remaining flip exposure — and they are invisible to SPARQL. Probe 1d's containment test moves from "nice to have" to "the only way to size H1".

#### Checklist from "Record from the probe"

- [x] **WKT format** — `POINT (lon lat)` with a space before the paren on 444,048 of 446,426; `POINT(lon lat)` on 2,161. Datatype `xsd:string` (**not** `geo:wktLiteral`). No `POINT Z`, no embedded CRS URI, no scientific notation, no trailing whitespace. 215 `MULTIPOINT`, 1 `MULIPOINT` (misspelled), 1 `NaN` latitude are invisible to every probe (parse coverage 99.951%).
- [x] **`:crs` on out-of-range rows** — populated and resolved on **100%** of them. Codes: EPSG:2994, EPSG:26912, EPSG:4326.
- [x] **Raw sites out of range** — **31,109** (vs 24,818 dedup; ratio 1.25).
- [x] **Country candidates on Harts Draw** — **1** per record (3 records = 3 distinct sites, not one multiplied). Graph-wide: 450,570 of 451,527 sites carry exactly 1.
- [x] **Dominant sources** — `oregongeology.org` 23,316 and `doi.org/10.34191/OFR-757` 7,792. Together 99.997%.

