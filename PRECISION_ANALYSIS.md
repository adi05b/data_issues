# Do decimal places actually measure precision?

*Aditi Bombe · 8 September 2026 · run record in `probe-runs/2026-09-08/` · read-only, 7 queries*
*Confidence: 🟢 verified from a saved response · 🟡 likely · 🔴 assumed*

**What this is.** Adriana's error model is sound and is hers. This run tests one input assumption it cannot see: that stored decimal places reflect how precisely the source measured. That holds for decimal-degree coordinates and fails for degrees-and-minutes conversions, which MinMod contains.

**One caveat on inputs, stated up front 🔴:** Adriana's spreadsheets are not in this folder. I have only the three anchor figures quoted in the brief — 0 dp → ±70.3 km, 1 dp → ±7.0 km, 2 dp → ±702.5 m — and her cap at 5 dp. Everything below extrapolates a ÷10-per-decimal progression from those three points (base 70.25 km at a 1° grid), which those three anchors fit exactly. **If her actual table differs, the ratios below need recomputing, though their direction will not change.**

---

## THE CONTROL — read this before any finding below

The detector is worthless if it cannot recognise decimal-degree data as decimal degrees. MRDS publishes decimal degrees at 5 places and has no coarse coordinates, so it is the control. **All 304,610 of its EPSG:4326 records were run through the detector, not a sample.** 🟢

| | Longitude | Latitude |
|---|---|---|
| **Classified decimal degrees (correct)** | **99.50%** | **99.18%** |
| whole-degree false positive | 0.005% | 0.006% |
| **arcminute false positive** | **0.047%** | **0.114%** |
| **arcsecond false positive** | **0.451%** | **0.701%** |
| total misclassified | 0.50% | 0.82% |

**The detector passes.** The brief's threshold was "more than a percent or two would mean it is broken"; the observed misclassification is 0.50%–0.82%. 🟢

**But the two tests are not equally strong, and that changes how the results below must be read:**

- **The arcminute test is reliable** — 0.047%–0.114% false positive. 🟢
- **The arcsecond test is weak** — 0.45%–0.70%, roughly 60–100× higher than chance would predict. The cause is arithmetic, not tolerance: a 5-decimal value `v = k/100000` gives `v × 3600 = 0.036k`, which is a whole number whenever `k` is a multiple of 250 — that is, whenever `v` is a multiple of 0.0025° (exactly 9 arcseconds). That happens to 1 in 250 random 5-decimal values = 0.40%, which is almost exactly the observed rate. **These are exact hits, so no tightening of the tolerance removes them.** 🟢

**Consequence:** arcminute findings are firm; arcsecond findings carry a ~0.5% floor of false positives and are used below only where the source-level rate is far above that floor.

### Tolerance, chosen from float64 behaviour rather than guessed 🟢

Exhaustive scan of every whole degree-and-minute value from 0° to 180°: the worst residual after multiplying by 60 is **9.1 × 10⁻¹³**; the worst after multiplying by 3600, over every whole degree-and-second value, is **5.8 × 10⁻¹¹**. (`7 + 25/60` round-trips to `7.416666666666667` and leaves a residual of exactly 0.)

**Chosen tolerance: 1 × 10⁻⁸.** It sits 172× above the worst genuine conversion residual, so no real DMS value is missed, while a random 6-decimal value has only a 0.00012% chance of landing on the arcminute grid and 0.0072% on the arcsecond grid by luck. Looser values were rejected: at 1 × 10⁻⁶ the chance arcsecond false-positive rate rises to 0.72%.

**Only values carrying six or more stored decimals are tested.** Below that the test is vacuous — 0.3° × 60 = 18 exactly, so every 1-decimal value passes by arithmetic rather than by provenance. This was the error that invalidated the earlier run's first attempt.

---

## Part 2 — The population

All 407,157 EPSG:4326 records, classified at the **pair** level. 🟢

| Class | Records | Share |
|---|---|---|
| **A — DMS, arcminute grid** | **2,310** | 0.57% |
| **B — DMS, arcsecond grid** | **6,979** | 1.71% |
| C — decimal degrees | 327,773 | 80.50% |
| **D — undetermined (both axes short)** | **69,938** | **17.18%** |
| unparseable geometry | 157 | 0.04% |

**Applying the control correction.** MRDS alone accounts for 3,954 of the raw DMS hits — 22% of all arcminute and 50% of all arcsecond hits. Its DMS rate is **1.3%**, which is exactly the pair-level false-positive rate the control predicts. **MRDS's hits are false positives, and the control predicted them before the population was measured.** 🟢

**Genuine DMS-derived population: 5,288 records** across ten sources whose rates are 60–100× the false-positive floor. 🟢

**The undetermined bucket is 17.18% and stays undetermined.** Both axes are short, so nothing can be concluded either way. It includes the two largest coarse sources — `P9HTERGK` (42,744, entirely undetermined) and `nicrpge` (17,954, entirely undetermined). **This must not be read as "decimal degrees"**; it is the same mistake as the one this run exists to correct, pointing the other way.

### The limit of the pairing rule 🟡

Classification is at pair level: if one axis carries ≥6 decimals and is grid-exact, the other axis of that pair is taken to have come from the same reading at the same precision — which is the only way to say anything about a bare `45`. **That is an inference from one axis to the other, not a measurement of both.** It is reasonable and probably right, but every figure that depends on it is 🟡, not 🟢. It cannot be validated without the source files.

---

## Part 4 — Where it comes from

Rate against each source's own EPSG:4326 total, so the figure is a rate and not a volume. 🟢

| Source | Arcmin | Arcsec | DMS total | Source total | **DMS rate** |
|---|---|---|---|---|---|
| mrdata.usgs.gov/**vms** | 171 | 919 | 1,090 | 1,090 | **100.0%** |
| mrdata.usgs.gov/**carbonatite** | 1 | 59 | 60 | 60 | **100.0%** |
| mrdata.usgs.gov/**podchrome** | 16 | 1,008 | 1,024 | 1,045 | **98.0%** |
| mrdata.usgs.gov/**laterite** | 0 | 116 | 116 | 120 | **96.7%** |
| mrdata.usgs.gov/**sedznpb** | 23 | 466 | 489 | 506 | **96.6%** |
| mrdata.usgs.gov/**sedau** | 0 | 118 | 118 | 123 | **95.9%** |
| mrdata.usgs.gov/**porcu** | 331 | 294 | 625 | 690 | **90.6%** |
| mrdata.usgs.gov/**sedcu** | 302 | 313 | 615 | 708 | **86.9%** |
| mrdata.usgs.gov/**ree** | 466 | 5 | 471 | 578 | **81.5%** |
| mrdata.usgs.gov/major-deposits | 458 | 222 | 680 | 3,161 | 21.5% |
| *mrdata.usgs.gov/mrds (control)* | *498* | *3,456* | *3,954* | *304,610* | *1.3% — false-positive floor* |
| doi.org/P9HTERGK, nicrpge, Virginia, Alabama, Idaho | 0 | ≤1 | ~0 | 76,000+ | **0.0%** |

**Answers to the three questions the brief poses:**

1. **Is it concentrated? Yes, completely.** Ten USGS commodity-specific deposit databases — `vms`, `carbonatite`, `podchrome`, `laterite`, `sedznpb`, `sedau`, `porcu`, `sedcu`, `ree`, `major-deposits`. They are all `mrdata.usgs.gov` compilations of older published deposit inventories, which is exactly the kind of source that would have been recorded in degrees and minutes. 🟢
2. **Does any source ship both? Yes — `major-deposits` at 21.5%** is the clear mixed case, and `ree` (81.5%), `sedcu` (86.9%) and `porcu` (90.6%) carry a non-DMS minority. A source that ships both is weak evidence that the mixing happens in compilation rather than in our pipeline 🟡 — but note MRDS itself, from the same `mrdata.usgs.gov` host, is 100% decimal degrees, so **the split is per-database, not per-host**. That points at the upstream compilations rather than at our ETL. 🟡
3. **Do they cluster by extraction date or team tag?** Not tested this run. All the affected records carry the `__umn` team tag, but so does most of the graph, so that is not discriminating. 🔴

**Repository check not run** — no `ta2-minmod-*` checkout on this machine, and I have not cloned. The ingest-code grep for degree/minute parsing remains open.

---

## Part 3 — How wrong is the model, and in which direction

Assessed over the 5,288 genuine-DMS records, both axes each, = 10,576 axis assessments. Her table value is `70.25 km / 10^min(dp,5)`; the true value is `70.25 km × grid`, giving **±1.171 km** for an arcminute grid and **±19.5 m** for an arcsecond grid on her own scale. 🟡 *(pairing-rule dependent)*

> **A note on the two conventions.** The brief quotes ±0.9 km and ±15 m for arcminute and arcsecond. Those are *half the grid spacing along one axis* (1′ of latitude = 1.852 km, half = 0.926 km). Her ±70.3 km for a 1° grid is a *half-diagonal with a longitude cosine factor* — half the grid spacing would be 55.7 km. The two are different conventions. I have used **her** convention throughout so the comparison is like-for-like. **The ratios below are unaffected**, because a ratio of two errors on the same scale is a pure ratio of grid sizes. Which convention to adopt is a choice for her, not a finding.

### The result inverts the brief's expectation

The brief framed this as a model that **overstates** error. In the population it mostly **understates** it, and understatement is the dangerous direction.

| Direction | Axes | Breakdown |
|---|---|---|
| **UNDERSTATED — treated as more accurate than it is** | **9,801** | ≥100×: 2,760 · ≥10×: 6,448 · ≥2×: 253 · 1–2×: 340 |
| **OVERSTATED — treated as worse than it is** | **775** | ≥100×: 40 · ≥50×: 76 · ≥10×: 161 · ≥2×: 498 |
| About right (within 5%) | **0** | — |

**Why understatement dominates.** Most DMS values land on the *long* side of the conversion — `7.41666666666667` carries 14 decimals. Her cap treats anything ≥6 dp as 5 dp, giving ±0.70 m. The true precision is an arcminute, ±1,171 m. **She treats a 1.2 km-accurate point as sub-metre accurate.** 🟡

**Worst case in each direction** 🟢:

- **Understatement, 1,667×.** A 15-decimal value on an arcminute pair: her table (capped at 5 dp) says **±0.70 m**; the truth is **±1,171 m**.
  Example record: `POINT (116.58333333333 71)` — that is 116°35′ and 71°00′, both measured to the arcminute.
- **Overstatement, 3,600×.** A 0-decimal axis on an arcsecond pair: her table says **±70.2 km**; the truth is **±19.5 m**.
  Example records: `POINT (45 39.983333333333)`, `POINT (80 6.3666666666667)` — the bare `45` and `80` are 45°00′ and 80°00′, not rounded whole degrees.

**Both errors occur in the same record.** `POINT (116.58333333333 71)` is understated by 1,667× on its longitude and overstated by 60× on its latitude, simultaneously. Which one her model reports depends on which axis it reads — and I do not have her spreadsheet, so I cannot tell which she uses. **This is the single question to put to her.**

**Category change** — sites her model would rule out as too coarse to compare against the 10 km FuseMine blocking radius, which are in fact precise enough to use: **83 records.** 🟡 Smaller than the understatement problem by two orders of magnitude, and worth saying so plainly: *the data being wrongly discarded is a minor issue; the data being wrongly trusted is the real one.*

### Cross-check against her two figures

**Grain warning:** her counts are on merged sites; SPARQL serves the underlying raw records. These are not directly comparable and are given for shape, not for reconciliation.

| Her figure (merged) | DMS-derived (raw records) |
|---|---|
| 3,633 sites at 1 decimal place | **463** DMS records have an axis at ≤1 dp (8.8% of DMS) — her table calls these ±7 km or ±70 km; the truth is ±1.17 km or ±19.5 m |
| 93,673 with uneven precision between axes | **2,906** DMS records have differing decimal counts (55.0% of DMS) — with a gap distribution that is bimodal: 1,509 at gap 1–2 (trailing-zero loss) and 1,310 at gap 8–14 (**the DMS signature**) |

---

## Part 5 — The proposed replacement

One better input, not a rewrite.

```
precision_of(lat, lon):
    # test only axes carrying >= 6 stored decimals; below that the test is vacuous
    # order matters: coarsest grid first, because an arcminute value is also
    # arcsecond-exact and must not be credited with arcsecond precision
    if either axis is arcminute-exact  ->  +/- 1.17 km      (her scale; 0.93 km on the half-spacing convention)
    if either axis is arcsecond-exact  ->  +/- 19.5 m       (her scale; 15.4 m  on the half-spacing convention)
    otherwise                          ->  her existing decimal-place table, capped at 5 dp
```

**One correction to the brief's own pseudocode:** it tests arcseconds *first*. That is the wrong order — every arcminute value is also arcsecond-exact (60″ = 1′), so testing arcseconds first would credit every one of the 2,310 arcminute records with ±19.5 m when the truth is ±1.17 km, making the understatement problem worse rather than better. The brief's Part 1 instruction ("classify coarsest first") is the correct one. 🟢

**Grid-exactness test:** `abs(v * 60 - round(v * 60)) < 1e-8`, and likewise `× 3600`. Gate on `stored_decimals >= 6`.

**Expected effect** on the 5,288 genuine-DMS records: 9,801 axis assessments stop being over-optimistic, 775 stop being over-pessimistic, and 83 records become usable at the 10 km blocking radius. Everything else is untouched.

### What it does not solve 🟡

**The trailing-zero case is unrecoverable.** A source publishing `37.90000` is stored as `37.9`; the information is gone before we see it. But the *size* of that population can now be estimated, because the distribution has a distinctive shape. `P9HTERGK`, a clean 5-decimal source (42,744 records), shows an almost perfect ÷10 cascade:

| decimals | 5 | 4 | 3 | 2 | 1 |
|---|---|---|---|---|---|
| records | 38,335 | 3,973 | 386 | 37 | 13 |
| expected if trailing-zero loss | — | 3,834 | 383 | 38 | 4 |

**Observed and predicted agree to within a few records at every step.** 🟢 So for a source publishing at 5 decimals, about **11% of values render short purely from trailing-zero loss, but only ~0.12% render at ≤2 decimals** — the population that would actually be misjudged is small, on the order of 50 records for a source of this size.

**And the same shape distinguishes a genuinely coarse source.** `nicrpge` (17,954 records) has 16,110 at exactly 2 decimals and 1,604 at 1 — a **pile-up**, not a cascade. That is real coarseness at about 1.1 km, not a rendering artefact. 🟢 `MRDS` sits at 16 decimals for 100% of records, a pure float64 round-trip, with no trailing-zero loss visible at all.

**Practical diagnostic:** a ÷10 cascade across decimal counts means trailing-zero loss and the values are as precise as the source's headline; a pile-up at one decimal count means the source really is that coarse.

### The point that outlasts this run

Every number here is reconstruction after the fact, and reconstruction has a floor: the 17.18% undetermined bucket can never be resolved from stored values, and `37.90000` can never be recovered from `37.9`. **The real fix is recording precision at extraction time**, while the source string is still in hand and the two are still distinguishable. That is a schema field plus extractor work, and it is the only thing that removes the guesswork permanently.

---

## Method notes

- **7 queries, all read-only, all HTTP 200.** Nothing written to the graph; no repository cloned.
- **One query failed silently and is recorded:** `C1-control-mrds` returned HTTP 200 with zero rows because it referenced an outer-group variable inside a `UNION` branch, where it is out of scope. This is the **third** occurrence of the same trap across the four runs. It was caught only because a zero-row control is obviously wrong. Superseded by `C1-control-mrds-lon` / `-lat`. **Standing rule for the eventual script: never reference an outer-group variable inside a UNION branch.**
- Detector, tolerance derivation, and error model are in `probe-runs/2026-09-08/error_model.py` and the run's `.rq` files, all re-runnable.
