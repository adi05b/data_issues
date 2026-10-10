# P2_AFFECTED_RECORDS.md — which records are affected

*Aditi Bombe · run 2026-09-14 · follow-up to `P2_DIAGNOSIS.md` (root cause, not in scope here) · **read-only**, 9 queries, nothing written.*
*Record in `probe-runs/2026-09-14/`. Confidence: 🟢 verified from a saved response · 🟡 likely · 🔴 assumed.*

**Endpoint reachable.** The certificate was renewed — new cert valid `Sep 1 2026 → Mar 19 2027`, issuer `InCommon Intermediate CA - DVG2C`. Gate `ASK { ?s ?p ?o }` returned `true` at 19:16:36Z. 🟢 `p2.0-gate.json`

**Every number below traces to a saved response file in `probe-runs/2026-09-14/`.** Adriana's spreadsheet appears once, in section 7, as a comparison.

---

## Bottom line

**6,156 records across 19 sources.** The pull reconciles exactly and the population is now fully enumerated and classified. Three things this run establishes that were not known:

1. **Matcher assignment is per-source, not per-record.** 19 sources, 20 (source, matcher) cells — every source is handled by exactly one matcher except `api.cdr.land`, which has two. So the question the brief posed ("one matcher failing everywhere, or one source handled badly?") has a third answer: **the two are confounded by construction** and cannot be separated from this table alone. 🟢
2. **`UMN Matching System-ProcMinev2` owns 92% of the damage** (5,668 of 6,156) — but its *rate* is 1.89%, mid-pack. **`Inferlink Extraction v3` fails at 8.51%, 4.5× worse**, and `SAND` at 11.56%. The volume leader and the quality problem are different matchers. 🟢
3. **The country constraint alone fixes almost everything.** Of the 2,282 "Other" rows — the hardest class — **2,279 (99.87%) have the correct target already in the vocabulary under the record's own country.** 🟢

**And the cross-check found a defect neither side was looking for.** Six records Adriana flags are **internally consistent in the graph** — I queried all six directly and their state's country equals their normalized country. Her rows carry a country that is not in the record she names. That is a **merge-induced conflict**, not a matcher failure, and it belongs to a different owner. 🟢 See §7.

---

## The table

| Source id | Team tag | Affected | Source total | Rate | Dominant matcher | Likely repo path 🔴 | Sample record ids |
|---|---|---|---|---|---|---|---|
| `https://mrdata.usgs.gov/mrds` | `umn` | **5,586** | 479,760 | 1.16% | UMN Matching System-ProcMinev2 | `…/mineral-sites/umn/mrdata-usgs-gov-mrds/` | `10003814`, `10003815`, `10003816` |
| `https://doi.org/10.5066/P9K1HBNT` | `umn` | 179 | 685 | **26.13%** | UMN Matching System v1 | `…/umn/doi-org-10-5066-p9k1hbnt/` | `100`, `101`, `103` |
| `https://api.cdr.land/v1/docs/documents` | `inferlink` | 98 | 15,421 | 0.64% | Inferlink Extraction v3 (97) + v2 (1) | `…/inferlink/api-cdr-land-v1-docs-documents/` | `0200ab064d1f…`, `02028cde67ee…` |
| `https://mrdata.usgs.gov/vms` | `umn` | 82 | 2,178 | 3.76% | UMN Matching System-ProcMinev2 | `…/umn/mrdata-usgs-gov-vms/` | `1053`, `1069`, `1070` |
| `https://mrdata.usgs.gov/phosphate` | `umn` | 71 | 2,790 | 2.54% | UMN Matching System v1 | `…/umn/mrdata-usgs-gov-phosphate/` | `112`, `113`, `114` |
| `https://mrdata.usgs.gov/nicrpge` | `umn` | 25 | 32,998 | 0.08% | UMN Matching System v1 | `…/umn/mrdata-usgs-gov-nicrpge/` | `12160134`, `12160135` |
| `https://mrdata.usgs.gov/major-deposits` | `umn` | 24 | 5,938 | 0.40% | UMN Matching System v1 | `…/umn/mrdata-usgs-gov-major-deposits/` | `697`, `700`, `701` |
| `https://mrdata.usgs.gov/ree` | `umn` | 20 | 1,563 | 1.28% | UMN Matching System v1 | `…/umn/mrdata-usgs-gov-ree/` | `109`, `134`, `167` |
| `https://doi.org/10.2113/econgeo.110.8.1925` | `usc` | 17 | 267 | 6.37% | SAND | `…/usc/doi-org-10-2113-econgeo-110-8-1925/` | `afrikanda__218`, `aryskan__220` |
| `https://doi.org/10.5066/P99RK9SU` | `usc-stu` | 15 | 73 | **20.55%** | SAND | `…/usc-stu/doi-org-10-5066-p99rk9su/` | `amitsoq`, `black-range-deposit` |
| `https://mrdata.usgs.gov/porcu` | `umn` | 13 | 1,376 | 0.94% | UMN Exact Match v1 | `…/umn/mrdata-usgs-gov-porcu/` | `11`, `12`, `14` |
| `https://doi.org/10.3133/pp1802J` | `usc-stu` | 10 | 108 | **9.26%** | SAND | `…/usc-stu/doi-org-10-3133-pp1802j/` | `29`, `33`, `48` |
| `https://mrdata.usgs.gov/deposit` | `umn` | 8 | 445 | 1.80% | UMN Exact Match v1 | `…/umn/mrdata-usgs-gov-deposit/` | `FL00001`, `FL00003` |
| `https://mrdata.usgs.gov/pp1802` | `umn` | 2 | 412 | 0.49% | UMN Matching System v1 | `…/umn/mrdata-usgs-gov-pp1802/` | `1641`, `1861` |
| `https://mrdata.usgs.gov/sedznpb` | `umn` | 2 | 1,004 | 0.20% | UMN Exact Match v1 | `…/umn/mrdata-usgs-gov-sedznpb/` | `7`, `8` |
| `https://doi.org/10.31035/cg2020009` | `usc-stu` | 1 | 20 | 5.00% | SAND | `…/usc-stu/doi-org-10-31035-cg2020009/` | `nei-mongol` |
| `https://mrdata.usgs.gov/carbonatite` | `umn` | 1 | 119 | 0.84% | UMN Matching System v1 | `…/umn/mrdata-usgs-gov-carbonatite/` | `9` |
| `https://mrdata.usgs.gov/sedcu` | `umn` | 1 | 1,563 | 0.06% | UMN Exact Match v1 | `…/umn/mrdata-usgs-gov-sedcu/` | `274` |
| `https://mrdata.usgs.gov/sir20105090z` | `umn` | 1 | 5,487 | 0.02% | UMN Exact Match v1 | `…/umn/mrdata-usgs-gov-sir20105090z/` | `10325` |
| | | **6,156** | | | | | |

Repo paths are 🔴 — inferred from the team tag in the site URI, not checked against a checkout. `p2.1a`, `p2.1b`, `p2.2a`, `p2.3`.

**The two orderings disagree sharply.** By volume, `mrds` is 90.7% of the problem at a 1.16% rate. By rate, `mrds` is 10th — the worst offenders are **`P9K1HBNT` at 26.13%** (179 of 685) and **`P99RK9SU` at 20.55%** (15 of 73), both small DOI feeds. Four of the top five by rate are DOI-sourced `usc`/`usc-stu` feeds running SAND. Fixing `mrds` fixes the most records; fixing the SAND path fixes the most broken *feeds*.

---

## Reconciliation — done before classifying 🟢

| Check | Result |
|---|---|
| Section 3 rows retrieved | 6,159 |
| Section 3 **distinct sites** | **6,156** |
| Section 1 sum of `?affected` | **6,156** |
| Match | **✅ exact** |
| Per-source reconciliation | **✅ all 19 sources match individually** |
| Retrieved without `LIMIT` | yes — no pagination needed, `truncated_by_limit: false` |

The 3 excess rows are **3 `api.cdr.land` sites carrying two state candidates each** — the row multiplication earlier runs predicted. `candidate lists are singletons in practice` holds at 6,153/6,156. Counts in this report are **distinct sites** except in section 5, which is row-based and noted as such. `p2_reconcile.py`

**Team tags** (distinct-site basis): `umn` 6,015 · `inferlink` 98 · `usc-stu` 26 · `usc` 17. 🟢

---

## Matcher cross-tab 🟢

Nobody had built this. `p2.2a`

| Matcher | Conflicts | Sources it appears on |
|---|---|---|
| UMN Matching System-ProcMinev2 | 5,668 | mrds, vms |
| UMN Matching System v1 | 322 | P9K1HBNT, phosphate, nicrpge, major-deposits, ree, pp1802, carbonatite |
| Inferlink Extraction v3 | 97 | api.cdr.land |
| SAND | 43 | econgeo.110.8.1925, P99RK9SU, pp1802J, cg2020009 |
| UMN Exact Match v1 | 25 | porcu, deposit, sedznpb, sedcu, sir20105090z |
| Inferlink Extraction v2 | 1 | api.cdr.land |

**Each source has exactly one matcher, except `api.cdr.land` (v3 + v2).** The brief's two hypotheses are therefore not separable from this cross-tab — matcher and source vary together. What the table *does* show is that one matcher (`ProcMinev2`) spans only two sources yet carries 92% of the volume, because one of those two is `mrds`.

### Matcher rates — the volume leader is not the quality problem 🟢

Conflicts ÷ all state candidates that matcher produced. `p2.2b`

| Matcher | Conflicts | Candidates | Rate |
|---|---|---|---|
| **Inferlink Extraction v2** | 1 | 5 | **20.00%** |
| **SAND** | 43 | 372 | **11.56%** |
| **Inferlink Extraction v3** | 97 | 1,140 | **8.51%** |
| UMN Matching System-ProcMinev2 | 5,668 | 300,045 | 1.89% |
| UMN Exact Match v1 | 25 | 1,839 | 1.36% |
| UMN Matching System v1 | 322 | 114,857 | **0.28%** |

**`Inferlink v3` and `SAND` are 4.5×–6× worse than `ProcMinev2` per candidate**, on small volumes. These are the forward risk the brief asked about: if either is scaled to a large feed, it will produce conflicts at several times the current rate. `Inferlink v2`'s 20% is 1-of-5 and not meaningful on its own 🟡, but it is the same family as v3.

Four user accounts (`jhammars`, `caknoblock`, `bvu`, `glederer`) appear as candidate sources with **0 conflicts in 29 candidates** — manual curation, clean so far. 🟢

---

## Classification — all 6,159 rows 🟢

Applied in the brief's order, each test kept narrow. Row-based, not site-based. `p2_classify2.py` → `p2.5-classified.csv`

| Class | Rows | Share | Who fixes it |
|---|---|---|---|
| **Other** | **2,282** | **37.05%** | see below — inspected in full |
| **Homonym** | 2,210 | 35.88% | matcher — country constraint alone |
| **Not in the list** | 781 | 12.68% | vocabulary — new entry or alias |
| **Accent** | 558 | 9.06% | matcher — diacritic folding |
| **Two-letter code** | 184 | 2.99% | extraction — the name never arrived |
| **Stray punctuation** | 107 | 1.74% | string cleaning, before matching |
| **No observed name** | 25 | 0.41% | — `:state_or_province` normalized with no `observed_name` |
| **Suffix** | 12 | 0.19% | matcher — suffix stripping |

Examples: Homonym `'Nevada'`→Nevada (US) on a **Canada** record; Accent `'San Jose'`→`'San José'` (Uruguay) on a **Costa Rica** record; Two-letter `'CA'`→`'Canelones'` (Uruguay) on a **US** record; Stray punctuation `'Yukon Territory*'`→`'Northern Territory'` (Australia).

**"No observed name" is a class the brief did not anticipate** — 25 rows where the state candidate has a `normalized_uri` but no `observed_name` at all. Every one normalizes to `'Florida'` (Uruguay) on a United States record. A matcher produced a confident match from **nothing**. 🟢

**Suffix is only 12 rows, not the large class earlier framing implied.** The suffix cases that matter (`La Paz` → `La Paz Department`) are *failures to match a suffixed vocabulary entry*, which land in Other — not observed-vs-matched suffix differences.

### Every distinct "Other" string — 110 distinct, 2,282 rows 🟢

Full list in `p2_classify2.py` output; the head, with the decisive column:

| Rows | Observed | Matched to | Record country → matched state's country | Correct target exists under own country |
|---|---|---|---|---|
| 592 | `La Paz` | `La Pampa` | Bolivia → Argentina | ✅ |
| 553 | `Potosi` | `San Luis Potosí` | Bolivia → Mexico | ✅ |
| 191 | `Oruro` | `Koror` | Bolivia → Palau | ✅ |
| 158 | `Camaguey` | `Camuy` | Cuba → Puerto Rico | ✅ |
| 64 | `Granma` | `Sanma` | Cuba → Vanuatu | ✅ |
| 62 | `Panama` | `Naama` | Panama → Algeria | ✅ |
| 51 | `Veraguas` | `Caguas` | Panama → Puerto Rico | ✅ |
| 44 | `Akita` | `Latakia` | Japan → Syria | ✅ |
| 43 | `Colon` | `Colonia` | Panama → Uruguay | ✅ |
| 39 | `Midlands` | `Islands` | Zimbabwe → Hong Kong S.A.R. | ✅ |
| … | *100 more, each listed in the run output* | | | |
| 2 | `Para` | `Paraná` | Suriname → Brazil | ❌ |
| 1 | `Northwest Region` | `Northwestern Region` | Yemen → Iceland | ❌ |

**Other is not heterogeneous — it is one failure mode with 110 surface forms:** the matcher chose an orthographically similar entry in the wrong country when a correct entry existed. **2,279 of 2,282 rows (99.87%) have the right target in the vocabulary under the record's own country**, so the country constraint resolves them. I am reporting this as inspection of Other, not by widening a class — the rows stay in Other. 🟢

Only **3 rows** genuinely lack a target: `Para` (Suriname) ×2 and `Northwest Region` (Yemen) ×1. Those are vocabulary gaps.

---

## Vocabulary 🟢

`p2.4` returns **5,084 `:StateOrProvince` entities**, every one with a `:country`, no entity on more than one row.

**The graph disagrees with the earlier CSV figure of 5,083 by exactly one.** The graph wins. The discrepancy is one entity — too small to explain any finding here, but it confirms the CSV is a stale copy and should not be the basis for vocabulary claims. 🟢

**5,084 entities carry only 4,967 distinct labels** — 117 labels are shared across countries. That is the structural precondition for the entire Homonym class: 2,210 rows fail because a name legitimately exists in more than one country and nothing constrains the choice. 🟢

---

## Damage by country, ranked by share 🟢

`p2.6` + `p2.3`. All 100 countries with ≥1 affected record; full list in the run output.

| Share | Affected | Total | Country |
|---|---|---|---|
| **88.34%** | 1,584 | 1,793 | **Bolivia** |
| **77.78%** | 7 | 9 | **Belize** |
| **74.42%** | 509 | 684 | **Venezuela** |
| **69.13%** | 215 | 311 | **Panama** |
| **56.41%** | 22 | 39 | **El Salvador** |
| 38.15% | 140 | 367 | Jamaica |
| 34.03% | 114 | 335 | DR Congo |
| 33.33% | 2 | 6 | Central African Republic |
| 30.48% | 82 | 269 | Honduras |
| 29.31% | 17 | 58 | Guinea |
| 28.81% | 17 | 59 | Austria |
| 28.16% | 227 | 806 | Cuba |
| 25.11% | 117 | 466 | Costa Rica |
| 24.84% | 157 | 632 | Japan |
| 23.67% | 67 | 283 | Zambia |
| … | | | *85 more* |
| 0.49% | 1,867 | 383,539 | United States |
| 0.05% | 2 | 4,363 | Chile |

**Bolivia is 88% destroyed.** Nearly nine in ten Bolivian mineral sites carry a state belonging to another country. Venezuela (74%), Panama (69%) and El Salvador (56%) are comparably broken. **The United States has the second-largest absolute count (1,867) at a 0.49% rate** — the volume view and the share view point at completely different countries, and only the share view shows that Latin America is effectively unusable for state-level analysis. 🟢

**84 of 184 countries have zero affected records** 🟢 — including Poland, Ukraine, Switzerland, Thailand, Kenya, Tanzania, Iran, Iraq, Israel, Saudi Arabia. Reading across them, the surviving conventions are: names that are **long and distinctive** (Antananarivo-class), names with **no short near-neighbour** in another country's list, and countries whose subdivisions are **transliterated consistently**. The failures cluster on **short Spanish/Japanese names** (`Colon`, `Limon`, `Nara`, `Gifu`, `Oita`) where a 4–6 character string has many near-matches across 5,084 entries. 🟡

---

## Cross-check against Adriana's export 🟢

`state_country_disagreements.xlsx` — 5,799 rows, 5,797 distinct `dedup_site_id`, 5,797 distinct `source_refid`. Hers are merged entities; mine are underlying records. `p2_xcheck.py`

| | Count |
|---|---|
| Her distinct `source_refid` | 5,797 |
| My distinct sites | 6,156 |
| **In both** | **5,791** |
| **Only mine** (her gap) | **365** |
| **Only hers** (my query misses) | **6** |

Ratio 1.062, and consistent across named cases — `Florida` 1.02, `La Paz` 1.10, `Potosi` 1.05, `Bolivar` 1.01, `Camaguey` 1.04, `Saint Andrew` 1.00, `Granma` 1.00. Two run hotter: `Orissa` 1.23 and `Santa Cruz` 1.15. The joins agree. 🟢

### The six she found that I miss — my query is not wrong 🟢

The brief says a record she found that my query misses means my query is wrong. **I queried all six directly rather than assume it.** `p2.7-missed-six`

| Record | Its state → state's country | Its normalized country | Conflict? | Her `entity_country` |
|---|---|---|---|---|
| `phosphate__95__umn` | Queensland → Q1013 | Australia (Q1013) | **no** | New Zealand |
| `phosphate__1__umn` | Helmand → Q1000 | Afghanistan (Q1000) | **no** | Pakistan |
| `api-cdr-land…__inferlink` | British Columbia → Q1038 | Canada (Q1038) | **no** | Portugal |
| `phosphate__1210__umn` | Roi Et → Q1219 | Thailand (Q1219) | **no** | Solomon Islands |
| `p96mmrfd__md055__umn` | Alaska → Q1235 | United States (Q1235) | **no** | Uganda |
| `sedznpb__493__umn` | Alaska → Q1235 | United States (Q1235) | **no** | Uganda |

**All six are internally consistent: state's country equals normalized country, exactly.** My query correctly excludes them. The country in her row — New Zealand, Pakistan, Portugal, Solomon Islands, Uganda — **is not present anywhere in the record she names**.

So this is not a gap in my query. It is a **conflict created by the merge**: the dedup entity took its country from one constituent record and its state from another, producing a contradiction that exists in neither. 🟢 (That the country arrives from a sibling in the same dedup cluster is the natural reading but I cannot see her cluster membership, so the mechanism is 🟡.) Note `sedznpb__493` has **no observed state or country string at all** yet her row asserts both — consistent with the same explanation.

**This is a second, separate defect, owned by the dedup/merge step rather than the matcher.** It is small (6 known) but it is the kind that a matcher fix will not touch.

### The 365 she misses — her check's gap 🟢

By source: `mrds` 221, `P9K1HBNT` 63, `api.cdr.land` 36, `phosphate` 18, `econgeo.110.8.1925` 17, `ree` 7, others 3. By team tag: `umn` 312, `inferlink` 36, `usc` 17, `usc-stu` 1.

Observed strings include `La Paz` ×55, `Florida` ×36, `Orissa` ×35, `Santa Cruz` ×31, `Potosi` ×25, `CA` ×21, `CO` ×18 — **the same failure modes already in her file, not a different class.** So her extract is a consistent ~94% sample rather than a biased one 🟡, most plausibly because dedup collapses several records onto one entity and her row keeps a single refid. Her totals are sound for prioritisation; they undercount the records needing repair by about 6%.

---

## Which files to open on GitHub

Every claim about file contents is 🔴 until someone opens it.

### 1. The state matcher's candidate selection · **fixes ~5,000+ records**

**Question: does candidate ranking filter on the already-normalized country before scoring, or after?**

This is the single change. It resolves **2,279 of 2,282 Other rows (99.87%)**, all 2,210 Homonym rows, and the 558 Accent rows once folding is added — by construction, since §5 confirms the correct target already exists under the record's own country in each case. Look for where state candidates are scored and the top one chosen; the fix is to constrain the candidate set by country first. Start with `UMN Matching System-ProcMinev2` (5,668 records).

### 2. `Inferlink Extraction v3` · **highest failure rate at scale-relevant volume**

**Question: why does it fail at 8.51% when `UMN Matching System v1` fails at 0.28% — 30× better?**

97 conflicts in 1,140 candidates. Low volume today, but it is an active extractor and the rate is the forward risk. Compare its matching path against `UMN Matching System v1`'s.

### 3. `SAND` · **11.56%, and it owns four of the five worst feeds by rate**

**Question: is SAND doing name matching at all, or string-similarity without a vocabulary lookup?**

43 conflicts in 372 candidates, on the `usc`/`usc-stu` DOI feeds — `P99RK9SU` (20.55%), `pp1802J` (9.26%), `econgeo.110.8.1925` (6.37%), `cg2020009` (5.00%).

### 4. The dedup/merge step · **the six records in §7**

**Question: when constituent records disagree on country, which one wins, and is the winning country checked against the winning state?**

This is the merge-induced defect the matcher fix will not touch. The six records in §7 are the test cases — each is internally consistent but merges to a contradiction. A post-merge assertion that state's country equals entity country would catch the whole class.

### 5. The vocabulary · **784 records, lowest priority**

**Question: add `Para` (Suriname), `Northwest Region` (Yemen), and the 781 "Not in the list" names as entries or aliases?**

Separate PR, no code change. `Muhanga` (Rwanda), `Karibib District` (Namibia), `Setúbal District` (Portugal) are representative — real subdivisions absent from a 5,084-entry list.

### 6. The extractor writing two-letter state codes · **184 records**

**Question: where does a US state abbreviation (`CA`, `CO`, `MO`, `SD`) reach the matcher as a state name?**

These never had a chance — `CA` matched `Canelones`, Uruguay. Either expand abbreviations before matching or refuse to match 2-character strings. The 25 "No observed name" rows belong to the same conversation: a matcher returned a confident `Florida` from an empty string.

---

## Run record — `probe-runs/2026-09-14/`

| File | Section |
|---|---|
| `p2.0-gate` | endpoint gate, `ASK` → `true` |
| `p2.1a` / `p2.1b` | 1 — affected by source / source totals |
| `p2.2a` / `p2.2b` | 2 — source × matcher / matcher denominators |
| `p2.3` | 3 — full population, 6,159 rows, unpaginated |
| `p2.4` / `p2.4b` | 4 — state vocabulary / country Q-id labels |
| `p2.5-classified.csv` | 5 — every row with its class |
| `p2.6` | 6 — country totals |
| `p2.7-missed-six` | 7 — direct query of the six she flags |
| `p2_reconcile.py` `p2_classify2.py` `p2_rates_xcheck.py` `p2_xcheck.py` | offline analysis |

All queries HTTP 200, `truncated_by_limit: false`. Nothing written to the graph; no `ta2-minmod-*` checkout touched.
