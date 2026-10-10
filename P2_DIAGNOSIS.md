# Problem 2 — proper diagnosis

*Aditi Bombe · 7 September 2026 · run record in `probe-runs/2026-09-07/` · read-only, 17 queries*
*Confidence: 🟢 verified from a saved response · 🟡 likely · 🔴 assumed*

**Scope note: Part 1 of the brief ran in full. Part 2 (2.1–2.4) was not run.** Everything below is Part 1.

---

## Headline: the recommendation does not change, but the number does

**The country side of a conflict is trustworthy. 🟢** In 99.38% of conflicts the record's *state* is the failure and its country is correct, so constraining state candidates to the already-normalized country is a sound fix and not error propagation. This was the load-bearing assumption and it holds.

**But the 83.9% figure was the rule grading itself, and it needs restating.** Re-derived per record and hand-audited against a random sample, the honest claim is:

> A suffix-stripping, diacritic-folding, country-constrained matcher resolves **5,144 of 6,156 conflicts (83.6%)**, and hand adjudication of 30 randomly drawn resolutions found **30 of 30 correct (95% Wilson interval 88.6%–100%)**. Combining the two, the rule correctly fixes an estimated **74.1%–83.6% of all conflicts**. 🟢

Quote the interval, not the point figure. The previous "83.9%" was the *resolution* rate presented as if it were an *accuracy* rate; they are different quantities and only the first was measured.

---

## 1.1 — Is the country side trustworthy?

Every conflict row, with the raw observed country string beside the normalized country label. 358 distinct combinations covering 6,159 site-rows (6,156 distinct sites). Classified offline against an explicit alias table built by reading the actual mismatches, not by guessing.

| Class | Sites | Share |
|---|---|---|
| **state-wrong** — observed and normalized country agree; the state is the failure | **6,121** | **99.38%** |
| country-wrong — the country normalization itself failed | **4** | **0.06%** |
| country-ambiguous — defensible but not certain | 9 | 0.15% |
| both-wrong | 0 | 0.00% |
| undecidable — no observed country string at all | 25 | 0.41% |

**Country-side failure is 0.06%, or 0.21% counting every ambiguous case against us.** The brief set the threshold at "more than a percent or two". We are an order of magnitude below it. 🟢

Only 13 sites are anything other than clean, and all of them are listed here in full:

**Genuinely wrong country normalizations (4 sites):**

| Observed country | Normalized to | Observed state → matched state | Sites |
|---|---|---|---|
| `Slovak Republic` | **Central African Republic** | `Banska Bystricka Region` → `Banská Bystrica Region` | 2 |
| `Korea, Republic of` | **Democratic Republic of the Congo** | `Ch'Ungch'Ong-Bukto` → `Changhua` | 1 |
| `Korea, Republic of` | **Democratic Republic of the Congo** | `Ch'Ungch'Ong-Namdo` → `Changhua` | 1 |

Note the pattern: `Slovak Republic` → `Central African Republic` and `Korea, Republic of` → `Democratic Republic of the Congo` are the **same fuzzy-matching failure on the token "Republic"** that afflicts the state side. The Slovak case is a *pure* country failure — its state matched correctly. The two Korea cases are wrong on both sides.

**Ambiguous (9 sites):** `Korea` → `North Korea` (8 sites; the unqualified string could be either Korea, and the paired states are South Korean provinces, so this is probably wrong too) and `Germany and Czech Republic` → `Czech Republic` (1 site; a two-country string partially matched).

**Benign alias mismatches, counted as state-wrong** — these are correct normalizations with a different surface form, each inspected individually: `Congo (Kinshasa)` → DR Congo (93), `Democratic Republic of Congo` → DR Congo (9), `Malawai` → Malawi (3, a source typo matched correctly), `USA` → United States (3), `Fiji` → Fiji Islands (2), `Republic of Portugal` → Portugal (2), `Republic of Congo` → Congo (1), `Côte d'Ivoire` → Cote D'Ivoire (Ivory Coast) (1), `Korea, North` → North Korea (1).

### The two failure modes inside "state-wrong" 🟢

Splitting the 6,121 by whether the *matched* state's label is the observed name:

| Failure mode | Sites | Share | Fixed by |
|---|---|---|---|
| **Wrong name entirely** — matcher picked a different word (`La Paz` → `La Pampa`) | **3,328** | 54.4% | suffix-stripping + diacritic-folding **and** the country constraint |
| **Homonym** — right name, entity in the wrong country (`Florida` → Florida, Puerto Rico) | **2,793** | 45.6% | **the country constraint alone** |

This is worth saying at the meeting: **45.6% of the problem is fixed by the country constraint on its own**, before any text normalisation. That is the cheapest half.

---

## 1.2 — Which matcher, and how many?

**Ten distinct matchers write state candidates, not the four the earlier runs saw.** Six are automated; four are individual human users. 🟢

| Matcher | Candidates | Normalized | Conflicts | Conflict rate | Never matched | Never rate |
|---|---|---|---|---|---|---|
| **UMN Matching System-ProcMinev2** | 300,045 | 300,045 | **5,668** | **1.89%** | **0** | 0.00% |
| **UMN Matching System v1** | 117,050 | 114,857 | 322 | 0.28% | **2,193** | 1.87% |
| **UMN Exact Match v1** | 2,836 | 1,839 | 25 | 1.36% | **997** | **35.16%** |
| **Inferlink Extraction v3** | 1,218 | 1,140 | 97 | **8.51%** | 84 | 6.90% |
| **SAND** | 372 | 372 | 43 | **11.56%** | 0 | 0.00% |
| Inferlink Extraction v2 | 5 | 5 | 1 | 20.00% | 0 | 0.00% |
| 4 human users | 29 | 29 | 0 | 0.00% | 0 | 0.00% |
| **All** | **421,555** | **418,287** | **6,156** | **1.47%** | **3,274** | **0.78%** |

**Answer to "change what, exactly?": one component, for the conflicts.** ProcMinev2 produces **5,668 of 6,156 conflicts — 92.1%**. A fix scoped to that single matcher covers almost the whole disagreement list. 🟢

**But the two symptoms come from different components,** and this corrects the earlier framing that treated them as one root cause with two faces:

- **Conflicts** are ProcMinev2 (92.1%).
- **Never-matched** is UMN v1 (2,193) plus Exact Match v1 (997) — **97.4%** — and ProcMinev2 contributes **exactly zero**.

The reason is a design difference worth naming: **ProcMinev2 never abstains.** It normalized 300,045 of 300,045 candidates and left none unmatched, so its failures are always *wrong answers*. UMN v1 and Exact Match v1 do abstain, so their failures are *missing answers*. Fixing ProcMinev2's scoring will not recover a single never-matched record, and fixing v1's recall will not remove a single conflict.

**By rate rather than volume, the worst offenders are different again:** SAND (11.56%) and Inferlink v3 (8.51%) are 4–6× ProcMinev2's conflict rate. They are small today (372 and 1,218 candidates) but if either scales, it scales the problem faster than ProcMinev2 does. Worth flagging as a forward risk rather than a present cost.

---

## 1.3 — A real spot check

**Method.** The rule was re-applied per record rather than per name-group, giving 5,144 resolved and 1,012 unresolved of 6,156. Samples drawn with `random.Random(20260907)` over sites sorted by URI — seed and procedure recorded in `spotcheck_sample.py`, sample itself frozen in `1.3-sample.json` so it can be re-audited.

**Result: 30 of 30 correct. 95% Wilson interval [88.6%, 100.0%]. No disagreements.** 🟢

The sample spans 13 countries and every failure class: homonyms (`Florida`→Q6850 United States, `Bolivar`→Q6958 Venezuela, `Santa Catarina`→Q2508 Brazil), suffix cases (`La Paz`→Q2453 La Paz Department ×5, `Oruro`→Q2454, `Potosi`→Q2456, `Santa Cruz`→Q2457, `Granma`→Q2890 Granma Province, `Bong`→Q4215 Bong County), diacritics (`Limon`→Q2830 Limón Province, `Osaka`→Q3943 Ōsaka Prefecture, `Darien`→Q5069 Darién Province), and combinations (`Saint Ann`→Q3903 Saint Ann Parish, Jamaica).

**Two records flagged — the rule is right, something else is wrong:**

- **#17** `Oruro` / Bolivia → `Oruro Department`. Correct given the inputs, but the stored coordinate is (−10.46, −66.47), roughly **900 km north** of Oruro, in Pando or Beni. Either the coordinate or the state string is wrong; the matcher cannot be blamed and cannot do better.
- **#13** `La Paz` / Bolivia → `La Paz Department`. Coordinate (−17.43, −66.98) sits near the Cochabamba border — marginal rather than wrong.

These matter for the fix design: **the coordinate cannot be used as an independent check on the state without discovering a second class of defect.** Roughly 1 in 15 of the sample had a coordinate that disagrees with its own state label.

**Caveat on method 🟡:** adjudication used the vocabulary (which country each entity belongs to — verifiable) plus my geographic judgement of whether the stored coordinate falls in the named state. The latter is judgement, not a computed polygon containment test. For 28 of 30 the name-plus-country logic alone is decisive and the coordinate merely corroborates.

### The 1,012 the rule does not resolve 🟢

| Class | Sites | Share |
|---|---|---|
| **C. Name absent from the vocabulary entirely** | **771** | 76.2% |
| **A. A two-letter CODE sitting in a name field** | **184** | 18.2% |
| No observed state name at all | 25 | 2.5% |
| B. Name exists, but only under another country | 17 | 1.7% |
| Ambiguous — more than one in-country match | 15 | 1.5% |

**Class A is a new finding and it is an extractor defect, not a matching one.** 184 records carry a bare two-letter US state code where a name belongs — `CO` 51, `CA` 46, `MN` 16, `ME` 15, `SD` 12, `MO` 11, `AR` 10, `SC` 10, `PA` 5 — and the matcher has fuzzy-matched them to random world provinces: `CO`→Colonia (Uruguay), `CA`→Canelones (Uruguay), `MO`→Montevideo, `SD`→Saada (Yemen), `MN`→Matabeleland North (Zimbabwe). **No name matcher should be expected to resolve `CO`.** Two separate fixes are implied: expand codes upstream, and make the matcher refuse two-character inputs rather than fuzzy-matching them.

**Class C is not one bucket.** The top entries show at least four sub-types: true renames (`Orissa` 187, `Katanga` 93+18), exonyms where the vocabulary holds the English form (`Niedersachsen` 43 — vocabulary has Lower Saxony; `Karnten` — Carinthia), sovereign entities that are not states of anything (`Greenland` 15, `Territory Of New Caledonia And Dependencies` 49), and cities in a state field (`Ekaterinburg` 19). Only the first genuinely needs new vocabulary entries. *(A full classification was scheduled as Part 2.2 and did not run.)*

---

## Restated recommendation

1. **Fix ProcMinev2.** It is 92.1% of the conflict problem, in one component. Three changes, in descending value: constrain candidates to the already-normalized country (fixes 45.6% of conflicts on its own), fold diacritics, strip a trailing `Department`/`Province`/`Parish`/`Region`/`Prefecture`/`County`. Expected effect **74.1%–83.6% of conflicts correctly resolved**, hand-verified at 30/30 on a random sample. 🟢
2. **Make any matcher refuse inputs of two characters or fewer.** 184 records are currently matched from bare state codes to unrelated provinces. Cheap, and it prevents a category of confidently-wrong output. 🟢
3. **Fix recall separately, in UMN v1 and Exact Match v1.** They own 97.4% of the never-matched population and none of the conflicts. This is a different change to a different component and should be a different ticket. 🟢
4. **Do not use the stored coordinate to validate a state match** until the coordinate defect surfaced in 1.3 is understood — 2 of 30 sampled records have coordinates that disagree with their own state.
5. **The country side needs no work.** 0.06% failure. The four bad cases share the `…Republic` token-matching flaw and would be swept up by the same normalisation fix applied country-side. 🟢

## What this run did not do

Part 2 was not run: reverse-engineering Adriana's Problem 3 count (2.1), the full classification of the ~3,100 vocabulary residue (2.2), where the conflicts land geographically (2.3), and the repository reads (2.4). The repository reads remain blocked on a checkout that is not on this machine, and I have not cloned.
