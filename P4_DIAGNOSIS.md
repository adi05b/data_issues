# P4_DIAGNOSIS.md — NAD27 stored as WGS84: the graph-only sections

*Aditi Bombe · USC ISI · run 2026-09-21 (third pass — endpoint reachable) · **read-only**. Nothing written to the graph, no repository modified.*
*Run record in `probe-runs/2026-09-21/`. Confidence: 🟢 verified (I ran it) · 🟡 likely · 🔴 assumed.*

**Endpoint reachable.** `ASK { ?s ?p ?o }` → HTTP 200, `true`, `curl` exit 0. The host was dead for the two earlier passes (exit 28 — timeout, not certificate). It held for this entire run; every query returned 200 and every raw JSON was written before analysis. 🟢

---

## Lead — what the graph changed

### 1. The convergence question is **closed**. Both figures reproduce exactly. 🟢

| Population | Adriana | Rebuilt from the graph | |
|---|---|---|---|
| **All pairs** — every NAD27 × non-NAD27 pairing within 5 km | **2,279** pairs / 1,470 entities · 174.2 → 101.1 m · 5.3 % → 47.6 % | **2,279** pairs / **1,470** entities · **174.8 → 101.4 m** · **5.3 % → 47.6 %** | ✅ |
| **Nearest sibling only** | 1,602 rows / 1,470 entities · 159.1 → 32.2 m · 6.6 % → 64.7 % · 1,239 improve | **1,609** rows / **1,470** entities · **159.2 → 26.4 m** · **6.5 % → 64.3 %** · **1,234** improve | ✅ |

Both are correct over different populations, exactly as the PDF's *"Counting these in the CSV"* box says. **Question closed.** 🟢 `q3-convergence-clean.json`

The all-pairs acceptance test lands on **n = 2,279 to the record**, with the before/after medians inside 0.6 m and the within-50 m percentages identical to one decimal. Nearest-only is within 7 rows and 5 improving pairs; the residual `after` gap (26.4 vs 32.2 m) is a tie-breaking difference in which sibling is "nearest" when two are near-equidistant, not a disagreement about the transform.

### 2. Reproducing it required excluding one broken entity — and that exclusion is itself a finding 🟢

My first all-pairs enumeration returned **13,111** pairs and a `nan` median. Both were real, and the cause is not in my code:

- **10,850 of the 13,111 pairs came from a single dedup entity**, `dedup_site__doi-org-10-4095-295581__955__usc`, which holds **1,329 member records** spanning Oregon, Virginia and Alaska. It is a bad merge, not a mine.
- **10,832 pairs had a sibling coordinate with |lat| > 90** — an impossible latitude, which is why `Geod.inv` returned `nan`.

**677 of that entity's members are `oregongeology.org` records whose merged coordinate has |lat| > 90.** That is **Problem 1's latitude/longitude transposition, live in the dedup layer today**, arriving here as corrupted input to a Problem 4 measurement. 🟢 Excluding those two things — and nothing else — gives exactly 2,279.

### 3. Four CRSs are in use; the vocabulary admits a fifth 🟢

The previous pass concluded four CRSs from a 2026-09-03 archive. **Confirmed live at raw-record grain**, with the `:observed_name`-OPTIONAL fix applied. But `:CoordinateReferenceSystem` has **five** entities: `Q703` = **EPSG:3857** (Web Mercator) exists in the vocabulary with **zero records**. It is *projected*, so if data ever arrives in it the failure would be Problem 1's axis swap, not Problem 4's silent no-op — verified: the current code returns `(39.738, −104.977)` for a Denver Web Mercator point, latitude first. 🟢

---

## Grain

`:MineralSite` = **raw record**. `dedup_mineral_site` = **merged entity**. Labelled on every number below.

---

## Query bug — confirmed and quantified 🟢

Making `:observed_name` non-OPTIONAL drops records and invents a CRS. With it OPTIONAL, at **raw-record grain**:

| `observed_name` | `normalized_uri` | Records | Sources |
|---|---|---|---|
| `EPSG:4326` | Q701 | **403,549** | 24 |
| `EPSG:2994` | Q705 | 23,316 | 1 (oregongeology) |
| **(absent)** | **Q701** | **7,869** | **20** |
| `EPSG:26912` | Q704 | 7,792 | 1 (OFR-757) |
| `EPSG:4267` | Q702 | **7,720** | 1 (ardf) |
| `WGS84` | Q701 | **1** | 1 (api.cdr.land) |
| | | **450,247** | |

Plus **1,280 records with no `:crs` node at all** → 451,527, which reconciles against the LocationInfo total. 🟢 `q1a-crs-census`, `q1b-no-crs-node`

**The required-`observed_name` form would have dropped 7,869 records and reported `WGS84` as a phantom non-4326 CRS.** Both confirmed.

### The 7,869 with no `:observed_name` — never looked at before 🟢

**All 7,869 normalize to Q701 (EPSG:4326), across 20 sources.** The largest are `econgeo.2018.4590` (2,301), `sir20105090z` (1,200), `oregeorev.2016.08.010` (851), `sedcu` (708), `porcu` (690), `econgeo.4950` (627).

**These records have EPSG:4326 *assumed*, not declared.** The profile is overwhelmingly DOI/paper sources — the same signature found in Problem 1 for the Tagaung Taung record (`econgeo.4950`, no `observed_name`, EPSG:4326 defaulted in, coordinates transposed at source). If any of these 7,869 are actually on a different datum, the error is present and **invisible**, because nothing records that the CRS was a default rather than a reading. That is a standing risk, not a current defect. 🟡

### The 1,280 with no `:crs` node 🟢

15 sources; `api.cdr.land` 490, `phosphate` 447, `ree` 221, `podchrome` 79, `mrds` 20, the rest single digits. These never reach the transformer at all.

---

## Section 1 — the population, at today's grain 🟢

For the 4267 set, live: **7,720 records, 1 source, 1 creator, 1 distinct confidence value.**

| Field | Value |
|---|---|
| `:source_id` | `https://doi.org/10.5066/P96MMRFD` (ardf) — **1** distinct |
| `:created_by` | `https://minmod.isi.edu/users/s/umn` — **1** distinct (the previous pass could not verify this) |
| `:confidence` on the CRS node | **1.0** — 1 distinct value |
| normalized state | Alaska |
| `crs_qid` | Q702 |

🟢 `q1d-4267-detail`. The CRS is asserted at full confidence by a single system matcher. **The source said NAD27 and MinMod recorded it correctly** — the defect is entirely downstream in `geo.py`.

---

## Section 2 — does the CRS survive the merge? **No.** 🟢

Confirmed from the dedup REST API, not the CSV. All 7,720 site ids resolved via `POST /api/v1/mineral-sites/find_by_ids`:

| | Count | Grain |
|---|---|---|
| NAD27 raw records | 7,720 | raw record 🟢 |
| **distinct dedup entities** | **7,218** | merged entity 🟢 — matches the CSV exactly |
| entities holding >1 NAD27 record | 353 | merged entity 🟢 |
| largest entity | 16 NAD27 records | 🟢 |

**Does the merged record expose a CRS in any form? No — plainly, 0 of 10.** 🟢 `q2-dedup-crs-check.json`

The dedup entity's full key list is `['deposit_types','discovered_year','grade_tonnage','id','location','mineral_form','modified_at','name','rank','sites','trace','type']`, and `location` is:

```json
{"lat": 61.4187, "lon": -149.3953, "country": ["Q1235"], "state_or_province": ["Q6840"]}
```

No CRS, no datum, no EPSG, no such substring anywhere in the JSON on any of the 10. **A downstream consumer cannot tell a NAD27-derived coordinate from a WGS84 one.** That is why this went unnoticed and it belongs in the write-up.

### Which entities did *not* take a NAD27 coordinate?

Measured on a random sample of 250 entities against the live API: **236 of 243 (97.1 %) publish a coordinate matching one of their NAD27 members; 7 (2.9 %) do not.** Extrapolated: ≈7,010 take NAD27, ≈208 do not. 🟢 `q2-coord-election-sample.json`

**This sits slightly outside the CSV's 7,140 / 78** (1.08 % non-NAD27); the sample's 95 % interval is roughly 1.2–5.9 %, so the CSV figure falls just below it. I am not calling either wrong — the sample is 250 of 7,218 and a full census would settle it. 🟡 The direction of the disagreement matters though: **more** entities may be escaping the NAD27 coordinate than the CSV suggests, which would make the merged-entity damage slightly smaller, not larger.

A separate heuristic — reading the representative record out of the dedup id — gives only **7** non-ARDF representatives. That tells us the dedup id names the representative record but **not** necessarily the record whose coordinate was elected; the two differ. Worth knowing before anyone uses the id as a proxy. 🟢

---

## Section 3 — the convergence question, closed 🟢

Rebuilt from the dedup grouping via the REST API. **Note `owl:sameAs` is not the right grouping**: it yields only **373 sibling pairs across 297 NAD27 records** 🟢 (`q3-nad27-siblings`), an order of magnitude short. The dedup entity is much broader, and anyone rebuilding this from SPARQL alone will get the wrong answer.

Method: all 7,218 entities fetched; 11,456 non-NAD27 member sites resolved; NAD27 records transformed with `always_xy=True` and the NADCON Alaska grid present; distances geodesic on WGS84; pairs capped at 5 km.

| | All pairs | Nearest sibling only |
|---|---|---|
| rows | **2,279** (hers 2,279) | **1,609** (hers 1,602) |
| entities | **1,470** (hers 1,470) | **1,470** (hers 1,470) |
| median before | **174.8 m** (hers 174.2) | **159.2 m** (hers 159.1) |
| median after | **101.4 m** (hers 101.1) | **26.4 m** (hers 32.2) |
| within 50 m before | **5.3 %** (hers 5.3) | **6.5 %** (hers 6.6) |
| within 50 m after | **47.6 %** (hers 47.6) | **64.3 %** (hers 64.7) |
| improving | 1,608 (70.6 %) | **1,234** (hers 1,239) |

**The all-pairs acceptance test passes.** Both populations are correct; they measure different things, and nearest-sibling flatters the result by construction because it selects the closest match. **Quote all-pairs — 174 → 101 m — when the claim needs to survive scrutiny.**

**Pairs that get worse (nearest-only): 360 of 1,609 (22.4 %)**, and **327 of them have an MRDS sibling.** 🟢 MRDS holds the lowest source score in the graph (0.1) and was shown in `P3_VERIFIED.md` to be the largest holder of coarse coordinates. So "worse against MRDS" most likely means the *sibling* is wrong, not the datum fix — 🟡, a hypothesis, not a finding.

---

## Section 4 — the 24, confirmed both ways 🟢

Over the 40 far-west ARDF records (longitude ≤ −168.91° or positive):

| | grids absent | grids present |
|---|---|---|
| PROJ operations available / unavailable | 31 / **48** | **79 / 0** |
| named missing grid | **`us_noaa_alaska.tif`** (also `us_noaa_conus.tif`, `ca_nrc_ntv2_0.tif`) | — |
| returned the identity | **24 / 40** | **0 / 40** |
| operation used for those 24 | `Ballpark geographic offset`, accuracy **−1.0** | **`NAD27 to WGS 84 (85)`, accuracy 5.0 m** |
| shift min / median / max | 199.4 / 202.4 / 274.1 m *(the 16 that did move)* | **161.5 / 173.5 / 274.8 m** *(all 40)* |

🟢 `q4-the24-grid.json`

> **Without the grid, the fix silently skips exactly the 24 worst-displaced records in the corpus.** They shift 161.5–244.2 m once corrected, against a corpus median of 126.5 m. PROJ reports no error — it substitutes a ballpark operation, declares accuracy −1.0, and returns the input unchanged.

That is the argument for provisioning the grids, and it is more persuasive than any median.

---

## What I verified, what I could not, and what is wrong

**Verified 🟢** — endpoint live, all queries HTTP 200, raw JSON saved before analysis:
- Full CRS census at raw grain with the OPTIONAL fix: four CRSs in use, 450,247 records with a `:crs` node + 1,280 without = 451,527.
- The 7,869 no-`observed_name` population: 20 sources, all normalizing to Q701.
- The vocabulary holds five CRS entities; Q703 (EPSG:3857) is unused and would be a Problem 1 risk, not a Problem 4 one.
- 4267 set: 7,720 records, one source, one creator (`users/s/umn`), confidence 1.0.
- 7,720 raw records → **7,218** merged entities, via the dedup API.
- **0 of 10** merged entities expose a CRS in any form.
- Both convergence populations reproduce; all-pairs lands on 2,279 exactly.
- `owl:sameAs` is not the dedup grouping (373 pairs vs 2,279).
- Grid absent → 24 identities via Ballpark; grid present → 0, all via `(85)` at 5 m.
- One dedup entity holds 1,329 members, 677 of which carry Problem 1's swapped coordinates.

**Could not verify 🔴 / 🟡**
- The 7,140 / 78 split: sampled 250 entities (97.1 % / 2.9 %), which sits just outside the CSV figure. A full 7,218-entity census would settle it; I did not run one because it is ~30 minutes of serial API calls. 🟡
- Whether any of the 7,869 assumed-4326 records are actually on another datum. Nothing in the graph records the difference. 🔴
- `04_nad27_datum.md` **still does not exist** on this machine — third pass, same result. I could not reconcile against it as instructed; everything reconciles against `NAD27_IMPACT.md`, the prior `P4_DIAGNOSIS.md` and the brief's own summary. 🟢

**What is wrong, in order of consequence**
1. **`NAD27_IMPACT.md` §2 and §4** — "24 records … will not be corrected by this or any `always_xy` change". Wrong. They are inside coverage and all 24 correct once the grid is present. My own earlier error.
2. **Problem 1 is unfixed and is corrupting the merged layer now** — 677 `oregongeology` records inside one dedup entity carry |lat| > 90. This surfaced as a `nan` in a Problem 4 measurement, which is how little it takes for the swap to contaminate unrelated analysis.
3. **`owl:sameAs` must not be used to rebuild dedup groups** — it finds 16 % of the pairs. The previous pass's Section 3 would have been badly wrong had it run that way.
4. **The dedup id is not a reliable proxy for the elected coordinate** — 7 non-ARDF representatives versus ~78–208 entities not publishing a NAD27 coordinate.
5. **The brief's original Section 1/3 queries** — `:observed_name` must be OPTIONAL. Confirmed: 7,869 dropped, one phantom CRS.

---

## Run record — `probe-runs/2026-09-21/`

| File | What |
|---|---|
| `q1a-crs-census.*` | full CRS census, OPTIONAL form, raw grain |
| `q1b-no-crs-node.*` | the 1,280 with no `:crs` |
| `q1c-crs-entities.*` | the five vocabulary CRS entities |
| `q1d-4267-detail.*` | source / creator / confidence for the 4267 set |
| `q2-site-to-dedup.json` | all 7,720 site → dedup mappings |
| `q2-dedup-crs-check.json`, `q2-coord-election-sample.json` | CRS exposure, election sample |
| `q3-nad27-siblings.*` | the `owl:sameAs` attempt (373 pairs) |
| `q3-dedup-members.json`, `q3-sibling-coords.json`, `q3-pairs.csv` | dedup membership and every pair |
| `q3-convergence.json`, `q3-convergence-clean.json` | both populations, raw and cleaned |
| `q4-the24-grid.json` | grid present/absent comparison |
| `s2_dedup.py`, `s2_taken.py`, `s3_fetch.py`, `s3_pairs.py`, `p4_*.py` | analysis |

Read-only throughout: SELECT and GET only, no write verb issued, no repository modified, TLS verification never disabled.
