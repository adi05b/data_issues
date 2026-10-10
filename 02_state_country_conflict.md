# Problem 2 — normalized state's country ≠ normalized country

**Scale:** 5,858 dedup entities.
**Adriana's ask:** review the disagreement CSV. Column D (entity country) does not match column H (`state_belongs_to`).
**Her example:** observed *Florida / United States* → normalized country United States, normalized state Florida, but that Florida entity belongs to Puerto Rico. Mean coordinates (28.82, −82.90) fall in the United States.

## What the vocabulary already tells us (checked 2 Sep, `data/entities/state_or_province.csv`)

| Observed | Normalized to | Correct target in vocabulary | Failure class |
|---|---|---|---|
| Florida, US | Q5307 Florida (Puerto Rico) | Q6850 Florida (United States) | **true tie** — three real Floridas (PR, US, UY) |
| La Paz, Bolivia | Q2181 La Pampa (Argentina) | `La Paz Department` (Bolivia) | **suffix** — matcher preferred a different word over the suffixed correct one |
| Potosi, Bolivia | Q5270 Porto (Portugal) | `Potosí Department` | suffix + diacritic |
| Oruro, Bolivia | Q5038 Koror (Palau) | `Oruro Department` | suffix |
| Santa Cruz, Bolivia | Q2190 Santa Cruz (Argentina) | `Santa Cruz Department` | suffix (and a real tie with Argentina) |
| Camaguey, Cuba | Camuy (Puerto Rico) | `Camagüey Province` | suffix + diacritic |
| Bolivar, Venezuela | Bolívar (Colombia) | `Bolívar` (Venezuela) exists | diacritic + tie |
| Saint Andrew, Jamaica | Q2374 Saint Andrew (Barbados) | Q3902 Saint Andrew (Jamaica) exists | true tie |
| Orissa, India | Q3993 Garissa (Kenya) | **none** — vocabulary has only `Odisha` | **vocabulary gap** (renamed 2011) |
| Katanga, DR Congo | Q6152 Tanga (Tanzania) | **none** — split in 2015 into Haut-Katanga, Lualaba, Tanganyika, Haut-Lomami | **vocabulary gap** |

Three distinct classes, three distinct fixes:

1. **Suffix/diacritic** (the bulk — 484 of 5,083 vocabulary labels carry `Department`, `Province`, or `Parish`). Fix the matcher: strip suffixes and fold diacritics before scoring, and constrain candidates to the already-normalized country. Repointing the rows without this regenerates the same rows on the next ETL.
2. **True tie** (Florida, Saint Andrew, Santa Cruz, Bolívar). Fix by filtering state candidates to the normalized country. Coordinates are the tiebreaker where the country is also in doubt. Do not use the vocabulary's own centroids for this: Q5307 (PR) and Q6850 (US) carry the *same* centroid, and Q6920 (Uruguay) sits in Tampa.
3. **Vocabulary gap** (Orissa, Katanga). Add aliases to `state_or_province.csv`. No row-level fix exists.

## Probe 2a — one known row, see how the candidate links

Also answers the open question: is `:country` on a state entity a literal `"Q1233"` or an IRI `mr:Q1233`?

```sparql
PREFIX : <https://minmod.isi.edu/ontology/>
PREFIX mr: <https://minmod.isi.edu/resource/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?site ?name ?wkt ?state_obs ?state_ent ?state_label ?state_country ?country_obs ?country_ent ?country_label ?state_src ?state_conf
WHERE {
  ?site a :MineralSite ; :location_info ?li .
  ?li :state_or_province ?sc .
  ?sc :observed_name ?state_obs ; :normalized_uri ?state_ent .
  FILTER(LCASE(STR(?state_obs)) = "florida")
  OPTIONAL { ?state_ent rdfs:label ?state_label }
  OPTIONAL { ?state_ent :country ?state_country }
  OPTIONAL { ?sc :source ?state_src }
  OPTIONAL { ?sc :confidence ?state_conf }
  OPTIONAL { ?site :name ?name }
  OPTIONAL { ?li :location ?wkt }
  OPTIONAL { ?li :country ?cc .
             OPTIONAL { ?cc :observed_name ?country_obs }
             OPTIONAL { ?cc :normalized_uri ?country_ent . OPTIONAL { ?country_ent rdfs:label ?country_label } } }
}
LIMIT 20
```

Look at `?state_country` and `?country_ent` side by side. If one is `"Q1233"` and the other is `<https://minmod.isi.edu/resource/Q1233>`, the join in 2b needs `STRAFTER`.

## Probe 2b — count the conflict in the raw graph

Written to work whether `:country` on the state is a literal or an IRI.

```sparql
PREFIX : <https://minmod.isi.edu/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?state_label ?state_country_label ?country_label (COUNT(DISTINCT ?site) AS ?sites)
WHERE {
  ?site a :MineralSite ; :location_info ?li .
  ?li :state_or_province ?sc ; :country ?cc .
  ?sc :normalized_uri ?state_ent .
  ?cc :normalized_uri ?country_ent .
  ?state_ent :country ?state_country_raw .
  BIND(REPLACE(STR(?state_country_raw), "^.*/", "") AS ?state_country_id)
  BIND(REPLACE(STR(?country_ent), "^.*/", "") AS ?country_id)
  FILTER(?state_country_id != ?country_id)
  OPTIONAL { ?state_ent rdfs:label ?state_label }
  OPTIONAL { ?country_ent rdfs:label ?country_label }
  BIND(IRI(CONCAT("https://minmod.isi.edu/resource/", ?state_country_id)) AS ?state_country_ent)
  OPTIONAL { ?state_country_ent rdfs:label ?state_country_label }
}
GROUP BY ?state_label ?state_country_label ?country_label
ORDER BY DESC(?sites)
LIMIT 40
```

The top of this list should reproduce Adriana's table (Florida/PR 1,587, La Paz/La Pampa 531, …) at raw-record grain. If it does, the join is right and the script can reuse it.

## Probe 2c — the tie cases only (does the correct target exist?)

```sparql
PREFIX : <https://minmod.isi.edu/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?label (COUNT(DISTINCT ?ent) AS ?entities) (GROUP_CONCAT(DISTINCT ?country_id; separator=", ") AS ?countries)
WHERE {
  ?ent a :StateOrProvince ; rdfs:label ?label ; :country ?c .
  BIND(REPLACE(STR(?c), "^.*/", "") AS ?country_id)
}
GROUP BY ?label
HAVING (COUNT(DISTINCT ?ent) > 1)
ORDER BY DESC(?entities)
LIMIT 50
```

Every label that appears more than once is a potential tie. Cross that against the observed strings in the conflict set.

## Record from the probe

- [ ] Literal vs IRI for `:country` on state entities
- [ ] Raw-grain counts for the top conflict pairs vs Adriana's dedup counts
- [ ] Whether a site carries one state candidate or several (from 2a's row count per site)
- [ ] The `?state_src` values — which extractor produced the bad normalization? (all sources, or one?)
- [ ] The `?state_conf` values — did the matcher report low confidence on the wrong picks? If so, a confidence threshold alone would have caught them.

## Decision after the probe

- Classify every observed string in the 5,858 into suffix / tie / gap using the vocabulary.
- Suffix class → propose the matcher change; row repoints are a stopgap only.
- Tie class → repoint to the candidate whose `country_id` equals the normalized country. Where the country itself is unreliable, geocode the stored point and use its country.
- Gap class → alias rows added to `state_or_province.csv`. Separate PR.

## One-row dry run (step 3)

One Florida record. Repoint `:normalized_uri` on the state candidate from Q5307 to Q6850. Confirm on the live graph. Then one La Paz record → `La Paz Department`. Two dry runs, because the two classes take different code paths.

## Findings

*(paste probe output and notes here)*

---

### Probe run 2026-09-02 — raw output

*Endpoint `https://minmod.isi.edu/sparql` (Fuseki), read-only. Files in `probe-runs/2026-09-02/`. Grain: **raw** (679,781 records).*

#### Probe 2a — 20 rows, TRUNCATED BY LIMIT

Raw JSON bindings, verbatim (row 3) — **this answers the open question**:

```json
"state_ent":     { "type": "uri",     "value": "https://minmod.isi.edu/resource/Q5307" }
"state_country": { "type": "literal", "value": "Q1177" }
"country_ent":   { "type": "uri",     "value": "https://minmod.isi.edu/resource/Q1235" }
"state_conf":    { "type": "literal", "datatype": "http://www.w3.org/2001/XMLSchema#decimal", "value": "0.9999" }
"state_src":     { "type": "literal", "value": "UMN Matching System-ProcMinev2" }
```

**`:country` on a state entity is a plain LITERAL holding a bare Q-id** (no `"datatype"` key -> `xsd:string`, no namespace). `:normalized_uri` is an **IRI**. So the join needs prefix-stripping on the IRI side only — Probe 2b's `REPLACE(STR(?country_ent), "^.*/", "")` is correct as written, and the same `REPLACE` on the literal side is a harmless no-op.

Two distinct wrong Floridas, from two distinct matchers, both at near-maximum confidence:

```
state_ent  state_country  matcher                          confidence   rows
Q6920      Q1237 Uruguay  UMN Matching System v1           1.0             2
Q5307      Q1177 P.Rico   UMN Matching System-ProcMinev2   0.9999         18
```

Normalized country on every row is `Q1235` (United States). Rows-per-site = **1.00** — one state candidate per site.

#### Probe 2e — the three Florida entities (new)

```
ent     label     country_raw   country_label
Q5307   Florida   Q1177         Puerto Rico
Q6850   Florida   Q1235         United States   <- the correct target
Q6920   Florida   Q1237         Uruguay
```

Note the master plan's assumed `Q1233` for the United States is wrong; **it is `Q1235`**.

#### Probe 2b — conflict counts, TRUNCATED BY LIMIT (top 15 of 40)

```
state_label                         state_country_label   country_label      sites
Florida                             Puerto Rico           United States       1609
La Pampa                            Argentina             Bolivia              586
Porto                               Portugal              Bolivia              552
Bolivar                             Colombia              Venezuela            475
Santa Cruz                          Argentina             Bolivia              216
Koror                               Palau                 Bolivia              191
Garissa                             Kenya                 India                187
Camuy                               Puerto Rico           Cuba                 158
Tanga                               Tanzania              DR Congo             112
Saint Andrew                        Barbados              Jamaica               87
Florida                             Uruguay               United States         73
Northern Territory                  Australia             Canada                67
Sanma                               Vanuatu               Cuba                  64
Naama                               Algeria               Panama                62
San Jose                            Uruguay               Costa Rica            56
```

#### Probe 2b-total — the population (new, no limit)

```
conflicting_sites   rows
6156                6159
```

`rows` exceeds `sites` by 3 — the handful of multi-candidate sites. Confirms multiplication is negligible.

#### Reproduction of Adriana's table

| Pair | Adriana (dedup) | This run (raw) | Ratio |
|---|---|---|---|
| Florida / Puerto Rico | 1,587 | **1,609** | **1.014** |
| La Paz / La Pampa | 531 | **586** | **1.104** |
| **Total** | **5,858** | **6,156** | **1.051** |

Raw >= dedup on both, ratios internally consistent. **The join is correct and the script can reuse it.**

#### Probe 2c — duplicate labels, TRUNCATED BY LIMIT (top 12 of 50)

```
label                entities   countries
Central Province         5       Q1131, Q1170, Q1202, Q1209, Q1248
Western Province         5       Q1170, Q1182, Q1202, Q1209, Q1248
Eastern Province         5       Q1182, Q1193, Q1197, Q1209, Q1248
Saint George Parish      4       Q1009, Q1061, Q1087, Q1187
Amazonas                 4       Q1030, Q1047, Q1172, Q1241
Northern Province        4       Q1182, Q1197, Q1209, Q1248
Southern Province        4       Q1182, Q1197, Q1209, Q1248
Saint John Parish        3       Q1009, Q1061, Q1087
Cordoba                  3       Q1010, Q1047, Q1208
La Paz Department        3       Q1025, Q1065, Q1097
Bolivar                  3       Q1047, Q1063, Q1241
Florida                  3       Q1177, Q1235, Q1237
...
Zagreb                   2       Q1053                <- 2 entities, ONE country
```

#### Probe 2f — do the correct targets exist? (new)

```
label                    ent     country
Bolivar                  Q2785   Colombia
Bolivar                  Q3077   Ecuador
Bolivar                  Q6958   Venezuela          <- correct target EXISTS
Camaguey Province        Q2887   Cuba               <- correct target EXISTS
Haut-Katanga             Q3000   DR Congo
La Paz Department        Q2453   Bolivia            <- correct target EXISTS
La Paz Department        Q3132   El Salvador
La Paz Department        Q3556   Honduras
Odisha                   Q3657   India
Oruro Department         Q2454   Bolivia            <- correct target EXISTS
Potosi Department        Q2456   Bolivia            <- correct target EXISTS
Saint Andrew             Q2374   Barbados
Saint Andrew             Q3902   Jamaica            <- correct target EXISTS
Santa Cruz               Q2190   Argentina
Santa Cruz Department    Q2457   Bolivia            <- correct target EXISTS
```

No `Orissa`, no `Katanga`. **Both vocabulary gaps confirmed live.**

#### Probe 2d — confidence distribution on conflicts (new)

Top buckets of 223:

```
matcher                          confidence            sites
UMN Matching System-ProcMinev2   0.9999                 2058
UMN Matching System-ProcMinev2   0.7618130709963556      592
UMN Matching System-ProcMinev2   0.628445435771027       552
UMN Matching System-ProcMinev2   0.8063492063492064      491
UMN Matching System v1           1.0                     322
UMN Matching System-ProcMinev2   0.6517195767195767      191
UMN Matching System-ProcMinev2   0.7763088950788245      187
UMN Matching System-ProcMinev2   0.6457774168433701      158
Inferlink Extraction v3          1.0                      97
UMN Exact Match v1               1.0                      25
```

Cumulative: **conf < 0.9 -> 3,615 (58.7%)** · conf >= 0.9 -> 2,541 (41.3%).

#### Probe 2d-baseline — confidence on ALL state candidates (new)

```
bucket           candidates
hi_ge_0.99          410185
lo_lt_0.9            10732
mid_0.9_0.99           675
```

---

### Notes

1. **Open question answered: `:country` on a state entity is a plain literal bare Q-id, not an IRI.** The plan's 2b join handles this correctly. Reuse it.

2. **The plan's vocabulary analysis survived contact with the graph intact.** Every predicted correct target exists (Q2453 La Paz Department, Q2456 Potosi Department, Q2454 Oruro Department, Q2457 Santa Cruz Department, Q2887 Camaguey Province, Q6958 Bolivar/Venezuela, Q3902 Saint Andrew/Jamaica, Q6850 Florida/US), and both predicted vocabulary gaps are real (no Orissa, no Katanga).

3. **Suffix-stripping alone is insufficient.** `La Paz Department` exists in **three** countries (Bolivia Q2453, El Salvador Q3132, Honduras Q3556). Candidates **must** also be constrained to the already-normalized country. Same for `Santa Cruz`, `Bolivar`, `Saint Andrew`, `Florida`.

4. **Confidence IS a usable signal — the plan's own question, answered yes.** 58.7% of conflicts sit below 0.9 confidence versus **2.5%** of all state candidates: a **~23x enrichment**. A `confidence < 0.9` review gate flags 3,615 of 6,156 conflicts inside a queue of only 10,732 candidates (33.7% precision).

5. **But a threshold is not a fix.** It misses 2,541 conflicts (41.3%), including the single largest bucket — **2,058 Florida -> Q5307 rows at 0.9999** — plus 444 rows at exactly 1.0. The matcher change is still required.

6. **Ties are systemic, not anecdotal.** `Central Province`, `Western Province` and `Eastern Province` each resolve to **five** different countries. Country-constraining is not an optimisation for the Florida edge case; it is the primary mechanism.

7. **Four matchers are in play**, and two of them produce two *different* wrong Floridas: `UMN Matching System v1` -> Q6920 (Uruguay) at conf 1.0, and `UMN Matching System-ProcMinev2` -> Q5307 (Puerto Rico) at conf 0.9999. A fix targeting one matcher leaves the other's rows.

8. **New, not predicted:** `Zagreb` has **2 entities under a single country (Q1053)**. That is a duplicate entity in the vocabulary, not a tie and not a matcher error. Worth a separate check for other same-label-same-country pairs.

#### Checklist from "Record from the probe"

- [x] **Literal vs IRI** — `:country` on a state entity is a **plain literal** bare Q-id (`"Q1177"`). `:normalized_uri` is an **IRI**.
- [x] **Raw vs dedup counts** — total 6,156 raw / 5,858 dedup (1.05). Florida/PR 1,609 / 1,587 (1.014). La Paz/La Pampa 586 / 531 (1.104). Consistent.
- [x] **One state candidate or several** — **one**. 421,524 of 451,527 sites carry exactly 1; only 31 carry more. Rows-per-site on 2a = 1.00.
- [x] **`?state_src` values** — four matchers: `UMN Matching System-ProcMinev2` (dominant), `UMN Matching System v1`, `Inferlink Extraction v3`, `UMN Exact Match v1`. **Not one extractor — several.**
- [x] **`?state_conf` values** — spread 0.50-1.0, **not** a constant. Discriminative (~23x enrichment below 0.9) but incomplete: the largest single wrong bucket sits at 0.9999.

