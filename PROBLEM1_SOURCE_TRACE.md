# PROBLEM1_SOURCE_TRACE.md — where does the swap come from?

*Aditi Bombe · run 2026-09-13 · Problem 1 only · **read-only**, nothing written to the graph, no `ta2-minmod-*` checkout touched.*
*Record in `probe-runs/2026-09-13/`. Confidence: 🟢 verified from a saved artifact · 🟡 likely · 🔴 assumed.*

---

## Bottom line

**The source files are fine. The fault is in what MinMod does between them — for 24,817 of 24,818 records.** 🟢

Both projected source feeds declare their own coordinate system, MinMod reads that declaration correctly, and MinMod's reprojection arithmetic is correct to **5 × 10⁻⁸ degrees (≈ 5 mm)**. It then writes the correct answer into the wrong two columns. `stored_lat` holds the longitude and `stored_lon` holds the latitude. A plain column swap fixes **24,818 of 24,818** merged rows — 100.0%. 🟢

**The one exception is the Myanmar record, and it inverts the story.** `Tagaung Taung` is the only row where the merged table is a *faithful copy* of the graph (residual 0.0000) — because there is no reprojection step for a record already in EPSG:4326. Its swap is already present in the raw graph, and its `:crs` carries **no `observed_name`** — meaning EPSG:4326 was *assumed* by the extractor, not read from a source file. So the claim that this record is swapped upstream of MinMod's mapping is **supported**, and it is a different bug in a different place. 🟢

Two bugs, 24,817 : 1, different owners. Do not fix them with the same patch.

**Operational blocker, unrelated to the data:** the MinMod TLS certificate **expired 2026-09-12 23:59:59 UTC**, ~19 h before this run. Every live query in this run failed with `curl (60)`. Sections 1, 2, 4 and 5 were therefore re-derived from saved snapshots of earlier runs plus Adriana's export; three sub-questions could not be answered at all and are listed under **Still blocked**. Someone at ISI needs to renew that cert. 🟢

---

## The lookup table

| Source id | Team tag | Records (merged / raw) | Coordinate system | Likely repo path 🔴 | Sample record ids |
|---|---|---|---|---|---|
| `http://www.oregongeology.org` | `umn` | **17,073** / 23,316 | **EPSG:2994** — NAD83(HARN) Oregon GIC Lambert (**feet**), `observed_name` present and matching, 100% of the feed | `ta2-minmod-data/data/mineral-sites/umn/www-oregongeology-org/` | `id-02066` (Little Baby prospect), `id-03139` (Bi Metallic), `id-03057` (Gardner-Murphy prospect), `id-08602` (Irwin molybdenum prospect), `id-19879` (Blue Bell) |
| `https://doi.org/10.34191/OFR-757` | `umn` | **7,744** / 7,792 | **EPSG:26912** — UTM zone 12N (metres), `observed_name` present and matching, 99.99% of the feed | `ta2-minmod-data/data/mineral-sites/umn/doi-org-10-34191-ofr-757/` | `0` (Harts Draw Deposits), `1002` (V8), `1003` (View), `1004` (Yellow Tree Mine), `1005` (Baker Pit) |
| `https://doi.org/10.5382/econgeo.4950` | `usc` | **1** / 1 | **EPSG:4326** — but `observed_name` **absent**: assumed, not declared. 0.16% of the feed (1 of 628) | `ta2-minmod-data/data/mineral-sites/usc/doi-org-10-5382-econgeo-4950/` | `tagaung-taung` (Tagaung Taung) |

Counts are **merged** (Adriana's `coord_out_of_range.xlsx`, 24,818 rows) / **raw** (SPARQL site grain, 31,109 records, from `probe-runs/2026-09-02/1b.csv`). Repo paths are 🔴 — the folder convention is inferred from the team tag in the site URI and has not been checked against a checkout.

---

## 1 — Where the data comes from

**Three sources. No tail. Nothing trimmed.** 🟢

The §1 census query could not be run live (expired cert). The equivalent census was instead derived at **merged grain** from all 24,818 rows of Adriana's export — which is a complete enumeration, not a sample, so the "is there a third source?" question is answered exhaustively:

| `:source_id` (exact string) | `source_crs` | Merged records | Team tag |
|---|---|---|---|
| `http://www.oregongeology.org` | `EPSG:2994` | 17,073 | `umn` |
| `https://doi.org/10.34191/OFR-757` | `EPSG:26912` | 7,744 | `umn` |
| `https://doi.org/10.5382/econgeo.4950` | `EPSG:4326` | 1 | `usc` |
| | | **24,818** | |

There is **no fourth source, and no unexpected single-record source**. Every row's `source_crs` is a single value per source — the (source, crs, tag) cross-tab has exactly three cells. 🟢 `probe-runs/2026-09-13/profile_xlsx.py`

**Team tags, from splitting the site URI** (`site__<source slug>__<record id>__<team>`) across all 24,818 refids: 🟢

| Team tag | Records |
|---|---|
| `umn` | 24,817 |
| `usc` | 1 |

**Raw grain cross-check** (`probe-runs/2026-09-02/1b.csv`, captured when the endpoint was reachable): 23,316 EPSG:2994 + 7,792 EPSG:26912 + 1 EPSG:4326 = **31,109**, with **no null-CRS bucket at all**. The same three sources, the same three coordinate systems. 🟢

**Dedup compresses unevenly**, which is worth knowing before anyone reconciles the two numbers:

| Source | Raw out-of-range | Merged | Survives dedup |
|---|---|---|---|
| oregongeology.org | 23,316 | 17,073 | 73.2% |
| OFR-757 | 7,792 | 7,744 | 99.4% |
| econgeo.4950 | 1 | 1 | 100% |

---

## 2 — Source or mapping

### Half one: the raw record declares its own coordinate system, and MinMod read it correctly

From `probe-runs/2026-09-03/A2.3-crs-census.csv` — a graph-wide census of `:crs` `observed_name` against `normalized_uri` label: 🟢

| Normalized label | `observed_name` | LocationInfo nodes |
|---|---|---|
| EPSG:4326 | `EPSG:4326` | 403,549 |
| **EPSG:2994** | **`EPSG:2994`** | **23,316** |
| EPSG:4326 | *(absent)* | 7,869 |
| **EPSG:26912** | **`EPSG:26912`** | **7,792** |
| EPSG:4267 | `EPSG:4267` | 7,720 |
| *(no crs node)* | — | 1,280 |
| EPSG:4326 | `WGS84` | 1 |

For **both projected feeds, `observed_name` is populated and identical to the normalized label**, on every single node — 23,316/23,316 and 7,792/7,792. The source declared `EPSG:2994` / `EPSG:26912` as a literal string, and MinMod normalized it to itself. **The source files are not wrong about their coordinate system, and MinMod did not mis-read it.** 🟢

The Tagaung record falls in the **7,869-node `observed_name`-absent bucket**: EPSG:4326 was defaulted in, not read from anything. 🟢 Its sibling MRDS records for the same place *do* carry `observed_name = EPSG:4326`, and its WKT is serialised `POINT(23.63453 96.16317)` — no space after `POINT` — where every `umn` record uses `POINT (x y)`. Different serialiser, different code path. 🟢 `probe-runs/2026-09-02/1a-alt-tagaung.csv`

### Half two: the merged entity, side by side with the raw record

107 records were matched across both halves — well past the ten asked for. Raw `(easting, northing)` came from saved SPARQL snapshots; each was reprojected from its **declared** CRS to EPSG:4326 with `pyproj` 3.8.0 and compared against what the spreadsheet stores.

`d_as-written` = error if `stored_lat`/`stored_lon` mean what they are named. `d_swapped` = error if `stored_lat` actually holds longitude and `stored_lon` actually holds latitude.

| Name | Source | Declared CRS | Raw easting | Raw northing | Reprojected lon | Reprojected lat | `stored_lat` | `stored_lon` | d_as-written | d_swapped |
|---|---|---|---|---|---|---|---|---|---|---|
| Harts Draw Deposits | OFR-757 | EPSG:26912 | 632887.00 | 4199554.00 | −109.487835 | 37.933852 | **−109.487835** | **37.933852** | 147.42° | **1.5e−08** |
| Dolly Clark Mine | OFR-757 | EPSG:26912 | 262300.00 | 4650700.00 | −113.868797 | 41.972460 | −113.868797 | 41.972460 | 155.84° | 2.0e−08 |
| Peg Leg Mine | OFR-757 | EPSG:26912 | 261136.00 | 4652406.00 | −113.883521 | 41.987454 | −113.883521 | 41.987454 | 155.87° | 3.7e−09 |
| Vipont Mine | OFR-757 | EPSG:26912 | 264145.00 | 4649860.00 | −113.846220 | 41.965458 | −113.846220 | 41.965458 | 155.81° | 4.2e−08 |
| Jennie Mine | OFR-757 | EPSG:26912 | 231935.00 | 4198955.00 | −114.048678 | 37.898665 | −114.048678 | 37.898665 | 151.95° | 5.0e−08 |
| Goose Creek Lignite | OFR-757 | EPSG:26912 | 248493.00 | 4651383.00 | −114.035506 | 41.974320 | −114.035506 | 41.974320 | 156.01° | 4.1e−08 |
| Stateline | OFR-757 | EPSG:26912 | 670940.00 | 4219350.00 | −109.050302 | 38.105808 | −109.050302 | 38.105808 | 147.16° | 4.6e−08 |
| Bald Mountain | oregongeology | EPSG:2994 | 1991849.91 | 1039338.01 | −117.891533 | 44.571772 | −117.891533 | 44.571772 | 162.46° | 3.4e−08 |
| Cape Blanco | oregongeology | EPSG:2994 | 230268.76 | 414306.10 | −124.533924 | 42.813521 | −124.533924 | 42.813521 | 167.35° | 1.5e−08 |
| City of Astoria | oregongeology | EPSG:2994 | 484751.36 | 1637959.86 | −123.767782 | 46.197941 | −123.767782 | 46.197941 | 169.97° | 2.9e−08 |
| Little Baby prospect | oregongeology | EPSG:2994 | 2086265.32 | 1172007.21 | −117.510862 | 44.926693 | −117.510862 | 44.926693 | 162.44° | 1.5e−08 |
| Sand Island Placer | oregongeology | EPSG:2994 | 421944.17 | 1668631.78 | −124.020678 | 46.274828 | −124.020678 | 46.274828 | 170.30° | 4.2e−08 |
| **Tagaung Taung** | **econgeo.4950** | **EPSG:4326** | *(23.63453)* | *(96.16317)* | *23.634530* | *96.163170* | **96.163170** | **23.634530** | **0.0000** | **72.5°** |

Full 107-row table: `probe-runs/2026-09-13/decisive_table.csv`.

**Totals across all 107 matched records:** 🟢

- Swapped reading beats as-written reading: **106 / 107**
- Swapped reading agrees to **< 1e−4°** (≈ 11 m): **106 / 107**
- Worst residual under the swapped reading, per source: oregongeology **4.9e−08°**, OFR-757 **5.0e−08°**
- The single exception is Tagaung Taung, where the *as-written* reading is exact (0.0000) and the swapped reading is wrong by 72.5°.

**Independent corroboration from the column ranges alone**, across all 24,818 merged rows — no reprojection needed: 🟢

| Source | `stored_lat` range | `stored_lon` range |
|---|---|---|
| OFR-757 (Utah) | −114.050 … −109.044 | 36.999 … 41.991 |
| oregongeology (Oregon) | −124.534 … −116.533 | 41.996 … 46.275 |

Utah spans lon −114.05…−109.04 and lat 37.0…42.0. Oregon spans lon −124.57…−116.46 and lat 41.99…46.29. **The `stored_lat` column is exactly the state's longitude range and the `stored_lon` column is exactly its latitude range**, to the third decimal, for both states independently. The reprojection lands in precisely the right place; only the labels are crossed.

### The conclusion

**For the 24,817 projected records, the source files are correct and the fault is in MinMod's mapping.** 🟢 This is stated as a finding, not a suggestion. The evidence is threefold and each strand is independently sufficient:

1. The source declares its CRS explicitly and MinMod normalizes it correctly (`observed_name` = normalized label on 31,108/31,108 nodes).
2. MinMod's reprojection arithmetic is correct to ~5 mm — it is not a datum error, a unit error, or a bad CRS.
3. The output pair is assigned to the wrong two fields, uniformly, on 100% of rows.

A correct transform whose result is written to transposed fields is a mapping defect, by definition. Nothing in the source file can cause it.

**The exact defect is reproducible in two lines.** `probe-runs/2026-09-13/axis_order.py` shows that EPSG:4326's *declared* axis order is `[Lat, Lon]`, and that exactly two `pyproj` call shapes produce the observed output: 🟢

```python
# Both of these reproduce stored_lat = -109.4878352, stored_lon = 37.93385228
lat, lon = Transformer.from_crs(src, "EPSG:4326", always_xy=True).transform(e, n)   # (A)
lon, lat = Transformer.from_crs(src, "EPSG:4326").transform(e, n)                   # (B)
```

(A) sets `always_xy=True`, so the transformer returns `(x, y)` = `(lon, lat)`, then unpacks it as `lat, lon`.
(B) omits `always_xy`, so the transformer honours EPSG:4326's official `Lat, Lon` order and returns `(lat, lon)`, then unpacks it as `lon, lat`.

Either way it is a **one-line fix at a single call site**, and the fix is to make the `always_xy` flag and the unpacking order agree. That call site is what to find on GitHub. 🟢

**For the 1 EPSG:4326 record, the opposite holds.** The merged table copies the graph exactly; the graph itself holds `POINT(23.63453 96.16317)`, i.e. lon 23.6 / lat 96.2, which is impossible. Five sibling records for the same place sit at lon ≈ 96.1, lat ≈ 23.5 🟢. The swap predates the merge step. Whether it originates in the source file or in the `usc` extractor **cannot be settled without the repo** — the missing `observed_name` and the distinct WKT serialiser point at the extractor 🟡, but that is not proof. 🔴

---

## 3 — Does either source also publish good records?

**Both projected feeds are 100% single-CRS. The conversion is triggered per source, not per record.** 🟢

| Source | Sites in feed | Out-of-range | Share | Reading |
|---|---|---|---|---|
| oregongeology.org | 23,316 | 23,316 | **100.00%** | homogeneous — entire feed is EPSG:2994 |
| OFR-757 | 7,793 | 7,792 | **99.99%** | homogeneous — the 1 remainder has `:location_info` but **no `:location`** at all, so it is not a counter-example |
| econgeo.4950 | 628 | 1 | **0.16%** | mixed — 627 records in this feed are fine |

Feed totals from `probe-runs/2026-09-02/P0.8-source-census.csv`; out-of-range counts from `probe-runs/2026-09-02/1b.csv`; the OFR-757 remainder (`record_id 4563`, "A&G") is documented in `PROBE_REPORT.md`. 🟢

This splits the search cleanly, and the two halves are **different code paths**:

- **The 24,817:** a per-source branch. Something keys off the source or its declared CRS and runs a reprojection for the whole feed. Look for the code that decides *"this feed is projected, convert it"* — the bug is in that branch's output handling, and it will be one function.
- **The 1:** a per-record anomaly inside a feed that is otherwise 99.84% clean. Not a feed-level rule. Look at the single record, not at a branch.

---

## 4 — What links a record to its document

The §6 predicate census could not be run live. From the graph-wide MineralSite predicate census (`probe-runs/2026-09-02/P0.1-mineralsite.csv`), the provenance predicates and their coverage across all 679,781 sites: 🟢

| Predicate | Triples | Sites | Coverage |
|---|---|---|---|
| **`:reference`** | 679,781 | 679,781 | **100%** |
| `:record_id` | 679,781 | 679,781 | **100%** |
| `:source_id` | 679,781 | 679,781 | **100%** |
| `:created_by` | 679,781 | 679,781 | 100% |
| `:modified_at` | 679,781 | 679,781 | 100% |

**`:reference` is the document link, and it is mandatory** — every site in the graph has one. 🟢 It is the shortest route from a bad record to the file it came from.

**What is on the other end of it has not been checked.** 🔴 The one-hop expansion is a live query and the endpoint was down. This is the single highest-value query to run the moment the cert is renewed, because it is what converts a `record_id` into a document identifier without guessing at folder conventions.

---

## Which files to open on GitHub, in priority order

Each entry is the one question that file answers. Nothing below has been read — **every claim about file contents is 🔴 until someone opens it.**

### 1. `ta2-minmod-kg` — the reprojection call site · **fixes 24,817 records**

**Question: where is `Transformer.from_crs(..., "EPSG:4326")` called, and does its `always_xy` flag agree with how the result is unpacked?**

Grep, in this order:

```
always_xy
Transformer.from_crs
pyproj
EPSG:4326
26912|2994
```

Look for an assignment of the form `lat, lon = ...transform(...)` or `lon, lat = ...transform(...)`. One of the two shapes in §2 will be sitting there. This is the whole bug for 99.996% of the population, and the diff is one line.

### 2. Whatever writes `stored_lat` / `stored_lon` into Postgres · **confirms the blast radius**

**Question: is the transpose at the reprojection call, or at the INSERT?**

`coord_out_of_range.xlsx` is a Postgres export with columns named `stored_lat` / `stored_lon`. Those names come from a schema and something populates them. If the reprojection returns correctly-ordered values and the INSERT binds them crossed, the fix belongs here instead — same one-line character, different file. Grep `stored_lat`. Settling this decides whether the fix is one site or two.

### 3. `ta2-minmod-data/data/mineral-sites/usc/doi-org-10-5382-econgeo-4950/` · **the Myanmar record, 1 record**

**Question: does the source file for `tagaung-taung` already hold the coordinates swapped, or did the `usc` extractor swap them?**

This is the claim that has never been checked, and §2 narrows it to a binary. Open the record whose id is `tagaung-taung` and read its coordinate fields. If the file holds lon 23.6 / lat 96.2, the source is wrong and MinMod faithfully carried it through. If the file holds lon 96.2 / lat 23.6, the `usc` extractor transposed it. The missing `:crs` `observed_name` says the file declares **no** coordinate system 🟡 — confirm that too, since it explains why EPSG:4326 was assumed.

### 4. The `usc` extractor for `econgeo` DOIs · **only if #3 says the file is clean**

**Question: does this extractor write `POINT(lon lat)` or `POINT(lat lon)`, and why does it emit `POINT(` with no space when every `umn` record emits `POINT (`?**

The serialisation difference is a fingerprint of a separate code path. If #3 exonerates the source file, this path is the culprit, and the same question applies to every other record it has ever written — which is the part that matters more than the one record.

### 5. SHACL shapes, wherever they live · **prevents the recurrence**

**Question: does any shape bound latitude to [−90, 90], and is it conditional on the CRS being geographic?**

Still unverified from the earlier run 🔴. An **unconditional** bound would reject two valid source feeds — 31,108 correctly-stored projected records — so if one is being added, it must be conditional. Note that a CRS-aware bound would **not** have caught this bug: the merged records are nominally EPSG:4326, so a conditional rule fires on them correctly. The right guard here is a post-reprojection range assertion, which is a third thing to propose.

---

## Still blocked

The expired certificate stopped three sub-questions that were in scope for this run. All three are single queries; the `.rq` for the first is already written and saved.

| Question | Why it matters | Where |
|---|---|---|
| `:crs` `observed_name` **per out-of-range record**, not per graph-wide census | The census answers it at 99.99% confidence for both feeds; a per-record pull would close the last gap and catch any single dissenting row | `probe-runs/2026-09-13/p1.1-source-census.rq` |
| **One hop past `:reference`** — what is on the other end | The shortest route from `record_id` to the actual document; would replace the 🔴 repo paths in the lookup table with real identifiers | §6 query |
| Full `?p ?o` dump for the Tagaung site | Would confirm the record id, team tag and originating document in one shot before anyone opens the repo | §5 query |

**Nothing in this report comes from a source file.** The §2 conclusion is about MinMod's mapping, and it is 🟢 because both halves of the comparison came from MinMod's own artifacts — the graph and the Postgres export. Every statement about what a source file *contains* is on the checklist above, not in the findings.

---

## Run record

`probe-runs/2026-09-13/`

| File | What |
|---|---|
| `profile_xlsx.py` | Full census of all 24,818 merged rows — sources, CRS, team tags, column ranges |
| `collect_raw.py` | Recovers 123 out-of-range raw records from saved SPARQL snapshots; writes `raw_outofrange.csv` |
| `decisive.py` | The side-by-side test — reprojects and compares; writes `decisive_table.csv` (107 matched records) |
| `axis_order.py` | Reproduces the exact defect; identifies the two `pyproj` call shapes that cause it |
| `samples.py` | Per-source sample record ids and dedup compression |
| `p1.1-source-census.rq` | §1 query, written and saved — **failed with `curl (60)`**, ready to re-run |

Endpoint was contacted once, failed TLS verification, and was not contacted again. TLS verification was **not** disabled. No writes anywhere.
