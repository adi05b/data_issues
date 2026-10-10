# Problem 3 — proper diagnosis

*Aditi Bombe · 7 September 2026 · run record in `probe-runs/2026-09-07/` · read-only*
*Confidence: 🟢 verified from a saved response · 🟡 likely · 🔴 assumed*

**Scope note: Part 1 ran in full. Part 2 (2.1–2.4) was not run** — including the reverse-engineering of Adriana's count and the repository reads. Both are flagged at the end.

---

## Headline

**The earlier write-up was too dismissive and it wrote off a real deliverable.** `SUMMARY.md` said decimal places are a floating-point artefact and left it there. That is half right, and the wrong half mattered:

- **A high decimal count proves nothing.** Verified. 🟢
- **A low decimal count is real evidence of coarseness.** Also verified — and this is the half that was written off. 🟢

**The source table is worth publishing, and it now exists** (§1.4). What cannot be built on decimal counts is the per-record precision figure Adriana actually wants for error propagation — that needs a field the schema does not have.

**One genuinely new finding:** a large share of MinMod's coordinates are **degrees-minutes conversions**, and decimal-place counting misreads them in *both* directions — the same measurement renders as `45` on one axis and `7.41666666666667` on the other. 🟢

---

## 1.5 — What decimal counts actually measure, verified

Both halves tested in code rather than asserted (`1.5-1.6-verify.py`).

**A low count is real evidence.** 400,000 random values carrying 3–6 genuine decimals were round-tripped through `float()` and `repr()`. **Zero** rendered with one decimal or fewer. 🟢 So a value stored as `37.9` really is 37.9 to float precision — it carries about a tenth of a degree, roughly 11 km. The only escape is a source that published trailing zeros (`37.90000` → `37.9`), and such a value **was already rounded at source**, so it is still coarse in information content. Either way the conclusion holds.

**A high count proves nothing.** `float("-109.48789")` returns `-109.48789`; the 16-digit forms in the graph (`-109.4878899999999931`) are float64 round-tripping of a 5-decimal source value. 🟢

**The asymmetry is the usable result:** *low decimal count → genuine quality signal. High decimal count → no information.* A source table built only on the low end is sound.

---

## 1.4 — Coarse coordinates by source, corrected

Restricted to records whose CRS resolves to **EPSG:4326** (407,157 records) — projected coordinates are stored as integers and would otherwise rank the graph's most precise source as its coarsest, which is what the original query did. Latitude and longitude reported **separately**. Sorted by **rate**, with absolute counts and each source's own EPSG:4326 total. 🟢

| Source | Coarse (worst axis) | Source total | **Rate** | lat 0dp | lat 1dp | lon 0dp | lon 1dp |
|---|---|---|---|---|---|---|---|
| mrdata.usgs.gov/**ree** | 131 | 578 | **22.66%** | 25 | 106 | 26 | 100 |
| mrdata.usgs.gov/**phosphate** | 246 | 1,187 | **20.72%** | 48 | 198 | 59 | 164 |
| **api.cdr.land**/v1/docs/documents | 137 | 679 | **20.18%** | 42 | 89 | 51 | 86 |
| mrdata.usgs.gov/**sedcu** | 110 | 708 | **15.54%** | 23 | 78 | 39 | 71 |
| mrdata.usgs.gov/**major-deposits** | 475 | 3,161 | **15.03%** | 101 | 374 | 117 | 352 |
| mrdata.usgs.gov/sedexmvt | 32 | 240 | 13.33% | 6 | 26 | 2 | 27 |
| mrdata.usgs.gov/**nicrpge** | **2,381** | 17,954 | 13.26% | 239 | 1,604 | 475 | 1,906 |
| mrdata.usgs.gov/porcu | 67 | 690 | 9.71% | 7 | 60 | 8 | 58 |
| mrdata.usgs.gov/ofr20151121 | 34 | 446 | 7.62% | 2 | 27 | 2 | 32 |
| mrdata.usgs.gov/potash | 34 | 981 | 3.47% | 2 | 29 | 3 | 31 |
| mrdata.usgs.gov/asbestos | 21 | 913 | 2.30% | 1 | 20 | 1 | 13 |
| mrdata.usgs.gov/pp1802 | 6 | 410 | 1.46% | 0 | 0 | 1 | 5 |
| mrdata.usgs.gov/sedznpb | 4 | 506 | 0.79% | 0 | 4 | 1 | 0 |
| mrdata.usgs.gov/podchrome | 7 | 1,045 | 0.67% | 3 | 4 | 0 | 2 |
| mrdata.usgs.gov/sir20105090z | 6 | 1,200 | 0.50% | 0 | 6 | 0 | 3 |
| mrdata.usgs.gov/deposit | 1 | 428 | 0.23% | 0 | 0 | 0 | 1 |
| doi.org/10.5066/P9K1HBNT | 1 | 684 | 0.15% | 0 | 0 | 0 | 1 |
| doi.org/10.5066/**P9HTERGK** | 13 | **42,744** | **0.03%** | 0 | 13 | 0 | 7 |
| **All EPSG:4326** | | **407,157** | | **499** | **2,638** | **785** | **2,859** |

Graph-wide: **latitude ≤1 dp on 3,137 records (0.77%)**, **longitude ≤1 dp on 3,644 (0.90%)**. Longitude is consistently the coarser axis, which is worth a line to Adriana on its own.

**Reading the table two ways, because they disagree:**

- **By volume**, `nicrpge` dominates — 2,381 of roughly 3,600 coarse records.
- **By rate**, `ree` (22.7%), `phosphate` (20.7%) and `api.cdr.land` (20.2%) are the worst contributors; `nicrpge` is only seventh.
- **P9HTERGK is the counter-example worth naming**: 42,744 records at a 0.03% coarse rate. It is possible to ship at scale without this problem.
- **MRDS does not appear at all.** The graph's largest source (304,622 records with coordinates) has **zero** coarse coordinates.

*Rate is against each source's own EPSG:4326 record count, so a small source shipping mostly coarse data is not hidden behind a large clean one — which was the specific failure of the original table.*

---

## 1.6 — Uneven precision, split by gap size

`gap = |lat_decimals − lon_decimals|`, EPSG:4326 only. **22,946 records** have a non-zero gap. 🟢

| Gap | Records | | Gap | Records |
|---|---|---|---|---|
| 1 | 16,820 | | 8 | 101 |
| 2 | 2,280 | | 9 | 245 |
| 3 | 625 | | 10 | 296 |
| 4 | 1,434 | | 11 | 443 |
| 5 | 254 | | 12 | 271 |
| 6 | 66 | | 13 | 77 |
| 7 | 32 | | 14 | 2 |

| Band | Records | Share | Earlier reading | What it actually is |
|---|---|---|---|---|
| **gap 1–2** | **19,100** | **83.2%** | artefact | **Confirmed artefact** — a lost trailing zero (`-109.48780` → `-109.4878`) 🟢 |
| **gap ≥3** | **3,846** | **16.8%** | artefact | **Not an artefact — but not "two different sources" either** 🟢 |

**The earlier blanket dismissal of the whole set was wrong**, and so was the brief's proposed reading of the ≥3 band. Pulling the largest-gap records individually shows a third mechanism:

```
POINT (-80 -4.33333333333333)          lon = 80°00'   lat = 4°20'
POINT (7.41666666666667 45)            lon = 7°25'    lat = 45°00'
POINT (-121 50.5666666666667)          lon = 121°00'  lat = 50°34'
POINT (28.6111111111111 -13)           lon = 28°37'   lat = 13°00'
POINT (-78.6 -3.78333333333333)        lon = 78°36'   lat = 3°47'
```

**These are degrees-minutes values converted to decimal degrees.** One axis had zero minutes and renders as a bare integer; the other produced a repeating decimal and renders at 13–14 digits. **Both axes carry identical precision — arcminutes, about 1.8 km.** The 14-decimal-place difference is entirely a rendering effect. 🟢

Tested rather than asserted: of the 12 largest-gap records, **every one of the 12 long-decimal values (100%) lands exactly on a whole arcminute or arcsecond.** 🟢

**Important limit on that claim, stated because the obvious version of the test is broken:** an arcminute test is *vacuous* on short decimals — any 1-decimal value trivially satisfies n/60 (0.3° = 18′). Restricting the test to values carrying **six or more stored decimals**, where it actually discriminates:

| Band | Long values tested | Exact arcmin/arcsec |
|---|---|---|
| gap ≥12 | 12 | **12 (100%)** |
| gap 3–11 | 288 | 134 (**47%**) |
| coarse (lat ≤1 dp) | 96 | 91 (**95%**) |

So: **DMS conversion fully explains the extreme tail, and about half of the 3–11 band.** 🟢 The remainder of that band has some other cause and is not characterised. 🔴 The brief's hypothesis — that a large gap means one axis was filled from a fallback such as a state centroid — is **not supported by anything seen here**, though it is not excluded for the unexplained half.

**A caveat this places on §1.4** 🟡: among coarse records, 95% of the *partner* axis's long values are arcminute-exact, so a meaningful share of "coarse" records are DMS-derived. That does not change what the stored value carries — `78.6` is still 0.1° of information — but it shifts the *blame*: the coarseness may have entered during a degrees-minutes conversion rather than at source. That distinction decides whether the fix is upstream or in our own ETL, and it is exactly what the repository read (not run) would settle.

---

## What Adriana asked for, and what she can have

| She asked for | Status |
|---|---|
| A list of sources shipping coarse coordinates | **Delivered** — §1.4, CRS-corrected, rate-ranked, both axes 🟢 |
| A per-record precision figure for error propagation | **Not possible from stored data.** No precision field exists anywhere in the schema, and decimal counts are unusable in the high direction and confounded by DMS in the low direction. Requires a schema change plus extractor work. 🟢 |

**What to tell her:** the source table is real and usable — treat `≤1 dp` as a reliable *floor* on coarseness (those records genuinely carry ~11 km or worse), but do not read the absence of that flag as evidence of precision, because a 14-digit value can be a 1.8 km arcminute reading. For error propagation, the honest per-record bound available today is **arcminute-or-worse for any DMS-derived record**, which is a different and much larger population than the ≤1 dp list.

---

## Still blocked

**Part 2 was not run.** Specifically outstanding:

- **Reverse-engineering Adriana's 3,633** (2.1) — not attempted this run. Still unexplained that a latitude-only raw count (2,853) comes back *below* her deduplicated figure, which is impossible at the same grain.
- **Is the deduplicated coordinate elected or recomputed?** (2.4.1) — still the highest-leverage unknown. If merging *averages* coordinates, every precision figure at deduplicated grain describes the merge rather than any source, and both of Problem 3's impossible ratios dissolve at once. **This should be read before anything is sent to Adriana.**
- **Do the source files carry coarse coordinates, or did our ETL round them?** (2.4.2) — the DMS finding above sharpens this considerably: the question is now specifically whether the degrees-minutes conversion happens upstream or in our pipeline.
- **Do any SHACL shapes bound latitude?** (2.4.3).

All four need a `ta2-minmod-*` checkout, which is not on this machine. I have not cloned.
