# NAD27_IMPACT.md — what else does the coordinate fix touch?

*Aditi Bombe · run 2026-09-14 · follow-up to `PROBLEM1_SOURCE_TRACE.md` · **read-only**, 5 queries, nothing written.*
*Record in `probe-runs/2026-09-14/`. Confidence: 🟢 verified · 🟡 likely · 🔴 assumed.*

**Endpoint reachable** — certificate renewed, `ASK { ?s ?p ?o }` → `true`. The previous run's blocker is cleared.

---

## 1 — Who ships NAD27

**One source. Not forty.** 🟢 `n1-nad27-sources`, `n1c-4267-anysource`

| Source id | Team tag | NAD27 records | Records with a location | Total sites | Rate |
|---|---|---|---|---|---|
| `https://doi.org/10.5066/P96MMRFD` — **Alaska Resource Data File (ARDF)** | `umn` | **7,720** | 7,720 | 14,099 | **100% of its located records** |

Every EPSG:4267 node in the graph belongs to this one feed — 7,720 of 7,720, confirmed without a source filter. **No other source ships NAD27 at all.** 🟢 `observed_name` is populated and reads `EPSG:4267`, so the datum was declared by the source and read correctly, exactly as for the two projected feeds in Problem 1. 🟢

**The single most important fact for this run: it is Alaska.** That was not visible before the query ran, and it changes what counts as a correct answer — the brief's expected envelope (10 m east, 100 m west) is a *continental US* figure, and Alaska's NAD27→NAD83 shift is larger and differently shaped.

Note also that 6,379 of the feed's 14,099 sites carry no location at all; the rate above is against located records, which is the honest denominator.

---

## 2 — What the fix does to them

**All 7,720 records tested, not a sample** — the whole population is small enough to convert exhaustively, which is better than the 40 the brief asked for. Each stored WKT string was passed to `shapely.wkt.loads` **exactly as the graph returned it** — not rounded, reformatted, or rebuilt from parsed numbers. Transformers constructed as in `geo.py`. 🟢 `nad27_real.py` → `n3-nad27-bothways.csv`

### The headline measurement

> **The current code returns the input unchanged on 7,720 of 7,720 records — 100.00%.** 🟢

Not approximately unchanged: bit-identical, on every single record. The silent no-op is confirmed on real data, not inferred from a synthetic one.

### Shift distribution (metres)

| | |
|---|---|
| min | **0.0** |
| p5 | 104.4 |
| p25 | 119.6 |
| **median** | **129.2** |
| p75 | 141.7 |
| p95 | 156.2 |
| max | **273.0** |
| non-finite results after the fix | **0** |
| fixed outputs outside a generous Alaska box | **0** |

### The trend, by longitude band

| Band (input longitude) | n | min | median | max |
|---|---|---|---|---|
| W of −170 | 30 | 0.0 | **0.0** | 201.8 |
| −170 … −160 | 1,159 | 0.0 | **155.4** | 188.6 |
| −160 … −150 | 2,127 | 126.1 | **138.7** | 156.7 |
| −150 … −140 | 2,946 | 110.9 | **125.1** | 135.7 |
| E of −140 (SE Alaska) | 1,453 | 99.5 | **107.4** | 116.5 |
| *positive longitude (Aleutians across 180°)* | 5 | 263.5 | **264.1** | 273.0 |

**The shift grows monotonically westward** — 107 m in southeast Alaska to 155 m at −170 — which is the direction the brief predicted. The *magnitude* is roughly 100–190 m rather than 10–100 m, because this is Alaska rather than the lower 48. The direction is what validates the test; the magnitude is a property of the region, and it is larger than the framing assumed.

### Named real records 🟢

| | Record | Stored (NAD27) | Current output | Fixed output | Shift |
|---|---|---|---|---|---|
| **Median** | `HE015` Lignite Creek; Hoseanna Creek | `POINT (-148.9 63.91)` | `(-148.9000000, 63.9100000)` | `(-148.9024074, 63.9095164)` | **129.2 m** |
| **Largest** | `AT001` Unknown (east of Abraham Bay) | `POINT (172.82 52.85)` | `(172.8200000, 52.8500000)` | `(172.8169921, 52.8483413)` | **273.0 m** |
| **Smallest** | `GI001` Unnamed (on Gareloi Island) | `POINT (-178.77 51.76)` | `(-178.7700000, 51.7600000)` | `(-178.7700000, 51.7600000)` | **0.0 m** |

In every case the *current* output is character-for-character the stored input.

### One limitation the fix does not remove 🟢

**24 records shift by ~0 m even after the fix.** All lie between −178.77 and −168.91 — St. Lawrence Island (`SL001`–`SL0nn`) and Gareloi Island (`GI001`). These sit outside the Alaska NADCON grid's coverage, so there is no transformation to apply and pyproj returns the input either way. The fix repairs 7,696 records and leaves these 24 exactly where they are. They are not made worse, but they are not corrected, and they should not be counted as repaired. 🟡 *(grid-coverage attribution is the natural reading; not separately verified)*

The 5 Aleutian records with **positive** longitude transform correctly and land inside Alaska — the 180° meridian is not a problem.

---

## 3 — Which of the three outcomes

**Outcome 1: the records are missing their datum correction, and the fix repairs them.** 🟢

Shifts of roughly 100–270 m, trending larger westward, no erratic values, no non-finite results, and not one output outside Alaska. The third outcome — the one this run existed to catch — **did not occur**, and I looked for it specifically: the Alaska bounding-box check and the non-finite check were written to fail loudly and both came back clean.

**Where the framing was wrong, and the real records win:** the brief predicted 10–100 m; the truth is 100–273 m with a median of 129 m. The synthetic Colorado coordinate (≈49 m) understated the real effect by roughly 2.6×, because Colorado is not Alaska. The *mechanism* the synthetic test predicted is exactly right — the no-op is 100% confirmed — but its magnitude did not transfer, and nothing in this section rests on it.

---

## 4 — What this means for the recommendation

**The fix touches 38,828 records and repairs a second defect nobody reported.** Adding `always_xy=True` corrects the 31,108 swapped records in Problem 1 and, as a side effect, applies the missing NAD27→WGS84 datum shift to **7,696** of the 7,720 Alaska Resource Data File records — which are currently sitting a median of 129 m from where they belong, with a quarter of them beyond 142 m. That is safe to recommend: the change moves these records in a single, well-understood direction, every result stays inside Alaska, and nothing becomes non-finite. It is worth saying plainly in the proposal that this is a *second* correction rather than a side effect to be tolerated, because 7,696 records silently misplaced by over 100 m is a finding in its own right — and because the 129 m median is small enough to be invisible on a map but large enough to matter to the 10 km blocking radius only in aggregate, so nobody was ever going to notice it by looking. Two caveats belong in the same sentence: **24 records near St. Lawrence and Gareloi Islands lie outside the NADCON grid and will not be corrected by this or any `always_xy` change**, and the ARDF feed's other 6,379 sites carry no coordinates at all, so the fix reaches barely more than half of it.

### Section 5 — the corroboration check 🟢

**Zero overlap.** Joined by record id, not by eyeball: none of the 7,720 NAD27 records appears among the 24,818 rows of `coord_out_of_range.xlsx`, whose `source_crs` column contains only `EPSG:2994`, `EPSG:26912` and one `EPSG:4326`.

That is the independent confirmation the brief wanted: a swapped NAD27 coordinate would put an Alaskan longitude (−178 … −130) into the latitude slot and produce an impossible latitude, which is precisely what her export selects for. Not one of the 7,720 is in it. **NAD27 records are not being swapped** — consistent with §2, where the current code is shown to leave them untouched rather than transposing them.

---

## Run record — `probe-runs/2026-09-14/`

| File | What |
|---|---|
| `n1-nad27-sources` | §1 — every source shipping EPSG:4267 |
| `n1b-p96-totals` / `n1c-4267-anysource` / `n1d-p96-sitecount` | §1 — rate denominators, and confirmation no other source ships NAD27 |
| `n2-nad27-coords-all` | §2 — all 7,720 records with verbatim WKT, `observed_name` included |
| `n3-nad27-bothways.csv` | §3 — both conversions and the measured shift, per record |
| `nad27_real.py` | the conversion, run on the stored strings unmodified |

All queries HTTP 200, `truncated_by_limit: false`. Nothing written to the graph; no `ta2-minmod-*` checkout touched. Every claim about `geo.py`'s contents remains 🔴 until someone opens it.
