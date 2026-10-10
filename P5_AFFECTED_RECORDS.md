# P5_AFFECTED_RECORDS.md — the below-0.90 list, short codes, and false positives

*Aditi Bombe · USC ISI · run 2026-09-21 · **read-only**. Companion to `P5_DIAGNOSIS.md`.*
*Confidence: 🟢 verified · 🟡 likely · 🔴 assumed. **Raw-record grain** (`COUNT(DISTINCT ?site)`) unless stated.*

---

## Lead: a 0.90 floor is roughly break-even; 0.62 is 1453 : 1 🟢

| floor | records cut | **WRONG fixed** | **GOOD lost** | ratio |
|---|---|---|---|---|
| 0.55 | 47,241 | 47,226 | 15 | 3148 : 1 |
| 0.60 | 47,976 | 47,955 | 16 | 2997 : 1 |
| **0.62** | **47,993** | **47,955** | **33** | **1453 : 1** |
| 0.65 | 48,439 | 47,967 | 437 | 110 : 1 |
| 0.70 | 50,819 | 48,938 | 1,802 | 27 : 1 |
| 0.72 | 51,607 | 48,938 | 2,544 | 19 : 1 |
| 0.75 | 54,875 | 48,940 | 5,810 | 8.4 : 1 |
| 0.80 | 78,341 | 49,856 | 28,352 | 1.8 : 1 |
| 0.85 | 82,140 | 49,859 | 32,148 | 1.6 : 1 |
| **0.90** | 82,318 | 49,861 | **32,324** | **1.5 : 1** |

Of the 82,318 records below 0.90: **49,861 WRONG (60.6%), 32,324 correct (39.3%), 133 partial (0.2%)**.

**The 0.72–0.90 band is 97% legitimate** (GOOD 29,780 vs WRONG 923). **Below 0.72 is 95% wrong** (WRONG 48,938 vs GOOD 2,544). That boundary, not 0.90, is where the signal changes.

⚠️ **0.90 is the exact constant `UMN Exact Match v1` stamps on all 10,385 of its matches.** `confidence > 0.90` destroys every one; `>= 0.90` spares them. A floor at 0.62 avoids the boundary entirely. 🟢

### Wrong matches that no sub-0.90 floor catches — these need a blocklist 🟢

| records | conf | observed | → normalized |
|---|---|---|---|
| 840 | 0.7599 | `Metal` | **Nonmetal** (mrds) — an outright inversion |
| 76 | 0.7599 | `Metal` | **Nonmetal** (nc-geological-survey) |
| 3 | 0.8367 | `Chlorite` | Chlorine |
| 2 | 0.8566 | `Magnetite` | Magnesite |
| 2 | 0.7326 | `Anthophyllite` | Pyrophyllite |

---

## Section 2 — every below-0.90 commodity match, in full

All 116 distinct `(observed, normalized, source)` rows, 82,318 raw records, each hand-judged. 🟢 `p5-s2d-below90`

| records | conf | observed | → normalized | source | verdict |
|---|---|---|---|---|---|
| 46221 | 0.5453 | `Construction` | Strontium | mrds | **WRONG** |
| 17461 | 0.7715 | `Crushed/Broken` | Stone > Crushed/Broken | mrds | correct |
| 3427 | 0.7798 | `General` | Clay > General | mrds | correct |
| 3081 | 0.7469 | `Dimension` | Limestone > Dimension | mrds | correct |
| 2391 | 0.8494 | `Fire Clay (Refractory)` | Clay > Fire (Refractory) | mrds | correct |
| 1033 | 0.7553 | `Kaolin` | Clay > Kaolin | mrds | correct |
| 1008 | 0.8119 | `Bentonite` | Clay > Bentonite | mrds | correct |
| 980 | 0.5368 | `Construc` | Cobalt | nc-geological-survey | **WRONG** |
| 840 | 0.7599 | `Metal` | Nonmetal | mrds | **WRONG** |
| 723 | 0.7161 | `Sulfur-Pyrite` | Sulfur > Iron Pyrite | mrds | correct |
| 710 | 0.6815 | `Niobium (Columbium)` | Niobium | mrds | correct |
| 487 | 0.5950 | `Volcanic Materials` | Clay > Bloating Material | mrds | **WRONG** |
| 466 | 0.6753 | `Halite` | Alunite | mrds | **WRONG** |
| 456 | 0.6734 | `Salt` | Aluminum | mrds | **WRONG** |
| 449 | 0.6705 | `Garnet` | Abrasive > Garnet | mrds | correct |
| 261 | 0.6281 | `Oil Shale` | Petroleum (Oil) > Oil Shale | mrds | correct |
| 221 | 0.5556 | `Water` | Slate | mrds | **WRONG** |
| 221 | 0.7715 | `Crushed/Broken` | Stone > Crushed/Broken | nc-geological-survey | correct |
| 170 | 0.8073 | `Sulfuric Acid` | Sulfur > Sulfuric Acid | mrds | correct |
| 148 | 0.8431 | `Contained Or Metal` | Aluminum > Contained Or Metal | mrds | correct |
| 119 | 0.6970 | `Corundum` | Abrasive > Corundum | mrds | correct |
| 99 | 0.7553 | `Kaolin` | Clay > Kaolin | nc-geological-survey | correct |
| 76 | 0.7599 | `Metal` | Nonmetal | nc-geological-survey | **WRONG** |
| 67 | 0.7902 | `Ferrochrome` | Chromium > Ferrochrome | mrds | correct |
| 65 | 0.6226 | `Pigment` | Mineral Pigments | mrds | correct |
| 64 | 0.7462 | `Refiner` | Gold > Refinery | mrds | correct |
| 63 | 0.7611 | `High Calcium` | Limestone > High Calcium | mrds | correct |
| 62 | 0.8632 | `Fullers Earth` | Clay > Fullers Earth | mrds | correct |
| 60 | 0.7343 | `Ultra Pure` | Limestone > Ultra Pure | mrds | correct |
| 60 | 0.7469 | `Dimension` | Limestone > Dimension | nc-geological-survey | correct |
| 49 | 0.6872 | `Emery` | Gemstone > Emerald | mrds | **WRONG** |
| 48 | 0.7747 | `Lignite` | Coal > Lignite | mrds | correct |
| 40 | 0.7017 | `Sodium Sulfate` | Sodium > Salt | mrds | partial |
| 38 | 0.6663 | `Aggregate` | Aggregate > Light Weight | mrds | partial |
| 38 | 0.7571 | `Light Weight` | Aggregate > Light Weight | mrds | correct |
| 37 | 0.8906 | `Bloating Material` | Clay > Bloating Material | mrds | correct |
| 32 | 0.6281 | `Oil Sands` | Petroleum (Oil) > Oil Sands | mrds | correct |
| 31 | 0.8256 | `Bituminous` | Coal > Bituminous | mrds | correct |
| 30 | 0.6265 | `Sodium Carbonate` | Sodium | mrds | partial |
| 28 | 0.6474 | `Smelter` | Lead > Smelter | mrds | correct |
| 28 | 0.6970 | `Corundum` | Abrasive > Corundum | nc-geological-survey | correct |
| 28 | 0.7591 | `Ferrosilicon` | Silica > Ferrosilicon | mrds | correct |
| 25 | 0.6985 | `Talc` | Talc-Soapstone | nc-geological-survey | correct |
| 25 | 0.8740 | `Montmorillonite` | Clay > Montmorillonite | mrds | correct |
| 24 | 0.8035 | `Iron-Pyrite` | Iron > Pyrite | mrds | correct |
| 22 | 0.7798 | `General` | Clay > General | nc-geological-survey | correct |
| 18 | 0.7161 | `Sulfur-Pyrite` | Sulfur > Iron Pyrite | nc-geological-survey | correct |
| 17 | 0.6815 | `Niobium (Columbium)` | Niobium | nc-geological-survey | correct |
| 17 | 0.8853 | `Mica?` | Mica | nc-geological-survey | correct |
| 15 | 0.6048 | `Rock Asphalt` | Petroleum (Oil) > Rock Asphalt | mrds | correct |
| 14 | 0.5004 | `Industrial/Frac Sand` | Sand | mrds | correct |
| 14 | 0.6454 | `Crushed Stone` | Stone > Crushed/Broken | nc-geological-survey | correct |
| 12 | 0.8332 | `Ferromanganese` | Manganese > Ferromanganese | mrds | correct |
| 11 | 0.4998 | `Industrial` | Indium | mrds | **WRONG** |
| 11 | 0.5174 | `Monazite` | Magnesite | nc-geological-survey | **WRONG** |
| 11 | 0.6705 | `Garnet` | Abrasive > Garnet | nc-geological-survey | correct |
| 11 | 0.7931 | `Refinery` | Gold > Refinery | mrds | correct |
| 8 | 0.5833 | `Soda Ash` | Ash | mrds | **WRONG** |
| 8 | 0.6423 | `Clay (Halloysite)` | Clay > Chlorite | nc-geological-survey | **WRONG** |
| 8 | 0.8494 | `Fire Clay (Refractory)` | Clay > Fire (Refractory) | nc-geological-survey | correct |
| 7 | 0.7604 | `Mill Concentrate` | Tungsten > Mill Concentrate | mrds | correct |
| 7 | 0.7841 | `Soapstone` | Talc-Soapstone | nc-geological-survey | correct |
| 7 | 0.8718 | `Titanium-Ilmenite` | Titanium > Ilmenite | mrds | correct |
| 6 | 0.7184 | `Magnesium Compounds` | Magnesium | mrds | partial |
| 6 | 0.7521 | `Beryl` | Beryllium | nc-geological-survey | partial |
| 6 | 0.8609 | `Subbituminous` | Coal > Subbituminous | mrds | correct |
| 5 | 0.5851 | `Columbite-Tantalite` | Tantalum | nc-geological-survey | partial |
| 5 | 0.6978 | `Sandstone` | Stone | mrds | partial |
| 5 | 0.7611 | `High Calcium` | Limestone > High Calcium | nc-geological-survey | correct |
| 5 | 0.8569 | `Titanium-Rutile` | Titanium > Rutile | mrds | correct |
| 4 | 0.5954 | `Galena` | Gallium | nc-geological-survey | **WRONG** |
| 4 | 0.8513 | `Stn?` | Stone | nc-geological-survey | correct |
| 3 | 0.5576 | `Chalcopyrite` | Clay > Chlorite | nc-geological-survey | **WRONG** |
| 3 | 0.5913 | `Sillimanite` | Silica | nc-geological-survey | **WRONG** |
| 3 | 0.8367 | `Chlorite` | Chlorine | mrds | **WRONG** |
| 3 | 0.8602 | `High Alumina Clay` | Aluminum > High Alumina Clay | mrds | correct |
| 3 | 0.8779 | `Dimension Stone` | Limestone > Dimension | nc-geological-survey | correct |
| 3 | 0.8906 | `Bloating Material` | Clay > Bloating Material | nc-geological-survey | correct |
| 2 | 0.6261 | `Iron Oxide Pigments` | Iron > Pig Iron | mrds | **WRONG** |
| 2 | 0.6349 | `Bornite` | Granite | nc-geological-survey | **WRONG** |
| 2 | 0.6449 | `Alabaster` | Gypsum-Anhydrite > Alabaster | mrds | correct |
| 2 | 0.7326 | `Anthophyllite` | Pyrophyllite | nc-geological-survey | **WRONG** |
| 2 | 0.7878 | `Molybdenite` | Molybdenum | nc-geological-survey | partial |
| 2 | 0.8122 | `Hectorite` | Clay > Hectorite | mrds | correct |
| 2 | 0.8566 | `Magnetite` | Magnesite | nc-geological-survey | **WRONG** |
| 2 | 0.8750 | `Tantalum From Tin Slag` | Tantalum > Tin Slag | mrds | correct |
| 1 | 0.5186 | `Tripoli` | Lithium | mrds | **WRONG** |
| 1 | 0.5318 | `Tourmaline` | Staurolite | nc-geological-survey | **WRONG** |
| 1 | 0.5455 | `Muscovite Mica` | Mica | nc-geological-survey | correct |
| 1 | 0.5488 | `Halloysite` | Alunite | nc-geological-survey | **WRONG** |
| 1 | 0.5623 | `Vesuvianite` | Kyanite | nc-geological-survey | **WRONG** |
| 1 | 0.5632 | `Hematite` | Diatomite | nc-geological-survey | **WRONG** |
| 1 | 0.5856 | `Gilsonite` | Wollastonite | mrds | **WRONG** |
| 1 | 0.5910 | `Apatite` | Graphite | nc-geological-survey | correct |
| 1 | 0.6165 | `Copper And Garnet` | Copper | nc-geological-survey | correct |
| 1 | 0.6198 | `Kaolin/ Feldspar` | Feldspar | nc-geological-survey | correct |
| 1 | 0.6242 | `Road Gravel??` | Sand and Gravel | nc-geological-survey | correct |
| 1 | 0.6313 | `Feld?` | Feldspar | nc-geological-survey | correct |
| 1 | 0.6574 | `Ilmenite` | Titanium > Ilmenite | nc-geological-survey | correct |
| 1 | 0.6637 | `Pyrrrhotite` | Pyrite | nc-geological-survey | correct |
| 1 | 0.6663 | `Aggregate` | Aggregate > Light Weight | nc-geological-survey | partial |
| 1 | 0.6795 | `Lime` | Limestone | nc-geological-survey | correct |
| 1 | 0.6876 | `Quartz Crystal` | Quartz | nc-geological-survey | correct |
| 1 | 0.6902 | `Iron? Feldspar?` | Feldspar | nc-geological-survey | correct |
| 1 | 0.6971 | `Mica? Feldspar?` | Feldspar | nc-geological-survey | correct |
| 1 | 0.7138 | `Allanite?` | Alunite | nc-geological-survey | correct |
| 1 | 0.7369 | `Soapstone?` | Talc-Soapstone | nc-geological-survey | correct |
| 1 | 0.7563 | `Tailings` | Tin > Tailings | mrds | correct |
| 1 | 0.7584 | `Allanite` | Alunite | nc-geological-survey | correct |
| 1 | 0.7666 | `Iron Sulfides` | Sulfides | nc-geological-survey | correct |
| 1 | 0.7741 | `Chromite` | Chromium | nc-geological-survey | correct |
| 1 | 0.7817 | `Contained Or Me` | Aluminum > Contained Or Metal | nc-geological-survey | correct |
| 1 | 0.8073 | `Sulfuric Acid` | Sulfur > Sulfuric Acid | nc-geological-survey | correct |
| 1 | 0.8489 | `Dimension Stone?` | Limestone > Dimension | nc-geological-survey | correct |
| 1 | 0.8519 | `Olvine` | Olivine | nc-geological-survey | correct |
| 1 | 0.8838 | `K-Feldspar` | Feldspar | nc-geological-survey | correct |
---

## Section 2b — the other two fields

| field | nodes below 0.90 | population | share |
|---|---|---|---|
| **commodity** | **125,424** | 1,379,833 | 9.1% |
| `state_or_province` | 10,732 | ~421,592 | 2.5% |
| `country` | **382** | ~450,574 | **0.08%** |

🟢 `p5-s2e-*`. A floor tuned for commodity is **nearly inert** for the other two. And `P2_AFFECTED_RECORDS.md` established that the state matcher's real failures sit at *high* confidence (`Florida → Puerto Rico` at 0.9999), so a floor does not address them either. **Apply one threshold if you like, but do not describe it as fixing state or country.** 🟡

### Why a floor is the wrong instrument for 182,746 records 🟢

| matcher | matched | **unmatched** | confidence range |
|---|---|---|---|
| UMN Matching System-ProcMinev2 | 635,449 | 0 | **0.4998 – 0.9999** |
| SRI database agent v0 | 299,575 | **79,480** | **1.0 only** |
| UMN Matching System v1 | 192,018 | **102,843** | 1.0 / 0.001–1.0 |
| Inferlink Extraction v3 | 39,962 | 396 | 1.0 |
| SAND | 19,683 | 27 | 0.99–1.0 / **0.0** |
| UMN Exact Match v1 | 10,385 | 0 | **exactly 0.9** |

**`ProcMinev2` is the only matcher emitting a graded confidence.** Every other stamps a constant. **79,480 SRI nodes carry confidence 1.0 with no match at all** — invisible to any floor. 🟢 `p5-s2c-matcher-x-uri`

---

## Section 3 — short uppercase codes by source 🟢

19 sources use codes ≤3 characters. `p5-s3-shortcodes`

### Oregon (`www.oregongeology.org`) — the whole vocabulary is five codes

| code | records | → normalized | conf | verdict |
|---|---|---|---|---|
| `SC` | 7,076 | **Scandium** | 1.0 | **WRONG** — Stone, Crushed |
| `G` | 2,351 | *(unmatched)* | 0.001 | unmatched — see Section 4 |
| `S` | 2,349 | **Sulfur** | 1.0 | **WRONG** — Sand |
| `SD` | 41 | Sand | 1.0 | correct |
| **`CS`** | **6** | **Cesium** | **1.0** | **WRONG — new finding**, a DOGAMI code, not caesium |

Oregon's non-code commodity strings are lowercase English (`sand and gravel`, `stone`, `crushed`, `sulfur`) — the signature that the uppercase set is its own code book. **Co-occurrence confirms the meanings**: every `S` record carries siblings `sand and gravel | S | G`; every `SC` record carries `stone | crushed | SC`. 🟢

### Every other source's codes are genuine element symbols — no action

`FE → Iron`, `CU → Copper` (OFR-757) · `P → Phosphorus` (phosphate, ofr20151121) · `K → Potassium` (potash) · `W → Tungsten`, `U → Uranium`, `V → Vanadium`, `F → Fluorine`, `B → Boron` (P96MMRFD, major-deposits) · `WO3 → Tungsten` (295581) · `SDG → Sand and Gravel`, `CLY → Clay` (OFR-757) · `N → Nitrogen` (Virginia). **`Mn → Manganese` in Oregon is correct.** 🟢

### A larger problem than the collisions: the same code resolves inconsistently 🟢

| code | matched | **unmatched** |
|---|---|---|
| **`PGE`** | 131 (major-deposits) | **9,613 nicrpge · 714 mrds · 56 P96MMRFD = 10,383** |
| **`REE`** | 44 phosphate · 90 major-deposits · 14 ofr20151121 | **1,294 mrds · 64 P96MMRFD · 39 phosphate = 1,397** |
| `HAL` | — | 924 (potash) |

**`PGE` is unmatched on 10,383 records and matched on 131** — a larger commodity loss than all four documented defects combined. Not a mis-normalization but a non-normalization; out of this brief's scope, and it should not stay there.

### Junk that reached the matcher at all 🟢

`)` — 15 records (asbestos 6, potash 5, sedau 3, podchrome 1) · `0`, `5`, `7`, `44`, `96`, `68)` — 1 each. All unmatched at confidence 1.0.

---

## Section 4 — every single-character `observed_name` 🟢

`p5-s4-single-char`, 116 rows. **`G`: 2,351 records, oregongeology, UMN v1, confidence 0.001, no `normalized_uri`.**

**Matched symbols (correct):** `S`→Sulfur · `P`→Phosphorus-Phosphates · `K`→Potassium · `W`→Tungsten · `U`→Uranium · `V`→Vanadium · `F`→Fluorine-Fluorite · `B`→Boron-Borates · `I`→Iodine · `N`→Nitrogen-Nitrates · `Y`→Yttrium · `h`→Hydrogen · `k`→Potassium · `b`→Boron-Borates.

**Unmatched single characters:** `G` 2,351 · `A` 20 · `C` 12 · `D` 2 · `M` 2 · `T` 1 · `a` 1 · `g` 1 · `p` 3 — each a potential crash site under the `sorensen_dice` hypothesis.

**The 0.001 sentinel is not `G`-specific**: `A` (19, Virginia) and `Construction` (2,503, P9HTERGK) carry it too, both unmatched. It is UMN v1's ordinary no-match marker. 🟢

---

## Section 5 — the exclusion rules and their false positives

| rule | expected | measured | |
|---|---|---|---|
| `mrds` + `Construction` | 46,223 | **46,221** | ✓ (−2) |
| `nc-geological-survey` + `Construc` | 980 | **980** | ✓ |
| `oregongeology` + `SC` | 7,076 | **7,076** | ✓ |
| `oregongeology` + `S` + carries `G` | 2,348 | **2,349 total `S`**, 1 lacks `G` | ✓ |

### False-positive hunt — 99 candidates examined, exactly one real 🟢

`p5-s5-falsepos` returned 99 Oregon records whose site name mentions sand, stone, sulfur, scandium or cesium. **98 corroborate the rule** — *Eugene sand and gravel*, *Sandstone Quarry*, *Crook Sand Pit*, *Short Sand Rock*, each carrying `sand and gravel | S | G` or `stone | crushed | SC`.

**The one genuine exception:**

| site | observed | siblings | carries `G`? |
|---|---|---|---|
| **Last Chance Sulfur Mine** | `S` | **`sulfur and pyrite | S`** | **no** |

The `G` condition spares it exactly as designed. **No second false positive was found by this test.** 🟢

### The inverse trap 🟢

| | Brief | **Measured (raw-record grain)** |
|---|---|---|
| records normalized to Sulfur | 4,174 | **5,171** |
| from the Oregon `S` code | 2,349 | **2,349** ✓ |
| would be wrongly stripped | 1,825 | **2,822** |

The brief's 4,174 is almost certainly **merged-entity grain** against my raw-record grain, so this is a grain mismatch rather than a disagreement — the 2,349 that matters matches exactly. 🟡

**Both rules are safe as written**, because both key on the **observed string**, not the normalized commodity. Oregon itself carries 6 records whose observed string is lowercase `sulfur` → Sulfur — genuine, and untouched by a rule scoped to `S`. Excluding on the *commodity* would strip 2,822 correct records; excluding on the *observed code* strips none. 🟢

---

## Recommended threshold — one line

> **0.62** — rejects 47,955 of 49,861 wrong commodity mappings (96.2%) while losing 33 correct ones (1453 : 1), where 0.90 loses 32,324 (1.5 : 1) and collides with the 0.9 constant stamped on all 10,385 `UMN Exact Match v1` matches. 🟢

**And the floor is only half the fix:** `SC` (7,076) and `S` (2,349) are at confidence **1.0** and need the source-scoped exclusion rule. The floor addresses 47,201 of the 56,626 defective records; the exclusion rules address the remaining 9,425.
