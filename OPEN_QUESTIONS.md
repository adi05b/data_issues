# OPEN_QUESTIONS.md

*After the probe run of 2026-09-02. Every question from the master plan's step-2 table, plus the ones the probe opened, with what the probe settled and what would settle the rest.*

Confidence: 🟢 verified · 🟡 likely · 🔴 assumed.

---

## Settled by the probe — no longer open

| Q | Answer | Evidence |
|---|---|---|
| **Is `:country` on `mr:Q<state>` a literal `"Q1233"` or an IRI `mr:Q1233`?** | **A plain literal holding a bare Q-id** (`"Q1177"`, no datatype key, no namespace). `:normalized_uri` is an IRI. Probe 2b's join is correct as written. *(Also: the US is `Q1235`, not `Q1233`.)* 🟢 | `2a`, `2e-florida-entities` |
| **Which country/state candidate does dedup elect when a site carries several?** | **Moot for 99.99% of sites — there is only one candidate to elect.** 450,570 of 451,527 sites carry exactly one country candidate (2 carry two); 421,524 carry exactly one state candidate (31 carry more). 🟢 | `P0.7`, `P0.7b` |
| **Does a naive join multiply rows?** | **No, in practice.** 33 sites of 451,527. Rows-per-site = 1.00 on every `1a-alt` and on `2a`. `COUNT(DISTINCT ?site)` remains correct practice but changes no count materially. 🟢 | `P0.7`, `P0.7b`, `2b-total` |
| **Is `:crs` populated?** | **Yes — 450,247 of 451,527 LocationInfo nodes (99.72%).** Not optional. It is the decisive field in Problem 1. 🟢 | `P0.1-locationinfo` |
| **Did the matcher report low confidence on the wrong picks?** | **Partly — and usefully.** 58.7% of conflicts sit below 0.9 confidence vs 2.5% of all candidates (~23× enrichment). But the largest wrong bucket (2,058 Florida rows) sits at 0.9999. A threshold is a good triage gate, not a fix. 🟢 | `2d`, `2d-baseline` |
| **Do the correct match targets exist in the vocabulary?** | **Yes for every suffix and tie case; no for both gap cases.** Q2453/Q2456/Q2454/Q2457/Q2887/Q6958/Q3902/Q6850 all exist. No `Orissa`, no `Katanga`. 🟢 | `2f-target-existence` |

---

## Still open — and what would settle each

### 1. Fix mechanism: edited JSON in `ta2-minmod-data` + ETL rebuild, or writes through the editor API? 🔴

**Untouched by this probe** — it is a process question, not a graph question, and answering it would have required a write.

**What would settle it:** Craig's decision. Bring him the concrete framing the probe produced: Problem 1's real fix is *not* 31,108 row edits but a CRS-aware validation rule plus possibly an ETL reprojection — which lands squarely in the data-repo/ETL path, not the editor path. Problem 2's suffix class is a matcher change (ETL path); only its tie class is row-level. That shifts the balance toward the repo path for most of the work. **This is the blocking decision for step 3.**

### 2. Why did SHACL validation not bound latitude? 🔴

**Could not be checked** — no `ta2-minmod-kg` checkout on this machine; nothing was cloned.

**What would settle it:** `grep -r` over `ta2-minmod-kg/schema/` for `sh:NodeShape` / `sh:minInclusive` on the location path. **Note the probe changes the recommendation:** an unconditional latitude bound would reject 31,108 *valid* projected-CRS records. Any shape must bound latitude **only when `:crs` resolves to a geographic CRS**. 🟢

### 3. Does the matcher get fixed, or only the rows? 🟡

**The probe strengthens the case for fixing the matcher**, and adds a constraint the plan did not have: suffix-stripping alone is insufficient, because `La Paz Department` exists in **three** countries. Candidates must also be constrained to the already-normalized country. 🟢 Four matchers are in play, so a fix targeting one leaves the others' rows.

**What would settle it:** a decision from Craig/Amandeep on whether the matching pipeline is in scope. If not, row repoints are explicitly a stopgap that the next ETL run regenerates.

### 4. **What exactly did Adriana count for Problem 3?** 🟡 — *new, and blocking*

Latitude-only gives **2,853 raw** against her **3,633 dedup**. Raw < dedup is impossible at the same grain, so Probe 3a does not measure her figure. "Either axis at exactly 1 dp" (5,409 raw, ratio 1.49) is the only tested rule that is arithmetically possible.

**What would settle it:** one email. Ask which axis (or both), whether "≤1 dp" or "exactly 1 dp", and whether her query filtered on CRS. **Do not publish a source table before this is answered.**

### 5. Why is raw uneven-precision (33,950) only 0.36× dedup (93,673)? 🟡 — *new*

Dedup has **fewer** entities but **more** uneven rows. The leading hypothesis is that dedup coordinates are **recomputed** — a mean over merged raw records — producing decimal lengths that exist in no raw record.

**What would settle it:** read the `dedup_mineral_site` build logic (Postgres/`minmodkg`), specifically whether the merged coordinate is copied from an elected record or computed. If computed, **every precision figure at dedup grain is a property of the merge, not of any source** — which would reframe Problem 3 entirely.

### 6. Does the source file already carry 1 dp, or did the ETL round it? 🟡 — *§9, could not run*

No `ta2-minmod-data` checkout; nothing cloned. **This is the single question that decides between "record a precision field" and "fix the extractor".**

The probe supplies a strong prior: MRDS stores `-109.4878899999999931` — 16 dp for a value published at 5 — so coordinates demonstrably round-trip through float64 and are re-serialised at shortest-round-trip length. **Trailing-zero loss is a serialisation artifact, near-certainly not an extractor bug.** 🟡 But whether the *≤1 dp* rows are coarse at source is a different question and genuinely unknown.

**What would settle it:** open 2–3 `nicrpge` records under `ta2-minmod-data/data/mineral-sites/` (the top coarse source, 1,843 rows) and compare the raw coordinate to the graph value.

### 7. How large is Problem 1's undercount? 🔴 — *now the main flip risk*

With H1's visible population known to be **exactly 1**, transpositions where both magnitudes are under 90 stay in range and are the **only remaining flip exposure**. This is no longer a footnote — it is the whole of Problem 1's genuine-error surface.

**What would settle it:** the containment test the plan parks as Probe 1d — reverse-geocode the stored point, compare to `?country_obs`, then test whether the *swapped* point lands in the observed country instead. Not expressible in SPARQL; needs a script with country polygons. **Recommend promoting this to a first-class task**, since it is where Problem 1's real errors now live.

### 8. Should the graph normalise all coordinates to EPSG:4326 on ingest? 🔴 — *new, for Craig*

31,108 records are correctly stored in EPSG:2994 and EPSG:26912. They are not wrong. But every downstream consumer that reads `:location` without reading `:crs` — the map view, FuseMine's 10 km blocking, Adriana's range check — treats them as degrees and gets nonsense.

**What would settle it:** a product decision. Either normalise on ingest (and keep the native value + CRS for provenance), or mandate that consumers read `:crs`. The probe shows the second is not currently happening.

### 9. What are the 217 unparseable geometries? 🟡 — *new, small but real*

215 `MULTIPOINT`, 1 misspelled **`MULIPOINT`**, 1 literal **`NaN`** latitude. Invisible to every probe query and to any regex anchored on `POINT`.

**What would settle it:** a targeted query listing all 217 with source and site id. Cheap. The `MULIPOINT` typo and the `NaN` suggest at least one extractor emits unvalidated geometry strings, which is worth knowing independently of the count.

### 10. Is `Zagreb` a duplicate vocabulary entity? 🟡 — *new*

`2c` shows 2 entities under a single country (Q1053) — not a tie, not a matcher error, a probable duplicate in `state_or_province.csv`.

**What would settle it:** a query for all same-label-same-country entity pairs. One query, and it may reveal a class rather than a one-off.

---

## Not open, but worth stating

**Adriana's brief for Problem 1 — "most look like lat/lon flips" — is not supported by the raw graph.** 🟢 One record of 31,109 is a flip. This should be raised with her directly and early, before any correction work is scoped, because the entire framing of Problem 1 follows from it.

---
---

# ADDENDUM — 2026-09-02 (later same day)

*Status of the ten questions above after the addendum run, plus what it opened.*

## Closed by the addendum

| # | Question | Resolution |
|---|---|---|
| **9** | What are the 217 unparseable geometries? | **Partially closed.** Not enumerated individually, but the CRS census confirms none of them is a CRS problem: every CRS candidate in the graph normalizes, and the 1,280 nodes without a CRS have no candidate at all. Still worth the one cheap listing query. 🟡 |
| — | *(new, from Part 1)* Does reprojection actually reproduce the correct coordinate? | **Closed 🟢.** Harts Draw reprojects to within **6.4 m / 7.3 m** of its MRDS siblings. 89 of 90 tested records land in the observed state under their declared CRS; the exception is 123 m outside a bounding box whose edge is the state line. |
| — | *(new, from Part 4)* Is EPSG:2994 the foot or the metre variant, and is the declared CRS trustworthy? | **Closed 🟢.** EPSG:2994 is `NAD83(HARN) / Oregon GIC Lambert (**ft**)`; OFR-757's EPSG:26912 is metres. Under the declared CRS 50/50 Oregon records land in Oregon; under the metre sibling EPSG:2993 only 10/50. **The CRS field can be trusted, so a CRS-aware validation rule would work.** |
| — | *(new, from 2.2)* Which OFR-757 record isn't out of range? | **Closed 🟢.** `site__doi-org-10-34191-ofr-757__4563__umn` ("A&G") has `:location_info` but **no `:location`**. Benign — not a mislabeled CRS. |

## Changed by the addendum

| # | Question | Change |
|---|---|---|
| **8** | Should the graph normalise all coordinates to EPSG:4326 on ingest? | **Still open and still Craig's, but the supporting argument is weaker than the first run implied.** The linkage test (`A2.1`) found **no evidence** that projected coordinates suppress clustering — Oregon links at 5.93% cross-source against a 3.50% baseline. The case for normalising now rests on the mechanism (any consumer reading `:location` without `:crs` gets nonsense) rather than on measured harm. 🟡 |
| **3** | Does the matcher get fixed, or only the rows? | **The ROI is now quantified, and it is large.** Suffix-stripping + diacritic-folding + country-constraining resolves **83.9% of conflicts (5,145 of 6,134)** and **33.6% of never-matched state names (1,090 of 3,248)** — **6,235 sites from one change**, with only 15 sites hitting an ambiguous key. Row repoints fix at most the 6,156 conflicts and regenerate on the next ETL. Still a decision, but the numbers now favour the matcher decisively. 🟢 |
| **2** | Why did SHACL not bound latitude? | **Unchanged and still blocked on the repo** — but the recommendation is now firmer: the conditional bound *would* work, because A1 proves the CRS field is reliable enough to condition on. 🟢 |

## Still open, unchanged

- **#1 Fix mechanism (repo + ETL vs editor API).** Craig's decision. The addendum pushes further toward the ETL path: Problem 1's fix is a validation rule or an ingest reprojection, and Problem 2's best fix is now clearly a matcher change — both ETL-side.
- **#4 What exactly did Adriana count for Problem 3?** Blocked, and **still should not be asked until #5 is checked** — see below.
- **#5 Why is raw uneven-precision only 0.36× dedup?** Blocked on the `dedup_mineral_site` build logic. Unchanged and still the most leveraged of the Problem 3 questions.
- **#6 Does the source file carry 1 dp, or did the ETL round it?** Blocked on the repo.
- **#7 How large is Problem 1's undercount?** Unchanged, and now with a second reason to run it: the bounding-box test cannot classify a site on a state line (`School Sec. 36` sits 123 m outside a rectangle whose edge is the border). Probe 1d's polygon containment is needed both to size H1's invisible population **and** to adjudicate border cases.
- **#10 Is `Zagreb` a duplicate vocabulary entity?** Unchanged, one query.

## Opened by the addendum

### 11. The vocabulary CSVs are not a mirror of the deployed graph 🟢 — *new, and it undercuts a method*

`crs.csv` as read lists **EPSG:3857**, which appears **zero** times in the graph, and omits **EPSG:2994**, which carries the largest block of out-of-range records (23,316). The master plan's "root causes already visible from the vocabulary before any query" section reasons from these CSVs. Its Problem 2 conclusions happened to survive checking; its CRS conclusions did not.

**What would settle it:** diff `ta2-minmod-data/data/entities/*.csv` against the live graph for every entity type. Until then, **treat any CSV-derived claim as unverified until queried.** The state vocabulary count is also off by one (5,084 live vs 5,083 in the plan) — trivial, but the same symptom.

### 12. What actually produces `owl:sameAs`? 🔴 — *new, and it blocks a whole line of reasoning*

72.2% of pairs are the **same source record processed by two teams** (`__umn` ↔ `__sri`), 19.9% intra-source, only 7.8% cross-source. Two MRDS records ~20 m apart, plainly the same place, are **not** linked to each other. So `owl:sameAs` is not obviously FuseMine output, and it may not be entity resolution at all.

**Why it matters:** any argument about clustering, deduplication quality, or the downstream cost of projected coordinates runs through this predicate. Right now nobody has verified what writes it.

**What would settle it:** find the writer in `minmodkg`, and confirm whether FuseMine's spatial blocking output reaches the KG under a different predicate or only lives in Postgres.

### 13. Roughly 3,100 sites need vocabulary aliases, not repoints 🟢 — *new, sized*

After the best mechanical matcher, the residue is **974 sites in the conflict set + 2,153 in the unmatched set**. Largest: `Orissa` (278 across both), `Katanga` (241), `Newfoundland` (101), `Chitinskaya oblast` (83), `Aqmola` (78), `Greenland` (67), `Qaraghandy` (51), `Territory Of New Caledonia And Dependencies` (49), and **`CO` (51) — a bare two-letter abbreviation** that no name matcher should be expected to resolve.

**What would settle it:** a decision on whether an alias/renamed-entity table is in scope, and who owns it. The `CO` case additionally suggests an extractor is emitting state *codes* into an `:observed_name` field expected to hold names — worth checking separately.
