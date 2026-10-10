# DATA_SHAPE.md — what the MinMod query results actually look like

*Probe run 2026-09-02 · endpoint `https://minmod.isi.edu/sparql` (Apache Jena Fuseki) · raw-record grain (679,781 `:MineralSite`) · read-only*

Written so the step-4 script can be built against the live graph rather than against the paper's figure or the plan's reconstruction. Confidence tags: 🟢 verified from a saved response · 🟡 likely · 🔴 assumed.

---

## 0. Corrections to the schema in `00_MASTER_PLAN.md`

Four things in the plan's "What the graph actually looks like" block are wrong against the live endpoint. Two of them silently break probe queries.

| Plan says | Live graph | Evidence | Impact |
|---|---|---|---|
| `mr:<site> :name "…"` | **There is no `:name` predicate.** Zero triples. The site name is **`rdfs:label`** (438,655 of 679,781 sites). | `P0.1-mineralsite`, `P0.1b-name-check` 🟢 | **Fatal.** Probe 1a uses `:name` in a *required* pattern + FILTER → returns **0 rows, HTTP 200, no error**. Probes 1c and 3b use it under `OPTIONAL` → run, but `?name` is unbound on every row. |
| `:location "…"^^geo:wktLiteral` | Datatype is **`xsd:string`** on all 446,426 values. No `geo:wktLiteral` anywhere. | `P0.4-alt-datatype` 🟢 | Any script filtering on `geo:wktLiteral`, or using a GeoSPARQL function that requires it, gets nothing. |
| `mr:Q6850 … :country "Q1233"` (US) | The United States is **`Q1235`**. `Q1233` is not the US. | `2a`, `2e-florida-entities` 🟢 | Hard-coding `Q1233` targets the wrong country. |
| `:crs` is optional / rarely populated | `:crs` is on **450,247 of 451,527** `LocationInfo` nodes (**99.72%**). | `P0.1-locationinfo` 🟢 | `:crs` is effectively mandatory and **must** be read before any coordinate is interpreted. See §1. |

One thing in the plan is **wrong in the safe direction**, and it simplifies the script considerably:

| Plan says | Live graph | Evidence |
|---|---|---|
| "`:country` / `:state_or_province` are LISTS — a naive join will multiply rows" | True in the ontology, **false in the data**. Of 451,527 sites with location info, **450,570 carry exactly one country candidate** and only **2 carry two**. For states, **421,524 carry exactly one** and **31 carry more than one** (28×2, 1×3, 1×4, 1×5). | `P0.7-country-cardinality`, `P0.7b-state-cardinality` 🟢 |

**Consequence:** row multiplication from candidate joins affects **33 sites out of 451,527**. `COUNT(DISTINCT ?site)` is still correct practice, but the plan's fear that naive joins would inflate counts is unfounded, and the "which candidate did dedup elect?" question is **moot for 99.99% of sites — there is only one candidate to elect.** 🟢

---

## 1. The exact WKT grammar in use

All 446,426 stored locations, collapsed to their *forms* by `P0.3-wkt-shapes` (digit runs → `#`). 39 distinct forms, no truncation (39 rows under a `LIMIT 50`).

### Canonical parse

```
POINT<optional-space>(<lon><single-space><lat>)
```

- **Longitude first, latitude second** — confirmed 🟢 (`1a-alt-harts`: `POINT (-109.487… 37.933…)`, Utah).
- Datatype `xsd:string`; serialised as a **plain literal** (no `"datatype"` key in the JSON binding). 🟢
- **No leading or trailing whitespace, no invisible characters.** Verified by hexdump of two values: `POINT (-109.4878899999999931 37.9338899999999981)` → `50 4f 49 4e 54 20 28 2d …29` — ends `29` (`)`) with no trailing byte. Pure ASCII. 🟢
- **Not observed at all:** `POINT Z`, `POINT M`, a CRS URI inside the literal (`<http://www.opengis.net/def/crs/…> POINT(...)`), scientific notation, a leading `+`, `POLYGON`, `LINESTRING`, or a trailing-whitespace variant. 🟢 *(These were specifically looked for per §4; none exist.)*

### The two spacing variants — both common

| Form | Count | Note |
|---|---|---|
| `POINT (lon lat)` — **space before paren** | 444,048 | **The dominant form** (99.47%) |
| `POINT(lon lat)` — no space | 2,161 | 0.48% |

The plan's regexes use `POINT\\s*\\(`, which handles both. 🟢 **No change needed** — but any hand-written parser that assumes `POINT(` will miss 99.5% of the graph, and one that assumes `POINT (` will miss 2,161 rows (including Tagaung Taung, the only genuine coordinate flip in the graph).

### The exceptions — 217 rows invisible to every probe

| Form | Count | Why it's invisible |
|---|---|---|
| `MULTIPOINT(…)` (10 sign/decimal variants) | **215** | Regex is anchored `^\s*POINT`; `MULTIPOINT` fails at char 1 |
| `MULIPOINT(#.# #.#)` | **1** | **Misspelled geometry keyword** — malformed literal in the graph |
| `POINT (-#.# NaN)` | **1** | **Literal `NaN` as latitude** |

**Parse coverage: 446,209 / 446,426 = 99.951%.** 🟢 (`P0.6-parse-coverage`, and independently reproduced by summing `P0.3`'s histogram — the two agree exactly.)

This is **above** the ~95% floor in §11, so the run continued. The 217 invisible rows are a known, bounded, enumerated blind spot — not an unknown one. Every count in this report is a lower bound by at most 217.

---

## 2. Literal-vs-IRI resolution for `:country` on state entities

**This was the plan's open question. Answer: `:country` on a `:StateOrProvince` is a plain LITERAL. `:normalized_uri` on a candidate is an IRI.** 🟢

Raw bindings from `2a.json`, row 3, verbatim:

```json
"state_ent":     { "type": "uri",     "value": "https://minmod.isi.edu/resource/Q5307" }
"state_country": { "type": "literal", "value": "Q1177" }
"country_ent":   { "type": "uri",     "value": "https://minmod.isi.edu/resource/Q1235" }
"state_conf":    { "type": "literal", "datatype": "http://www.w3.org/2001/XMLSchema#decimal", "value": "0.9999" }
"state_src":     { "type": "literal", "value": "UMN Matching System-ProcMinev2" }
```

Note `state_country` has **no `"datatype"` key** — a plain literal, i.e. `xsd:string`. It is a bare Q-id with no namespace.

**Therefore:** joining a state's country to a site's normalized country requires stripping the IRI prefix from the IRI side only. Probe 2b's
`BIND(REPLACE(STR(?country_ent), "^.*/", "") AS ?country_id)` is **correct as written**, and `REPLACE(STR(?state_country_raw), "^.*/", "")` is a harmless no-op on the literal side. 🟢 The script can reuse this join unchanged.

To go from the literal back to an entity, `2e`/`2f` confirm the working pattern:
`BIND(IRI(CONCAT("https://minmod.isi.edu/resource/", STR(?country_raw))) AS ?ce)`. 🟢

---

## 3. Candidate list cardinality

| | 0 candidates | **1** | 2 | 3 | 4 | 5 | max |
|---|---|---|---|---|---|---|---|
| `:country` | 955 | **450,570** | 2 | — | — | — | **2** |
| `:state_or_province` | 29,972 | **421,524** | 28 | 1 | 1 | 1 | **5** |

Modal = **1** for both. 🟢 Denominator is the 451,527 sites carrying `:location_info`.

---

## 4. Which fields are reliably populated, and which are effectively optional

**On `:MineralSite`** (n = 679,781) — `P0.1-mineralsite` 🟢

| Predicate | Sites | Coverage | Verdict |
|---|---|---|---|
| `:record_id`, `:source_id`, `:reference`, `:created_by`, `:modified_at` | 679,781 | **100%** | mandatory |
| `:location_info` | 451,527 | 66.4% | **optional — 228,254 sites have no location at all** |
| `rdfs:label` (the site name) | 438,655 | 64.5% | optional |
| `:site_type` | 340,128 | 50.0% | optional |
| `:site_rank` | 175,130 | 25.8% | optional |
| `:geology_info` | 38,442 | 5.7% | optional |
| `:discovered_year` | 10,933 | 1.6% | rare |
| **`:name`** | **0** | **0%** | **does not exist** |

**On `:LocationInfo`** (n = 451,527) — `P0.1-locationinfo` 🟢

| Predicate | Subjects | Coverage | Verdict |
|---|---|---|---|
| `:country` | 450,572 | 99.79% | effectively mandatory |
| **`:crs`** | **450,247** | **99.72%** | **effectively mandatory — not optional as the plan assumed** |
| `:location` (WKT) | 446,426 | 98.87% | effectively mandatory; 5,101 `LocationInfo` nodes carry no WKT |
| `:state_or_province` | 421,555 | 93.36% | optional |

**On `:CandidateEntity`** (n = 3,407,081) — `P0.1-candidateentity` 🟢

| Predicate | Subjects | Coverage | Verdict |
|---|---|---|---|
| `:source` | 3,407,081 | **100%** | mandatory |
| `:confidence` | 3,407,081 | **100%** | mandatory |
| `:observed_name` | 3,366,629 | 98.81% | near-mandatory |
| `:normalized_uri` | 3,182,495 | **93.41%** | **optional — 224,586 candidates never normalized** |

`:confidence` is `xsd:decimal`; `:source` and `:observed_name` are plain literals; `:normalized_uri` is an IRI. 🟢

**Population baselines** (`P0.2-baselines`, the denominators for everything else) 🟢

| Metric | Raw count |
|---|---|
| Total `:MineralSite` | **679,781** |
| …with `:location_info` | 451,527 |
| …with a `:location` WKT | **446,426** |
| …with **no** `:location_info` | 228,254 |
| `:location_info` present but no WKT | 5,101 |

679,781 matches the plan's raw figure exactly. 🟢

---

## 5. Every field a fix script would need to read or write

| Field | Path | Exists? | Term type | Note for the script |
|---|---|---|---|---|
| site id | `?site` | ✅ | uri | `mr:site__<source-slug>__<record>__<team>` |
| site name | `?site rdfs:label` | ✅ | literal | **NOT `:name`** |
| source | `?site :source_id` | ✅ | literal (a URL string, not an IRI) | 48 distinct values |
| coordinates | `?li :location` | ✅ | plain literal `xsd:string` | one WKT string, lon first; **rewriting means rewriting the whole string** |
| **CRS** | `?li :crs / :normalized_uri / rdfs:label` | ✅ 99.7% | literal e.g. `EPSG:4326` | **must be read before interpreting any coordinate** |
| CRS observed | `?li :crs / :observed_name` | ✅ mostly | literal | can be unbound while the label is bound — see §6 |
| country candidate | `?li :country` | ✅ | uri → `:CandidateEntity` | 1 per site in practice |
| country observed | `?cc :observed_name` | ✅ | literal | free text: `Myanmar`, `Myanmar (Burma)`, `Burma` all occur for one place |
| country entity | `?cc :normalized_uri` | ✅ 93% | uri | can be **unbound** while `:observed_name` is bound |
| state candidate | `?li :state_or_province` | ✅ | uri → `:CandidateEntity` | absent on 29,972 sites |
| state entity | `?sc :normalized_uri` | ✅ | uri | **the field a repoint would write** |
| state→country | `?state_ent :country` | ✅ | **plain literal** bare Q-id | **not an IRI** |
| matcher name | `?sc :source` | ✅ 100% | literal | 4 distinct matchers seen |
| matcher confidence | `?sc :confidence` | ✅ 100% | `xsd:decimal` | discriminative — see `PROBE_REPORT.md` §2 |
| **an explicit precision field** | — | ❌ | — | **does not exist.** Adriana's error-propagation need has nowhere to live today. |
| **a per-record provenance/edit marker** | — | ❌ (only `:created_by`, `:modified_at`) | — | no `owl:sameAs`-back-link convention visible on 100% of records (`owl:sameAs` is on 198,118 sites, 29%) |

---

## 6. Per-variable table (every variable in every probe)

Term type is taken from the JSON binding's `"type"` field. "Example" is verbatim from the response with spaces shown as `·`. "Rows per site" is computed over the `?site` variable where present.

| Probe | Variable | Term type | Datatype IRI | Lang | Example (verbatim, `·`=space) | % unbound | Rows per site |
|---|---|---|---|---|---|---|---|
| 1a | `site` | unbound | — | — | — | **100%** | n/a |
| 1a | `name` | unbound | — | — | — | **100%** | n/a |
| 1a | `source` | unbound | — | — | — | **100%** | n/a |
| 1a | `wkt` | unbound | — | — | — | **100%** | n/a |
| 1a | `crs_obs` | unbound | — | — | — | **100%** | n/a |
| 1a | `crs_label` | unbound | — | — | — | **100%** | n/a |
| 1a | `country_obs` | unbound | — | — | — | **100%** | n/a |
| 1a | `country_ent` | unbound | — | — | — | **100%** | n/a |
| 1a | `state_obs` | unbound | — | — | — | **100%** | n/a |
| 1a | `state_ent` | unbound | — | — | — | **100%** | n/a |
| 1a-alt-harts | `site` | uri | — | — | `https://minmod.isi.edu/resource/site__mrdata…` | 0.0% | 1.00 |
| 1a-alt-harts | `name` | literal | — | — | `Pay·Off-Harts·Draw` | 0.0% | 1.00 |
| 1a-alt-harts | `source` | literal | — | — | `https://mrdata.usgs.gov/mrds` | 0.0% | 1.00 |
| 1a-alt-harts | `wkt` | literal | — | — | `POINT·(-109.4878899999999931·37.933889999999…` | 0.0% | 1.00 |
| 1a-alt-harts | `crs_obs` | literal | — | — | `EPSG:4326` | 0.0% | 1.00 |
| 1a-alt-harts | `crs_label` | literal | — | — | `EPSG:4326` | 0.0% | 1.00 |
| 1a-alt-harts | `country_obs` | literal | — | — | `United·States` | 0.0% | 1.00 |
| 1a-alt-harts | `country_ent` | uri | — | — | `https://minmod.isi.edu/resource/Q1235` | 0.0% | 1.00 |
| 1a-alt-harts | `state_obs` | literal | — | — | `Utah` | 0.0% | 1.00 |
| 1a-alt-harts | `state_ent` | uri | — | — | `https://minmod.isi.edu/resource/Q6897` | 0.0% | 1.00 |
| 1a-alt-tagaung | `site` | uri | — | — | `https://minmod.isi.edu/resource/site__doi-or…` | 0.0% | 1.00 |
| 1a-alt-tagaung | `name` | literal | — | — | `Tagaung·Taung` | 0.0% | 1.00 |
| 1a-alt-tagaung | `source` | literal | — | — | `https://doi.org/10.5382/econgeo.4950` | 0.0% | 1.00 |
| 1a-alt-tagaung | `wkt` | literal | — | — | `POINT(23.63453·96.16317)` | 0.0% | 1.00 |
| 1a-alt-tagaung | `crs_obs` | literal | — | — | `EPSG:4326` | 16.7% | 1.00 |
| 1a-alt-tagaung | `crs_label` | literal | — | — | `EPSG:4326` | 0.0% | 1.00 |
| 1a-alt-tagaung | `country_obs` | literal | — | — | `Myanmar` | 0.0% | 1.00 |
| 1a-alt-tagaung | `country_ent` | uri | — | — | `https://minmod.isi.edu/resource/Q1149` | 16.7% | 1.00 |
| 1a-alt-tagaung | `state_obs` | literal | — | — | `Sagaing` | 66.7% | 1.00 |
| 1a-alt-tagaung | `state_ent` | unbound | — | — | — | **100%** | 1.00 |
| 1b | `crs_label` | literal | — | — | `EPSG:2994` | 0.0% | n/a |
| 1b | `sites` | literal | `http://www.w3.org/2001/XMLSchema#integer` | — | `23316` | 0.0% | n/a |
| 1c | `site` | uri | — | — | `https://minmod.isi.edu/resource/site__www-or…` | 0.0% | 1.00 |
| 1c | `name` | unbound | — | — | — | **100%** | 1.00 |
| 1c | `source` | literal | — | — | `http://www.oregongeology.org` | 0.0% | 1.00 |
| 1c | `lon` | literal | `http://www.w3.org/2001/XMLSchema#double` | — | `1116711.6013779491e0` | 0.0% | 1.00 |
| 1c | `lat` | literal | `http://www.w3.org/2001/XMLSchema#double` | — | `1418219.7509842515e0` | 0.0% | 1.00 |
| 1c | `crs_label` | literal | — | — | `EPSG:2994` | 0.0% | 1.00 |
| 1c | `country_obs` | literal | — | — | `United·States` | 0.0% | 1.00 |
| 1c | `state_obs` | literal | — | — | `Oregon` | 0.0% | 1.00 |
| 1e | `bucket` | literal | — | — | `A_90_to_180` | 0.0% | n/a |
| 1e | `sites` | literal | `http://www.w3.org/2001/XMLSchema#integer` | — | `1` | 0.0% | n/a |
| 2a | `site` | uri | — | — | `https://minmod.isi.edu/resource/site__mrdata…` | 0.0% | 1.00 |
| 2a | `name` | unbound | — | — | — | **100%** | 1.00 |
| 2a | `wkt` | literal | — | — | `POINT·(-82.0400142109·30.0135714563)` | 0.0% | 1.00 |
| 2a | `state_obs` | literal | — | — | `Florida` | 0.0% | 1.00 |
| 2a | `state_ent` | uri | — | — | `https://minmod.isi.edu/resource/Q6920` | 0.0% | 1.00 |
| 2a | `state_label` | literal | — | — | `Florida` | 0.0% | 1.00 |
| 2a | `state_country` | literal | — | — | `Q1237` | 0.0% | 1.00 |
| 2a | `country_obs` | literal | — | — | `United·States` | 0.0% | 1.00 |
| 2a | `country_ent` | uri | — | — | `https://minmod.isi.edu/resource/Q1235` | 0.0% | 1.00 |
| 2a | `country_label` | literal | — | — | `United·States` | 0.0% | 1.00 |
| 2a | `state_src` | literal | — | — | `UMN·Matching·System·v1` | 0.0% | 1.00 |
| 2a | `state_conf` | literal | `http://www.w3.org/2001/XMLSchema#decimal` | — | `1.0` | 0.0% | 1.00 |
| 2b | `state_label` | literal | — | — | `Florida` | 0.0% | n/a |
| 2b | `state_country_label` | literal | — | — | `Puerto·Rico` | 0.0% | n/a |
| 2b | `country_label` | literal | — | — | `United·States` | 0.0% | n/a |
| 2b | `sites` | literal | `http://www.w3.org/2001/XMLSchema#integer` | — | `1609` | 0.0% | n/a |
| 2c | `label` | literal | — | — | `Central·Province` | 0.0% | n/a |
| 2c | `entities` | literal | `http://www.w3.org/2001/XMLSchema#integer` | — | `5` | 0.0% | n/a |
| 2c | `countries` | literal | — | — | `Q1131,·Q1170,·Q1202,·Q1209,·Q1248` | 0.0% | n/a |
| 2d | `state_src` | literal | — | — | `UMN·Matching·System-ProcMinev2` | 0.0% | n/a |
| 2d | `state_conf` | literal | `http://www.w3.org/2001/XMLSchema#decimal` | — | `0.9999` | 0.0% | n/a |
| 2d | `sites` | literal | `http://www.w3.org/2001/XMLSchema#integer` | — | `2058` | 0.0% | n/a |
| 3a | `source` | literal | — | — | `https://doi.org/10.34191/OFR-757` | 0.0% | n/a |
| 3a | `lat_dp` | literal | `http://www.w3.org/2001/XMLSchema#integer` | — | `0` | 0.0% | n/a |
| 3a | `sites` | literal | `http://www.w3.org/2001/XMLSchema#integer` | — | `7792` | 0.0% | n/a |
| 3b | `site` | uri | — | — | `https://minmod.isi.edu/resource/site__api-cd…` | 0.0% | 1.00 |
| 3b | `name` | unbound | — | — | — | **100%** | 1.00 |
| 3b | `source` | literal | — | — | `https://api.cdr.land/v1/docs/documents` | 0.0% | 1.00 |
| 3b | `wkt` | literal | — | — | `POINT(0·0)` | 0.0% | 1.00 |
| 3b | `country_obs` | literal | — | — | `Madagascar` | 14.7% | 1.00 |
| 3c | `source` | literal | — | — | `http://www.oregongeology.org` | 0.0% | n/a |
| 3c | `sites` | literal | `http://www.w3.org/2001/XMLSchema#integer` | — | `9593` | 0.0% | n/a |

### Notes on specific bindings

- **`1a` is all-unbound because it returned zero rows.** Not a data property — a broken query. See §0.
- **`?crs_obs` can be unbound while `?crs_label` is bound.** Seen on the Tagaung Taung `usc` record: the `:crs` candidate has a `:normalized_uri` resolving to a labelled entity but no `:observed_name`. This is exactly the three-way distinction §5/1b asks for, and it means **`:crs` presence must be tested via `:normalized_uri`, not via `:observed_name`.** 🟢
- **`?country_ent` can be unbound while `?country_obs` is bound.** Seen on `site__mrdata-usgs-gov-laterite__74__umn`: `?country_obs = "Myanmar (Burma)"` normalizes to nothing. 224,586 candidates graph-wide have no `:normalized_uri`. 🟢
- **Numeric values returned by `xsd:double` casts are re-serialised by Fuseki with an `e0` suffix** (`1116711.6013779491e0` in `1c`). That is the *response* format, not the stored string. A script reading `?lon`/`?lat` must accept `e0`; a script reading the stored precision must parse `?wkt` itself. 🟢
- **`:source_id` is a literal string that looks like a URL** (`"https://mrdata.usgs.gov/mrds"`, `"type": "literal"`), not an IRI. Do not treat it as a resource. 🟢
