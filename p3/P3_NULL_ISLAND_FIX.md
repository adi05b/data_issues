# P3 — Null Island fix: never keep POINT (0 0) as a location

*Branch `fix/p3-null-island` in `ta2-minmod-kg`, from main `ab1c352`. **3 local commits, not pushed, no PR.** Measured offline on `ta2-minmod-data` `3a086a5`, with the same setup as `p3/run-main`. Nothing live was touched.*

## Diff

| commit | file | change |
|---|---|---|
| `4681f01` Treat POINT (0 0) as no coordinate in the location view | `minmodkg/models/kgrel/custom_types/location.py` | +28 −3. New `drop_null_island(geometry)`, which `LocationView.from_location` applies to the parsed WKT before the centroid and the reprojection |
| `7fc92b6` Bump merge cache for the Null Island change | `minmodkg/etl/mineral_site.py` | `merge-v107` → `merge-v108` |
| `48ee8ce` Tests: Null Island is cleared, real coordinates untouched | `tests/test_misc.py` | +63, 10 tests |

**Where.** `LocationView.from_location` is the only place a record's lat/lon is computed from its location. Every writer goes through it via `MineralSite.from_raw_site`: the ETL merge (`MergeFn`), the API create/update path (`api/models/public_mineral_site.py`) and the GeoChem loader. So a site posted through the API with `POINT(0 0)` also gets no lat/lon.

**Rule.**
- Coordinates are read as numbers, in the source's own CRS, before any reprojection. `-0.0 == 0`, so every spelling counts.
- A **POINT** at (0, 0) gets no lat/lon.
- A **MULTIPOINT** drops its (0, 0) points and takes the centroid of the rest. If nothing is left, it gets no lat/lon.
- Unchanged:
  - other geometry types (there are no polygons in the data), empty geometries and the existing `nan` guard;
  - country and state;
  - the raw `location` written to the KG, since `to_kg` uses `location.coordinates`;
  - signs: no sign is flipped anywhere.

**Caches.**
- **`merge-v108`:** bumped. `location_view` is computed in `MergeFn`, whose cache is keyed by the raw input files, so without the bump a rebuild would replay the old views. The run below did use `merge-v108.sqlite`.
- **`EntityDeserFn` (`transform-v107`):** not bumped. It caches entity tables only.
- **`ExportTTLFn` (`export-v101`):** not bumped. It is keyed by the merged file's sha256, so it invalidates itself, and it writes the raw location anyway. The same-as caches are unrelated.
- **#110:** also bumps `merge-v107` → `merge-v108` (and `EntityDeserFn` `v107` → `v108`). Whichever of the two merges second must move the merge cache to **`merge-v109`**.

## Tests

- **New, 10 in `tests/test_misc.py`.** They sit next to the #108 reprojection tests; that file is already in the Tests workflow's list.
  - `POINT(0 0)`, `POINT (0.0 0.0)`, `POINT(-0.0 0.0)`, `MULTIPOINT((0 0), (0 0))` and a UTM 12N `POINT (0 0)` all get no lat/lon, and country and state are kept.
  - `MULTIPOINT((0 0), (10 20))` gives (lat 20, lon 10).
  - `POINT(0 10)`, `POINT(10 0)`, a normal point and a real UTM point are unchanged.
  - **All pass.** With the fix reverted, the 6 Null Island cases fail and the 4 unchanged cases still pass.
- **The Tests workflow's list (no Docker):** main 50 passed / 15 failed, branch 60 passed / 15 failed. The 15 are the same on both: `FileNotFoundError` on the SHACL schema in `vendor/ta2-table-understanding`, because that submodule isn't initialised in this checkout.
- **Full suite with Docker:** the conftest's own Fuseki and Postgres containers, with a scratch copy of `tests/resources/config.yml` that only changes the kgrel host so it resolves on this Mac. Main **69 passed / 23 failed**, branch **79 passed / 23 failed**. The same 23 fail on both sides and nothing is new:
  - 15 from the `vendor` submodule (`test_sample` 11, `test_validators` 4);
  - 4 in `tests/api/test_mineral_site.py`: the create endpoint returns 422;
  - 3 in the backup listener (it needs a git repo dir);
  - 1 in `test_mineral_site_service`'s upsert: `AttributeError: 'DedupMineralSiteAndInventory' object has no attribute 'get_update_args'` (`services/mineral_site.py:765`), a bug already on main.

  So none of the Docker tests that create sites through the API pass on either side. This change's coverage is the unit tests plus the full rebuild below.
- **`black` 26.10.0** on the three files reflowed one new line; the other two files were already clean.

## Step 4 — measured against expected

`p3_null_island_measure.py` compares all 679,778 records and every partial merged site in `run-main` and `run-null-island` (inventories compared as sets, since their order is per-process noise). It then rebuilds every merged site whose inputs differ with `DedupMineralSite.from_dedup_sites`. Results: `out/null_island_fix.json`.

| | expected | measured |
|---|--:|--:|
| records that lose their coordinate | 37, all Inferlink | **37**, all `api.cdr.land` (Inferlink) |
| · POINT at (0, 0) → no lat/lon | | 34 (`POINT(0 0)` 27, `POINT(0.0 0.0)` 6, `POINT(-0.0 0.0)` 1) |
| · MULTIPOINT, all at (0, 0) → no lat/lon | | 3 (`MULTIPOINT(0 0)`) |
| · MULTIPOINT, some at (0, 0) → centroid of the rest | | 0 |
| merged sites that change | 29 | **29**, only `coordinates` differs |
| · → no coordinate | 25 | **25** |
| · → another member's point | 4 | **4** |
| other records changed | 0 | **0** |
| other merged sites changed (coordinate, country, state or anything else) | 0 | **0** |

34 merged sites have a (0, 0) member, and all 34 were rebuilt. Five of them don't change, because the zero record wasn't the one kept.

## The 4 fallbacks

| merged site | name | recorded country / state | old | new: record and WKT | |
|---|---|---|---|---|---|
| `…021c1446…__inferlink` | Oropesa | Spain / "Ba" | `POINT(0.0 0.0)` | Inferlink `02bb6d11…`: `MULTIPOINT(-5.475 -19.00)` | ⚠ **looks sign-flipped**: −19 is south of the equator, Spain is north of it |
| `…022513c3…__inferlink` | Ambatovy Nickel Project | Madagascar / "Ra" | `POINT(0 0)` | Inferlink `02c1b00d…`: `MULTIPOINT(48.0 17.5)` | ⚠ **looks sign-flipped**: +17.5 is north of the equator, Madagascar is south of it |
| `…022da331…__inferlink` | Lynn Lake | Canada / Ontario | `POINT(0 0)` | Inferlink `0280c84b…`: `POINT(-97.8601 56.8013)` | in Manitoba |
| `…0254ffd6…__inferlink` | Munali | Zambia / Southern | `POINT(0.0 0.0)` | MRDS `10231516`: `POINT (28.11805 -15.89717)` | plausible |

Not fixed: sign errors are a separate issue. Full ids are in `out/null_island_fix.json`.

## Noticed, not changed

- **Inferlink sign errors:** Oropesa and Ambatovy above. Clearing (0, 0) exposes them as the next point in line.
- **Lynn Lake's fallback differs from P3_MEASURE.** P3_MEASURE's simulation, which also applied the precision tie-break, gave (−99.67, 55.99); this change keeps the current order and gives (−97.86, 56.80).
- **Odd recorded states:** Lynn Lake is recorded in Ontario, but both candidate points are in Manitoba. Oropesa's state resolves to "Ba" and Ambatovy's to "Ra". These look like state-matching issues of the Problem 2 kind.
- **The KG keeps `POINT(0 0)` for these 37 records, by design.** Anything reading `:location` straight from SPARQL still sees it; only the location view and the merged sites change.
- **`get_update_args`:** a pre-existing `AttributeError` on `DedupMineralSiteAndInventory` (`services/mineral_site.py:765`) fails the upsert test on main.

Not done: the precision tie-break, sign fixes, or recording coordinate accuracy at ingest. Draft PR text: `PR_P3.md`.
