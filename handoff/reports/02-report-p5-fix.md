# Report 02: Problem 5 fix, a commodity corrections list

*2026-10-20. Committed locally, nothing pushed, no PR opened. ProcMine unchanged. No graph, Postgres or API was touched.*

## Summary

- **Data:** `ta2-minmod-data` branch `p5-commodity-corrections` @ `7ae473f`, on upstream `0c8b827`. It adds one file, `data/corrections/commodity.csv`, with 15 rows.
- **Updated 2026-10-22 (report 03, Part C):**
  - Both `Metal` rows now remap to Q674 Titanium > Metal, not Q628.
  - `Water` stays a remap to Q680.
  - Both are decided defaults; see "For you".
  - The data commit was amended (same message), and every number below was re-measured.
- **kg:** `ta2-minmod-kg` branch `fix/p5-commodity-corrections` @ `3766487`, on main `45a2a16`, in worktree `ta2-minmod-kg-p5`.
- **Effect, measured offline with main's own merge code on all 679,778 records:**
  - The 7 defects go to 0, except the listed leftovers (SC 2, S 12).
  - Merged sites listing Strontium go from **46,612 to 393**.
  - **0 unintended changes:** no other candidate, no other site field, no merged country, state or coordinate.

## Diff summary

**`ta2-minmod-data`** (1 commit: `Add a commodity corrections list (Problem 5)`)

| file | |
|---|---|
| `data/corrections/commodity.csv` | new; header + 15 rows; CRLF like the entity tables |

**`ta2-minmod-kg`** (3 commits)

| commit | files |
|---|---|
| `0f8f5a5` Apply commodity corrections when loading sites (Problem 5) | `minmodkg/misc/commodity_corrections.py` (new, 140 lines); `minmodkg/etl/mineral_site.py` (+26); `etl.yml` (+1) |
| `8f657d0` Bump merge cache for commodity corrections | `merge-v107.sqlite` → `merge-v109.sqlite` |
| `3766487` Tests: commodity corrections | `tests/misc/test_commodity_corrections.py` (25 tests), a fixture under `tests/resources/commodity_corrections/`, and one line in `.github/workflows/tests.yml` |

**Where the list goes: `data/corrections/commodity.csv`, not `data/entities/`.**
- kg's entity ETL reads a fixed list of nine files (`etl/kgrel_entity.py:56-66`), so a new file in `data/entities/` would be ignored.
- But `etl.yml`'s filename validator globs `data/entities/*.csv`, and that folder holds Q-id entity tables (its README gives the id ranges).
- Nothing reads `data/corrections/`.

**Hook point: `MergeFn.invoke`** (`etl/mineral_site.py:449`).
- It is the only ETL read of a site's `mineral_inventory` that comes before both `from_raw_site` and the TTL export. The export reads the merged `ms.inventories`.
- The same-as step 0 also reads site files, but only their ids (`etl/same_as.py:445-452`).
- The list is applied to each raw site dict just before `MineralSiteAndInventory.from_raw_site`.
- `etl.yml` passes `commodity_corrections: ::REPO::data/corrections/commodity.csv`. A missing file means an empty list.
- The file's content hash is part of the merge cache key (`corrections_files`), so a later edit to the list re-merges without another version bump.
- **The API/editor and GeoChem paths are unchanged.**

**Caches.**
- `merge-v107` → `merge-v109`, as asked.
- `export-v101` needs no bump: it is keyed on the merged file's sha256 (`etl/mineral_site.py:491-495`), so it re-runs whenever the merged output changes.
- No entity or same-as cache needs a bump: none of their inputs or code changed.

## Tests

| run | result |
|---|---|
| `tests/misc/test_commodity_corrections.py` (fixture) | **25 passed** |
| same, with `MINMOD_DATA_DIR=<data branch>/data` | **25 passed**: every remap target is in `commodity.csv`, and no row matches the Last Chance Sulfur Mine |
| full suite with Docker, **main** `45a2a16` | 80 passed, **23 failed** |
| full suite with Docker, **branch** `3766487` | 105 passed, **23 failed**: the same 23 tests with the same messages; the 25 extra passes are the new tests |

**Full suite setup:**
- The repo's own Fuseki and Postgres test images (built from `containers/fuseki` and `containers/postgres`, image ids `670676e6a842` and `3b61d2d28efd`), on Docker 29.4.0.
- A scratch copy of `tests/resources/config.yml` points kgrel at the local test container, because the configured host does not resolve on this Mac (as in P6).
- The `vendor/ta2-table-understanding` submodule is not checked out, the same as the P2 baseline.

**The 23 pre-existing failures:**
- 11 `test_sample.py` and 4 `test_validators.py` (SHACL; they need the submodule);
- 4 `api/test_mineral_site.py`;
- 3 `test_backup_listener.py`;
- 1 `test_mineral_site_service.py`.

**What the new tests cover:**
- each action changes a candidate as expected: drop, remap with a context, remap without one;
- non-matching records are untouched: another source, case, no inventories, an unmatched candidate, one already at the target;
- the context must match: Oregon `stone | crushed | S | G` and `sand and gravel | SC` are untouched;
- the sulfur mine is untouched (the real record);
- a matching context wins over an empty one;
- bad lists are refused;
- through `MergeFn`, the stored inventories, `to_kg()` and the views all show the corrected value;
- an empty list is byte-for-byte the same as no list.

`black` 25.9.0 (the P6 version; it leaves main's `mineral_site.py` unchanged) was run on the three changed Python files.

## Step 3: measured offline

**Setup:**
- The investigation's harness (`p2d_run_merge.py`) on the data branch.
- `run-main0`: main code with `p2_etl.yml`.
- `run-fix0`: branch code with `p5/p5_etl.yml`.
- `run-nolist0`: branch code with a list path that doesn't exist.
- All three with `PYTHONHASHSEED=0`; see Deviations.
- Compared by `p5/p5_fix_measure.py` → `p5/out/p5_fix_measure.json` and `p5/out/p5_fix_rows.csv`.

**Byte checks:**
- `run-main0` vs `run-nolist0`: **0 of 2,446 merged files differ.**
- `run-main0` vs `run-fix0`: 192 differ, exactly the 192 site files that hold a defect.

**The 7 defects.** "Merged sites listing it" means merged sites that list the wrong commodity from any member.

| defect | records before → after | merged sites with a defect member | merged sites listing the wrong commodity |
|---|--:|--:|--:|
| `Construction` → Strontium | 46,221 → **0** | 46,220 → **0** | Strontium 46,612 → **393** |
| `SC` → Scandium (Oregon) | 7,076 → **2** | 2,949 → **2** | Scandium 2,998 → 51 |
| `S` → Sulfur (Oregon) | 2,349 → **12** | 2,349 → **12** | Sulfur 4,174 → 1,837 |
| `Construc` → Cobalt | 980 → **0** | 980 → **0** | Cobalt 4,042 → 3,062 |
| `CS` → Cesium (Oregon) | 6 → **0** | 6 → **0** | Cesium 42 → 36 |
| `SD` → Sand (Oregon) | 41 → **0** | 41 → **0** | Sand 688 → 647 |
| `Metal` → Nonmetal (now → Q674 Titanium > Metal) | 916 → **0** (mrds 840, nc 76) | 821 → **0** | Nonmetal 824 → 3 |

**The other 8 rows:**

| row | inventories | records | merged sites | wrong commodity, merged sites listing it |
|---|--:|--:|--:|--:|
| `Volcanic Materials` → Q679 | 487 | 487 | 487 | Clay > Bloating Material 527 → 40 |
| `Water` → Q680 | 260 | 221 | 220 | Slate 618 → 398 |
| `Industrial` drop | 11 | 11 | 11 | Indium 94 → 83 |
| `Soda Ash` drop | 8 | 8 | 8 | Ash 13 → 5 |
| `Tripoli` drop | 1 | 1 | 1 | Lithium 773 → 772 |
| `Halloysite` drop | 1 | 1 | 1 | Alunite 468 → 467 |
| `Gilsonite` → Q649 | 1 | 1 | 1 | Wollastonite 134 → 133 |

**Targets:**
- Stone > Crushed/Broken: 17,689 → 20,643 merged sites (+2,954 = 2,948 SC + 6 CS).
- Stone > Dimension: 344 → 385 (+41).
- Titanium > Metal Q674: 774 → 821 merged sites (records 811 → 1,727). SRI's copy of MRDS already maps `Titanium, Metal` → Q674 on 811 records.
- Volcanic Materials Q679: 256 → 562 (181 SRI copies already had it).
- Water Q680: 1 → 221.
- Gilsonite Q649: 0 → 1.

**Dashboard grain** (records carrying the QID):
- Strontium 47,112 → 892
- Scandium 7,139 → 65
- Sulfur 5,171 → 2,834
- Cobalt 6,535 → 5,555
- Cesium 65 → 59
- Sand 735 → 694
- Nonmetal 919 → 3

**Grade/tonnage:**
- **Dropped:** 2 inventories had grade/tonnage, and **both are duplicated on the same record**: MRDS `10115528` and `10236674`, `Construction` with the same grade and ore as their Sand And Gravel row. No stop condition was met.
- **Moved by a remap:**
  - 10 merged sites now show grade/tonnage under Titanium > Metal (it was under Nonmetal). These are MRDS's own `Titanium, Metal` row.
  - 2 merged sites now show it under Water (it was under Slate). These are MRDS's `Water, Free` row. The rare-earth rows on those records are phantoms of "Free" that copy it (report 03).

**Unintended changes: 0.**
- Every one of the 679,778 records keeps every site field except `inventories`, and its inventories equal main's with the list applied, nothing more.
- The merged partials are unchanged: name, coordinates, country, state, deposit types, ranks.
- For each of the 54,057 merged sites with a corrected member, both runs were rebuilt with `DedupMineralSite.from_dedup_sites`. Every commodity removed is the old QID of a corrected candidate, every one added is a remap target, and no other commodity's grade/tonnage changed.
- 0 merged sites are left with no commodity.
- 2 merged sites keep the old QID because another candidate has it:
  - MRDS `10186268` "Strontium Group" (a genuine Strontium);
  - merged site `id-05487`, which keeps Scandium from the leftover `ID_23259` (`sand and gravel | SC`).

## Leftovers (untouched, by design)

| what | records | why |
|---|--:|---|
| Oregon `stone \| crushed \| S \| G` (S stays Sulfur) | 11 | can't be decoded from the record |
| Oregon `sand and gravel \| SC` (SC stays Scandium) | 2 | can't be decoded from the record |
| Last Chance Sulfur Mine, `ID_04514` (`sulfur and pyrite \| S`) | 1 | S really is sulfur |
| mineral names judged wrong in H5: Galena 4, Chalcopyrite 3, Hematite 1, Apatite 1, Monazite 11, Sillimanite 3, Tourmaline 1, Vesuvianite 1 | 25 | your decision: no drop reason (the string is the record's own information, the only commodity on 15 records) and no factual target |

Out of scope and unchanged:
- Wrong matches above 0.62 from the earlier diagnosis (e.g. Halite → Alunite, Salt → Aluminum, Emery → Emerald).
- PGE/REE/HAL unmatched.

## Deviations

1. **Rows beyond the table** (all from the investigation's facts or `commodity.csv`):
   - `Volcanic Materials` → Q679 and `Water` → Q680 are remaps. Q679 and Q680 are missing from ProcMine's table. Report 03 adds that MRDS writes `Water, Free` (code `H2O`), whose code entity is Q680.
   - `Gilsonite` → Q649: `commodity.csv` has Petroleum (Oil) > Gilsonite.
   - `Industrial`, `Soda Ash`, `Tripoli` and `Halloysite` are drops: every one of their records already carries the commodity the string stands for.
   - `Metal` needs two rows, for mrds and nc.
2. **Apatite "per `commodity.csv`":** `commodity.csv` has no apatite entity, so it falls under the mineral-name decision and is left out.
3. **Only matched candidates are corrected, and a remap already at its target is skipped.**
   - Without this, `Soda Ash` and `Tripoli` would also drop SRI's *unmatched* copies of the same string under the same `source_id` (8 + 1 inventories that the investigation never flagged).
   - And `Volcanic Materials` would rewrite 181 SRI candidates that already map to Q679.
4. **`MergeFn.invoke` takes `corrections_files: list[InputFile]` (zero or one file) rather than `Optional[InputFile]`.** libactor's cache rejects `Optional` argument types: `issubclass(Union, …)` raises.
5. **Byte-for-byte needed a fixed hash seed.**
   - Main's merged output is not byte-stable between runs: `from_raw_site` adds view rows by iterating a `set` of commodity ids (`models/kgrel/mineral_site.py:140-141`).
   - Two runs of main differ in 1,554 of 2,446 files, with the same rows in a different order. That is pre-existing.
   - With `PYTHONHASHSEED=0`, branch-without-list equals main exactly.
6. **The test fixture has no `data/` level** (`tests/resources/commodity_corrections/{corrections,entities,mineral-sites}`), because kg's `.gitignore` ignores any `data*` path. The data checks therefore take `MINMOD_DATA_DIR=<checkout>/data`.
7. **The data checks are kg tests**, in the alt-names style: they default to the fixture and use the real data when `MINMOD_DATA_DIR` is set.
8. **The new test file is added to the CI Docker-free list**, as #111 did.
9. **`run_acceptance.sh:126` still says `merge-v106`.** It is already stale on main, and #110 edits that line, so I left it alone.
10. **Git identities.** The data commit uses the global git config (`adi05b`); kg uses its repo config (`Aditi Bombe`). Both have the same noreply email.
11. **Branches.** The data clone is `p5/ta2-minmod-data`, the blobless clone of upstream from the investigation. A remote `fork` → `adi05b/ta2-minmod-data` was added but not fetched or pushed. The kg worktree `ta2-minmod-kg-p5` is kept, because it holds the branch.

## For you

- **Merge order:** the data PR first, then kg. Without the file, kg changes nothing.
- **Decided defaults:**
  - `Metal` → Q674 Titanium > Metal: MRDS writes `Titanium, Metal` (code `TI_M`), and its grade rows are that row.
  - `Water` stays a remap to Q680: MRDS writes `Water, Free` (code `H2O`). The rare-earth rows copy Water's grade, not the reverse, so dropping Water would keep 15 phantoms and remove the real commodity.
- **Still open for Amandeep** (in `p5/PR_P5_KG.md`):
  - remap vs drop for Oregon;
  - API edits are not corrected.
- **Nothing is pushed.**
  - Data: `git -C p5/ta2-minmod-data push fork p5-commodity-corrections`.
  - kg: push `fix/p5-commodity-corrections` from `ta2-minmod-kg-p5`.
