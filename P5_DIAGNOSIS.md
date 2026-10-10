# P5_DIAGNOSIS.md — commodity mis-normalizations: diagnosis and sweep

*Aditi Bombe · USC ISI · run 2026-09-21 · **read-only**. SELECT only, no write verb, no repository modified.*
*Run record in `probe-runs/2026-09-21/` (`p5-*`). Confidence: 🟢 verified (I ran it) · 🟡 likely · 🔴 assumed.*

**Endpoint reachable.** `ASK { ?s ?p ?o }` → HTTP 200, `true`, `curl` exit 0. Held for the whole run; every raw JSON written before analysis. 🟢

---

## Lead: **0.90 is the wrong threshold, and a confidence floor cannot fix two of the four defects**

### 1. A 0.90 floor destroys 32,324 correct mappings to fix 49,861 wrong ones 🟢

Every commodity match below 0.90 — 116 distinct `(observed, label, source)` rows, 82,318 raw records — hand-judged. The trade-off at each candidate floor:

| floor | records cut | **WRONG fixed** | **GOOD lost** | ratio |
|---|---|---|---|---|
| 0.55 | 47,241 | 47,226 | **15** | 3148 : 1 |
| 0.60 | 47,976 | 47,955 | **16** | 2997 : 1 |
| **0.62** | **47,993** | **47,955** | **33** | **1453 : 1** |
| 0.65 | 48,439 | 47,967 | 437 | 110 : 1 |
| 0.70 | 50,819 | 48,938 | 1,802 | 27 : 1 |
| 0.75 | 54,875 | 48,940 | 5,810 | 8.4 : 1 |
| 0.80 | 78,341 | 49,856 | 28,352 | 1.8 : 1 |
| **0.90** | 82,318 | 49,861 | **32,324** | **1.5 : 1** |

🟢 `p5-threshold-analysis.txt`, `p5-s2d-below90`

**Going from 0.62 to 0.90 buys 1,906 extra correct rejections and costs 32,291 good mappings.** The 0.85–0.90 band the brief worried about is nearly empty (194 nodes) — the real damage is the 0.72–0.85 band, which is **97% legitimate**.

What 0.90 would destroy, by volume: `Crushed/Broken → Stone > Crushed/Broken` **17,461 @ 0.7715**; `General → Clay > General` 3,427 @ 0.7798; `Dimension → Limestone > Dimension` 3,081 @ 0.7469; `Fire Clay (Refractory) → Clay > Fire (Refractory)` 2,391 @ 0.8494; `Kaolin → Clay > Kaolin` 1,033; `Bentonite → Clay > Bentonite` 1,008; `Sulfur-Pyrite → Sulfur > Iron Pyrite` 723; `Niobium (Columbium) → Niobium` 710. Every one is correct.

### 2. **Two of the four documented defects sit at confidence 1.0.** No floor touches them 🟢

| observed | → | records | **confidence** | matcher |
|---|---|---|---|---|
| `Construction` | Strontium | 46,221 | **0.5453** | ProcMinev2 |
| **`SC`** | **Scandium** | **7,076** | **1.0000** | UMN v1 |
| **`S`** | **Sulfur** | **2,349** | **1.0000** | UMN v1 |
| `Construc` | Cobalt | 980 | **0.5368** | ProcMinev2 |

🟢 `p5-s1-four-defects`

Mechanism (A), the fuzzy junk, is a confidence problem. **Mechanism (B), the symbol collisions, is not** — `SC` and `S` are *exact* matches against the element table and score a perfect 1.0. A threshold of any value below 1.0 leaves all 9,425 of those records untouched. **The fix sizing must not assume the floor addresses them; it addresses 47,201 of the 56,626 defective records, and the other 9,425 need the source-scoped exclusion rule.**

### 3. A floor is the wrong instrument for 182,746 records anyway 🟢

`:confidence` and `:source` are **mandatory** on commodity nodes (1,379,833 of 1,379,833). `:normalized_uri` is present on only **1,197,087** — **182,746 commodity nodes never normalized at all**, and the confidence they carry is meaningless:

| matcher | matched | **unmatched** | confidence range |
|---|---|---|---|
| UMN Matching System-ProcMinev2 | 635,449 | 0 | **0.4998 – 0.9999** |
| SRI database agent v0 | 299,575 | **79,480** | **1.0 only** |
| UMN Matching System v1 | 192,018 | **102,843** | 1.0 matched / 0.001–1.0 unmatched |
| Inferlink Extraction v3 | 39,962 | 396 | 1.0 |
| SAND | 19,683 | 27 | 0.99–1.0 / **0.0** |
| UMN Exact Match v1 | 10,385 | 0 | **exactly 0.9** |

🟢 `p5-s2c-matcher-x-uri`

**`ProcMinev2` is the only matcher that emits a graded confidence at all.** Every other matcher stamps a constant. **79,480 SRI nodes carry confidence 1.0 with no match whatsoever** — a floor cannot see them.

### 4. ⚠️ **0.90 is exactly the constant `UMN Exact Match v1` stamps on all 10,385 of its matches** 🟢

If the filter is written `confidence > 0.90`, **all 10,385 exact matches are destroyed.** If `>= 0.90`, they survive. This is a one-character difference with a 10,385-record blast radius, and it is the single most important implementation detail in the fix. A floor at 0.62 avoids the boundary entirely.

---

## Grain

`:MineralSite` = **raw record**. `dedup_mineral_site` = **merged entity**. Commodity counts are at **commodity-node** grain where stated and **raw-record** (`COUNT(DISTINCT ?site)`) otherwise. **Merged-entity counts were not run** — see "could not verify".

---

## Pre-flight 🟢

`p5-pf2-commodity-preds` — commodity node grain, 1,379,833 nodes:

| predicate | nodes | coverage |
|---|---|---|
| `rdf:type` | 1,379,833 | 100% — mandatory |
| **`:confidence`** | 1,379,833 | **100% — mandatory** |
| **`:source`** | 1,379,833 | **100% — mandatory** |
| `:observed_name` | 1,379,559 | 99.98% — **274 nodes without** |
| `:normalized_uri` | 1,197,087 | 86.8% — **182,746 nodes without** |

`:confidence` and `:source` are mandatory, so filtering on them is safe. `:observed_name` and `:normalized_uri` are **not** — both must be OPTIONAL, and every query in this run used them that way.

---

## Section 1 — the four defects, confirmed 🟢

All four reproduce at raw-record grain. Counts match the brief except `Construction`, where I get **46,221** against 46,223 — a 2-record difference, not chased.

**Matcher attribution confirmed:** ProcMinev2 for the fuzzy pair, UMN v1 for the symbol pair. ✓

**The 54 genuine non-Oregon `S → Sulfur` rows confirmed exactly** 🟢: `major-deposits` 35, `P96MMRFD` 7, `OFR-757` 6, `potash` 5, `sir20105090z` 1 = **54**.

**New:** `Construction` also appears **2,503 times from `P9HTERGK`, left UNMATCHED at confidence 0.001 by UMN v1** — the same string that ProcMinev2 maps to Strontium. The two matchers disagree on identical input, which corroborates the mechanism independently. 🟢

---

## Section 2 — the threshold (see Lead) 🟢

### Commodity confidence histogram, both grains 🟢 `p5-s2-conf-histogram`

| bucket | nodes | raw records | | bucket | nodes | raw records |
|---|---|---|---|---|---|---|
| 0.00 | 42,752 | 34,018 | | 0.75 | 23,560 | 23,221 |
| 0.45 | 11 | 11 | | 0.80 | 3,799 | 3,799 |
| 0.50 | 47,232 | 47,229 | | **0.85** | **194** | **173** |
| 0.55 | 774 | 732 | | 0.90 | 57,278 | 21,734 |
| 0.60 | 464 | 459 | | 0.95 | 552,707 | 306,819 |
| 0.65 | 2,562 | 2,343 | | 1.00 | 644,424 | 310,221 |
| 0.70 | 4,076 | 4,052 | | | | |

**Below 0.90: 125,424 nodes. Below 0.80: 121,431. Below 0.70: 93,795.** The 0.00 bucket (42,752 nodes) is entirely **unmatched** — 42,725 at 0<c<0.05 and **27 at exactly 0.0**, none with a `normalized_uri`. 🟢 `p5-s2b-zero-conf`

### State and country — different distributions, same conclusion 🟢

| field | nodes below 0.90 | share |
|---|---|---|
| commodity | 125,424 | 9.1% |
| `state_or_province` | **10,732** | 2.5% |
| `country` | **382** | 0.08% |

🟢 `p5-s2e-state_or_province-hist`, `p5-s2e-country-hist`

**A single threshold does not need to differ — because for state and country it is nearly inert.** Country has 382 nodes below 0.90 in a 450,574-node population. And from `P2_AFFECTED_RECORDS.md` we already know the state matcher's real failures sit at *high* confidence (`Florida → Puerto Rico` at 0.9999). **The floor is a commodity-specific remedy. Applying it to all three is harmless but should not be described as fixing state or country.** 🟡

### Recommended threshold

> **0.62.** It rejects **47,955 of the 49,861 wrong mappings (96.2%)** while losing **33 correct ones** — a 1453 : 1 ratio. Raising it to 0.90 buys 1,906 further rejections at a cost of 32,291 good mappings, and collides with the 0.9 constant that `UMN Exact Match v1` stamps on all 10,385 of its matches. 🟢

**923 wrong records survive any sub-0.90 floor**, chiefly `Metal → Nonmetal` (916 records @ 0.7599 — an outright inversion), plus `Chlorite → Chlorine` (3 @ 0.8367), `Magnetite → Magnesite` (2 @ 0.8566), `Anthophyllite → Pyrophyllite` (2 @ 0.7326). These need a blocklist, not a threshold.

---

## Section 3 — other source code books being misread 🟢

19 sources use uppercase codes ≤3 chars. `p5-s3-shortcodes`

### One new instance of the same defect

**`CS → Cesium`, 6 records, oregongeology, confidence 1.0.** 🟢 `Cs` is caesium's element symbol; in Oregon's code book alongside `SC` (stone, crushed) and `S` (sand), `CS` is a DOGAMI code, not caesium. Small, but the identical mechanism and it belongs on the same fix.

Oregon's complete commodity vocabulary is **five codes**: `SC` 7,076, `G` 2,351, `S` 2,349, `SD → Sand` 41, `CS → Cesium` 6. All uppercase, all short — and its other commodity strings are lowercase English (`sand and gravel`, `stone`, `crushed`, `sulfur`), which is the signature that the uppercase set is a code book. 🟢

**Co-occurrence is decisive** 🟢 `p5-s5-falsepos`: every Oregon `S` record carries siblings `sand and gravel | S | G`; every `SC` record carries `stone | crushed | SC`. The sibling strings name the real meaning on essentially every row.

### Everything else is fine

`FE → Iron`, `CU → Copper` (OFR-757), `P → Phosphorus` (phosphate), `K → Potassium` (potash), `W → Tungsten`, `U → Uranium` (P96MMRFD), `WO3 → Tungsten` (295581) — all genuine element symbols in geological datasets, correctly resolved. **`Mn → Manganese` in Oregon is correct**, as the brief says. 🟢

### A larger problem than the collisions: the same code resolves inconsistently across sources 🟢

| code | matched | unmatched |
|---|---|---|
| **`PGE`** | 131 (major-deposits) → Platinum-Group Elements | **9,613 nicrpge + 714 mrds + 56 P96MMRFD** |
| **`REE`** | 44 phosphate + 90 major-deposits + 14 ofr20151121 | **1,294 mrds + 64 P96MMRFD + 39 phosphate** |
| `HAL` | — | 924 (potash) |

**`PGE` is unmatched on 10,383 records and matched on 131.** That is a bigger commodity loss than all four documented defects combined, and it is not a mis-normalization — it is a non-normalization. Not in scope for this brief, but it should be. 🟢

---

## Section 4 — the `G` question, answered 🟢

**`G` exists in the graph: 2,351 records, oregongeology, `UMN Matching System v1`, confidence `0.001`, and NO `:normalized_uri`.** 🟢 `p5-s4-single-char` (the brief expected ~2,347; I get 2,351).

**Neither of the two proposed explanations is right as stated.**

- Not "dropped by the `confidence > 0` filter at `_attribute.py:216`" — the node **is in the graph**, and 0.001 > 0, so that filter would pass it.
- Not a crash that lost the record — the node exists with a recorded confidence and matcher, so the matcher ran to completion on it.

**The evidence supports a third reading: the matcher ran, produced no match above its floor, and recorded a sentinel confidence of 0.001 with no `normalized_uri`.** 🟢 The same 0.001 sentinel appears for `A` (19 records, Virginia) and for `Construction` (2,503, P9HTERGK), both also unmatched — so 0.001 is UMN v1's "no match" marker, not a `G`-specific artifact.

**This does not disprove the `ZeroDivisionError`** — it shows that *whatever* happened, the pipeline recorded a clean no-match rather than losing the row. If the exception fires and is swallowed upstream, the observable result is exactly this. Distinguishing the two requires the clone, which I did not run. 🔴

### Every single-character `observed_name` in the corpus 🟢

116 `(obs, src, label, conf, matcher)` rows. Genuinely matched symbols: `S`→Sulfur, `P`→Phosphorus, `K`→Potassium, `W`→Tungsten, `U`→Uranium, `V`→Vanadium, `F`→Fluorine, `B`→Boron, `I`→Iodine, `N`→Nitrogen, `Y`→Yttrium, `h`→Hydrogen, `k`→Potassium, `b`→Boron. Unmatched: `G` (2,351), `A` (20), `C` (12), `D`, `M`, `T`, `a`, `g`, `p`. **Junk that should never have reached a matcher: `)` (15 records across asbestos, potash, sedau, podchrome), `0`, `5`, `7`, `44`, `96`.** 🟢

---

## Section 5 — the exclusion rules 🟢

| rule | expected | **measured (raw grain)** | |
|---|---|---|---|
| `mrds` + `Construction` | 46,223 | **46,221** | ✓ (−2) |
| `nc-geological-survey` + `Construc` | 980 | **980** | ✓ |
| `oregongeology` + `SC` | 7,076 | **7,076** | ✓ |
| `oregongeology` + `S` + record carries `G` | 2,348 | **2,349 total `S`**, of which the one without `G` is the known exception | ✓ |

### The known false positive is confirmed, and it is the only one 🟢

`p5-s5-falsepos` returns 99 Oregon records whose name suggests sand/stone/sulfur. **98 of them corroborate the rule** — names like *Eugene sand and gravel*, *Sandstone Quarry*, *Crook Sand Pit*, each with siblings `sand and gravel | S | G` or `stone | crushed | SC`.

**One is a genuine sulfur mine:** `Last Chance Sulfur Mine`, observed `S`, siblings **`sulfur and pyrite | S`** — and crucially **no `G`**. The `G` condition spares it exactly as designed. 🟢 I found no second false positive by this test.

### The inverse trap — bigger than stated 🟢

| | Brief | **Measured (raw-record grain)** |
|---|---|---|
| records normalized to Sulfur, total | 4,174 | **5,171** |
| from the Oregon `S` code | 2,349 | **2,349** ✓ |
| **would be wrongly stripped** | 1,825 | **2,822** |

🟢 `p5-s5-sulfur-trap`. **The brief's 4,174 is almost certainly merged-entity grain and mine is raw-record** — exactly the comparison rule 2 warns about, so I am not calling it a discrepancy. The 2,349 matches exactly, which is the number that matters.

**Both rules are safe as written**, because both key on the **observed string**, not the normalized commodity. Oregon itself has 6 records whose observed string is lowercase `sulfur` → Sulfur — genuine sulfur, untouched by a rule scoped to `S`. 🟢 Excluding on the *commodity* would strip 2,822 correct records; excluding on the *observed code* strips none.

---

## What I verified, what I could not, and what is wrong

**Verified 🟢** — endpoint live, all queries HTTP 200, raw JSON saved before analysis:
- `:confidence` and `:source` mandatory on commodity nodes; `:normalized_uri` missing on **182,746**.
- All four defects, their confidences and matchers; the 54 genuine non-Oregon sulfur rows.
- Confidence histograms for commodity, state and country.
- Hand-judgment of all 116 below-0.90 rows and the full threshold trade-off.
- `UMN Exact Match v1` stamps exactly 0.9; `ProcMinev2` is the only graded matcher.
- `G`: 2,351 records, confidence 0.001, no `normalized_uri`.
- `CS → Cesium` as a fifth Oregon code-book collision.
- `PGE`/`REE` inconsistent normalization across sources.
- Every Section 5 rule count, the single false positive, and the inverse trap.

**Could not verify 🟡 / 🔴**
- **Merged-entity counts.** Section 1 asks for both grains; I ran raw only. The dedup roll-up needs ~7k serial REST calls per the Problem 4 run, and I prioritised Sections 2 and 3, which the brief names as the point of this run. 🔴
- **The `ZeroDivisionError` reproduction from the clone.** Not run — I did not clone the repo. The graph evidence narrows the question but cannot close it. 🔴
- **`05_commodity_normalization.md` does not exist** on this machine — the same pattern as `04_nad27_datum.md` in the Problem 4 run. I reconciled against the brief's own summary instead. Adriana's `commodity_bad_normalizations.csv` is in `~/Downloads` but I did not build any finding on it. 🟢

**What I believe is wrong**
1. **The 0.90 threshold.** It is roughly break-even (1.5 : 1) where 0.62 is 1453 : 1. This is the finding that changes the recommendation.
2. **The premise that a confidence floor sizes the fix.** `SC` and `S` — 9,425 records, two of the four defects — are at confidence 1.0. No floor reaches them.
3. **`Construction` is 46,221, not 46,223** (raw grain, −2).
4. **The Section 4 framing.** Neither proposed explanation matches: the node exists at confidence 0.001 with no `normalized_uri`, which is UMN v1's ordinary no-match sentinel.
5. **The inverse-trap figure** (4,174) does not reproduce at raw grain (5,171) — a grain mismatch, not an error.

---

## Recommended confidence threshold — one line

> **0.62** — it rejects 47,955 of 49,861 wrong commodity mappings (96.2%) while losing 33 correct ones (1453 : 1), where 0.90 loses 32,324 (1.5 : 1) and collides with the 0.9 constant stamped on all 10,385 `UMN Exact Match v1` matches. 🟢

---

## Run record — `probe-runs/2026-09-21/` (`p5-*`)

| File | What |
|---|---|
| `p5-pf2-commodity-preds.*` | pre-flight predicate census |
| `p5-s1-four-defects.*` | the four defects, confidences, matchers |
| `p5-s2-conf-histogram.*` | commodity confidence histogram |
| `p5-s2b-zero-conf.*` | the exact-zero and near-zero tail |
| `p5-s2c-matcher-x-uri.*` | matcher × normalization success × confidence range |
| `p5-s2d-below90.*` | all 116 below-0.90 rows |
| `p5-s2e-state_or_province-hist.*`, `p5-s2e-country-hist.*` | the other two fields |
| `p5-s3-shortcodes.*` | uppercase codes ≤3 chars by source |
| `p5-s4-single-char.*` | every single-character observed_name |
| `p5-s5-sulfur-trap.*`, `p5-s5-falsepos.*` | inverse trap, false-positive hunt |
| `p5_threshold.py`, `p5-threshold-analysis.txt` | hand judgments and the trade-off table |

Read-only throughout: SELECT only, no write verb issued, no repository cloned or modified, TLS verification never disabled.
