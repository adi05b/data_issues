# P3 — precision tie-break (option B): a more precise coordinate wins a trust-score tie only if it refines the same point

*Branch `fix/p3-null-island`: commit `e021ab2` on top of the 3 Null Island commits. **Local only, not pushed, no PR.** Measured offline on `ta2-minmod-data` `3a086a5`, with the same setup as `run-main`. Nothing live was touched.*

## Diff (`e021ab2`, 9 files, +432 −17)

| file | change |
|---|---|
| `minmodkg/misc/coord_precision.py` | **New**, 164 lines, ported from `p3_measure.py` / `p3_amandeep.py`: `real_decimals`, `dms_grid`, `SourceCoordinate.resolution_km` / `.contains` (the per-axis rounding box) and `finest_refinement`. The docstring explains why decimal places as written aren't precision. |
| `minmodkg/models/kgrel/dedup_mineral_site.py` | +81 −7. `prefer_refined_coordinate` runs after the existing `next(...)` in both `from_sites` and `from_dedup_sites`, and both take `crs_names` |
| `minmodkg/models/kgrel/custom_types/location.py` | `Location.crs_name(crss)`, now also used by `from_location` (no behaviour change) |
| `etl/mineral_site.py`, `etl/geochem_loader.py`, `services/mineral_site.py` | pass `crs_names` (9 call sites) |
| `tests/misc/test_coord_precision.py`, `tests/models/kgrel/test_dedup_mineral_site.py`, `.github/workflows/tests.yml` | 15 tests, added to the Tests workflow |

**The rule, as briefed:**
1. Take the records that hold the top trust score and have a coordinate.
2. If the top is an expert/curator record, or only one record holds the top score, nothing changes.
3. The pick is main's: the first in the current order.
4. Another tied record replaces it only if its real precision is **strictly finer** *and* it lies **inside the pick's rounding box, each axis on its own**. Raw numbers are compared when both are POINTs in the same CRS; otherwise the WGS84 views are.
5. The finest such record wins; on a tie the current order stands.
6. Only the coordinate changes.

**Two choices beyond the brief:**
1. **`crs_names` is a required keyword on both elections.** The CRS vocabulary (`Q701` → `EPSG:4326`, …) is entity data, not code, and a coordinate's unit and its DMS check depend on it.
   - It is required, not optional, so no caller can elect without the tie-break. The API's five re-elections in `services/mineral_site.py` would otherwise undo it on the next edit of a site.
   - The ETL passes its `FileEntityService`; the API and the GeoChem loader use `EntityService.get_instance()`, as they already do for `from_raw_site`.
2. **`from_dedup_sites` ranks all member `sites` (by `ms2score`), not only each partial's pick.**
   - A tied record that wasn't its own partial's pick still counts, so both paths apply the identical rule.
   - The pick is the first coordinate in that order, i.e. what main picks today (it matches main on all 23,283 sites, P3_MEASURE).
   - If main's partial pick doesn't hold the top score, nothing changes. That never happens in the data.

**Null Island:** (0, 0) records have no lat/lon after commit 1, so they are never candidates. `test_null_island_is_never_a_candidate` covers it, and so does the combined run below. **No cache bump** beyond this branch's `merge-v108`.

## Tests

- **`tests/misc/test_coord_precision.py`, 8 cases:**
  - `40` → 0 dp, `40.12345` → 5, `35.1000000000000000` → 1 (padded), `28.1180500000000002` → 5;
  - `-38.9166666666667` counts at the arcminute grid (1.86 km), not as 13 dp;
  - float noise in a projected CRS (Oregon feet, `741725.31000000001`) adds no precision, so it can't replace `741725.31`;
  - the box is per axis;
  - a refinement is found only inside the box.
- **`tests/models/kgrel/test_dedup_mineral_site.py`, 7 cases:**

  | case | result |
  |---|---|
  | tied, the second is the same spot with more digits | switches ✓ |
  | tied, more precise but 0.06° away (outside the box) | keeps ✓ |
  | the higher-score record is coarser | keeps ✓ |
  | the top is expert/curator (both at 1.0) | keeps ✓ |
  | tied, equal precision (`30.010` vs `30.01`) | keeps the current order ✓ |
  | a (0, 0) record first in order | never a candidate; the next record is refined ✓ |
  | `from_dedup_sites`, each record in its own partial | switches ✓ |

  With the tie-break stubbed out, the 3 switching cases fail and the 4 keeping cases still pass.
- **Existing location tests** (`tests/test_misc.py`, 13) and `test_site_score`: pass.
- **The Tests workflow's list, with the two new files:** branch 75 passed / 15 failed. The 15 are the same `vendor`-submodule SHACL failures as on main.
- **Full suite with Docker:** main **69 passed / 23 failed**, branch **94 passed / 23 failed**. The same 23 fail on both sides. The +25 are the 10 Null Island tests and the 15 new ones.
- **`black` 26.10.0** on all changed files.

**The float-print test.** The brief asks that a float print in a projected CRS not count as more precise just for having more digits. Under P3_MEASURE's definition, float prints count at their real digits: digits beyond what a double holds are dropped, and that is what the test pins. A float print of a *different* point is stopped by the box. Excluding float prints outright would break the exact-168 match, because 13 of the 168 new points are float prints.

## Step 3 — measured

Three merges on `3a086a5`, each compared with `run-main`. Every merged site where a change is possible (23,308) is rebuilt with its own run's code: main `ab1c352`; Null Island only `48ee8ce`; tie-break only, this commit with the Null Island step switched off for the run (`null_island_off/sitecustomize.py`, measurement only); and both, this commit. Every record is compared too. Results are in `out/tiebreak_*.json` and `*_changes.csv`.

| run | expected | measured |
|---|---|---|
| **tie-break only** | 168, identical to `amandeep_row5.csv`; median ~4 m, max ~2.8 km | **168**: the same 168 sites, with the same new record for each. Median **4.3 m**, p95 0.81 km, max **2.82 km**; 26 move over 100 m, 6 over 1 km. 0 records changed |
| **Null Island only** | 29 | **29** (25 → no point, 4 → another member's point); 37 records |
| **both** (as shipped) | report | **197 = 168 + 29, no overlap** |

In every run, only the `coordinates` field changes.

**Why there's no overlap:** none of the 29 Null Island sites is among the 168, and the 4 fallbacks are identical with and without the tie-break. Lynn Lake's fallback, `POINT(-97.8601 56.8013)`, has no tied record inside its own box, so it stays. P3_MEASURE's (−99.67, 55.99) came from a rule without the box.

## Invariants (tie-break changes, every run)

| | count |
|---|--:|
| the top record is an expert/curator | **0** |
| the new point has a lower score than the old one | **0** |
| the new point is outside the old point's box | **0** |
| the new point is not strictly more precise | **0** |
| a change between different scores | **0** |
| country, state or any field other than the coordinate changed | **0** |

One lower-score move exists, in the Null Island part and by design: Munali goes from the Inferlink (0 0) record (0.8) to MRDS (0.1), the next member with a coordinate. It is already reported in P3_NULL_ISLAND_FIX.

## Source pairs of the 168

| source pair | sites |
|---|--:|
| MRDS siblings | 75 |
| porcu → major-deposits | 32 |
| P9HTERGK siblings | 11 |
| ree → P9K1HBNT | 10 |
| ree → carbonatite | 8 |
| sedcu → major-deposits | 7 |
| sir20105090z → sedcu | 4 |
| ree → major-deposits | 3 |
| ree → pp1802 | 3 |
| sedznpb → sedexmvt | 2 |
| 13 other pairs, 1 each | 13 |

## Five examples

| moved | merged site | name | picked | now |
|--:|---|---|---|---|
| 1 m | `mrdata-usgs-gov-mrds__10049096__sri` | La Dorada | MRDS, 4 real dp: `POINT (-110.8006599999999935 29.5640999999999998)` | MRDS sibling, 5 dp: `POINT (-110.8006599999999935 29.5640900000000002)` |
| 7 m | `mrdata-usgs-gov-major-deposits__1134__sri` | Los Bronces/Rio Blanco | porcu, DMS arcminute: `POINT (-70.2666666666667 -33.1333333333333)` | major-deposits, 4 dp: `POINT (-70.2666 -33.1333)` |
| 311 m | `mrdata-usgs-gov-carbonatite__3__sri` | Mount Weld | ree, DMS arcminute: `POINT (122.55 -28.866666666667)` | carbonatite, DMS arcsecond: `POINT (122.548055555556 -28.8644444444444)` |
| 1.2 km | `doi-org-10-34191-ofr-757__4582__umn` | Copper Globe | sedcu, 1 dp WGS84: `POINT (-110.9 38.8)` | OFR-757, UTM 12N metres: `POINT (507527 4295014)` |
| 2.8 km | `api-cdr-land-v1-docs-documents__02282971…__inferlink` | Kwanika | Inferlink, 1 dp: `POINT(-125.3 55.5)` | Inferlink, DMS arcsecond: `POINT(-125.333333 55.516944)` |

Los Bronces shows the rule's limit: the "more precise" 4-place value is the arcminute value re-rounded. It moves 7 m and adds no real information, but it does no harm.

## Files

- `p3_tiebreak_measure.py`: rebuild and compare.
- `null_island_off/sitecustomize.py`: measurement-only switch.
- `out/tiebreak_{tiebreak-only,null-island-only,both}.json` and `_changes.csv`.
- The run directories are gitignored.
- PR text: `PR_P3.md` (title, tie-break bullets and combined numbers updated).
