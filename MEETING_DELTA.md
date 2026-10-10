# MEETING_DELTA — numbers this run changed

*7 September 2026. Check against the deck in five minutes. Old value → new value, with where the new one comes from.*
*Part 1 of the brief ran in full. Part 2 did not — nothing below depends on it.*

---

## Changed — update the slide

| # | Claim | Old | **New** | Why it changed |
|---|---|---|---|---|
| 1 | Matcher fix resolves this share of conflicts | **83.9%** | **83.6% resolved; 74.1%–83.6% correctly fixed (95% CI)** | The old figure was the *resolution* rate presented as an *accuracy* rate. Re-derived per record (5,144 of 6,156) and hand-audited: 30/30 correct, Wilson interval 88.6%–100%. **Quote the interval, not a point number.** |
| 2 | Hand-verified accuracy of the fix | *10 examples, informally* | **30 of 30, random, seed 20260907, [88.6%, 100%]** | A real reproducible sample replaces the rule grading itself. |
| 3 | Number of matchers involved | **4** | **10** (6 automated + 4 human users) | Full census over all state candidates, not just those in conflict. |
| 4 | Conflicts attributable to one component | *not stated* | **ProcMinev2 = 5,668 of 6,156 = 92.1%** | Answers "change what, exactly?" — it is one component. |
| 5 | Conflicts and never-matched share a root cause | *"one root cause, two symptoms"* | **Different components.** Conflicts: ProcMinev2 (92.1%), which never abstains. Never-matched: UMN v1 + Exact Match v1 (97.4%), and ProcMinev2 contributes **zero**. | Two tickets, not one. |
| 6 | Conflicts the rule cannot resolve | **989** | **1,012** | Recomputed per record rather than per name-group. |
| 7 | Uneven-precision set | *"artefact"* | **83.2% artefact (gap 1–2), 16.8% real (gap ≥3)** | Gap histogram. The blanket dismissal was too strong. |
| 8 | Decimal counts are meaningless | *"a floating-point artefact"* | **Asymmetric: a LOW count is real evidence; a HIGH count is meaningless.** | Verified: 400,000 round-trips, zero values with 3–6 real decimals ever render at ≤1. **The source table is publishable after all.** |
| 9 | Coarse-source ranking | *CRS-blind; OFR-757 ranked first on 7,792 "0 dp"* | **`ree` 22.7%, `phosphate` 20.7%, `api.cdr.land` 20.2% by rate; `nicrpge` 2,381 by volume** | Restricted to EPSG:4326 and ranked by rate against each source's own total. OFR-757's records were UTM metres and are correctly excluded. |
| 10 | Uneven precision means two axes from different sources | *hypothesis* | **Not supported. It is degrees-minutes conversion** — 12/12 of the largest-gap long values land exactly on a whole arcminute; 47% across gap 3–11. | `POINT (7.41666666666667 45)` is 7°25′ / 45°00′ — same precision, wildly different rendering. |

---

## New — no slide yet, add if there is room

| # | Finding | Number |
|---|---|---|
| 11 | **Country side of a conflict is sound** — the load-bearing assumption behind the whole fix | **99.38% state-wrong, 0.06% country-wrong**, 0 both-wrong, 25 undecidable |
| 12 | **Nearly half the problem needs no text matching at all** — the country constraint alone fixes the homonym class | **2,793 of 6,121 = 45.6%** |
| 13 | **Two-letter state CODES in a name field** — an extractor defect, not a matching one | **184 records**: `CO` 51, `CA` 46, `MN` 16, `ME` 15, `SD` 12 → matched to Colonia, Canelones, Matabeleland North, Saada |
| 14 | **Highest conflict *rates* are not the highest volumes** — a forward risk | SAND 11.56%, Inferlink v3 8.51% vs ProcMinev2 1.89% |
| 15 | **A second coordinate defect** surfaced during adjudication | 2 of 30 sampled records have coordinates disagreeing with their own state (one ~900 km off) |
| 16 | **Longitude is coarser than latitude** graph-wide | lat ≤1 dp: 3,137 (0.77%) · lon ≤1 dp: 3,644 (0.90%) |
| 17 | **MRDS has zero coarse coordinates**, and P9HTERGK ships 42,744 records at a 0.03% coarse rate | It is possible to ship at scale without this problem |
| 18 | The four bad country normalizations share the state side's flaw | `Slovak Republic`→Central African **Republic**; `Korea, Republic of`→Democratic **Republic** of the Congo |

---

## Unchanged — safe to leave as-is

- 6,156 raw conflicting sites (5,858 deduplicated).
- 31,109 out-of-range latitude records; 31,108 projected, **1** genuine transposition. Problem 1 is settled and out of scope for this run.
- Harts Draw reprojects to within 6.4 m / 7.3 m of its siblings.
- EPSG:2994 is the **foot** variant; the declared CRS is trustworthy.
- The ~3,100-record vocabulary residue (`Orissa`, `Katanga`, `Newfoundland`, …). *A proper classification of it was Part 2.2 and did not run — it is still one bucket that ought to be at least four.*
- 34 records at (0,0), all from one extraction pipeline, 29 carrying a real country.

---

## Two things to say out loud

**1. The headline number is an interval, not a point.** "The matcher fix correctly resolves an estimated 74–84% of the 6,156 conflicts, hand-verified at 30 of 30 on a random sample." If someone asks why not 83.9%, the answer is that the old figure measured whether the rule *produced an answer*, not whether the answer was *right* — those are different quantities and only the first had been measured.

**2. Problem 3 is more publishable than the last write-up implied.** The source table exists and is defensible. What is still impossible is the per-record precision figure Adriana wants for error propagation — that needs a schema field that does not exist, and the degrees-minutes finding means even a careful decimal count understates precision for a large share of records.

---

## Still blocked, and by whom

- **Craig / Amandeep:** is the matching pipeline in scope to change? Everything in Problem 2 turns on it.
- **Adriana:** what exactly did she count for the 3,633? *(Reverse-engineering the candidate rules was Part 2.1 and did not run.)*
- **A repository checkout, not on this machine — I have not cloned.** Four reads outstanding, the most leveraged being whether the deduplicated coordinate is **elected or recomputed**. If merging averages coordinates, every precision figure at deduplicated grain describes the merge rather than any source. **Worth reading before anything goes to Adriana.**
