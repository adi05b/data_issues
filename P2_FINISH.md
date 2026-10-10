# Problem 2: finishing the kg branch

*2026-10-09. Worktree `ta2-minmod-kg-p2`, branch `fix/p2-state-repair`. Committed locally, not pushed, no PR opened.*

## Rebase

- **`git rebase origin/main` onto `ab1c352` (#108) was clean. There was no conflict at all.**
  - #108 changed `minmodkg/misc/geo.py` (`always_xy=True` on both transformers), not `location.py`, so the expected conflict did not happen.
  - `location.py` keeps this branch's changes. Its `reproject_geometry` call now uses #108's `always_xy` transformer, so both changes are in.
- **Check:** the rebased branch differs from the old head `f01a385` by exactly #108's diff.
- **No fix-up commit was needed**, so commit 1 does not exist.
- **The rebase rewrote the earlier SHAs:**

  | old | new |
  |---|---|
  | `5318bdf` | `96e3d08` |
  | `9d68111` | `35268f4` |
  | `a888391` | `8bda1f7` |
  | `f01a385` | `968c378` |

  The reports in `minmod_data_issues` still cite the old SHAs.
- **`origin/fix/p2-state-repair` is still at `f01a385`**, so publishing will need a force-push.
- **The old head is kept as local branch `backup/p2-pre-rebase-f01a385`.** Delete it when you no longer need it.

New commits on top:

| commit | |
|---|---|
| `5f249a2` | Option A: add British Virgin Islands and Cayman Islands |
| `7942072` | Fill Katanga records from their location (four 2015 successor provinces) |
| `6af4901` | Bump merge and entity caches for state repair (`merge-v107` → `merge-v108`, `EntityDeserFn.VERSION` `v107` → `v108`) |
| `61fda35` | Update acceptance compare notes (amended: the `merge-v106` comment now says `merge-v108`) |

## Tests (HEAD `61fda35`)

| | result |
|---|---|
| `tests/misc/test_state_repair.py` + `tests/test_misc.py` (#108's test) | **46 passed** |
| `tests/misc/test_state_repair.py` with `MINMOD_ENTITY_DIR` = data branch `250abc7` | **43 passed** |
| `minmod_data_issues/tests/test_p2_dedup_pairing.py` | 5 / 5 |
| `minmod_data_issues/tests/test_always_xy.py` (#108) | 7 / 7 |
| `minmod_data_issues/tests/test_p2_repair.py` | **27 / 27** (after `92db179`, below) |
| full suite with Docker (`minmod-fuseki`, `minmod-postgres`, `kg-postgres` → `127.0.0.1`) | **112 passed, 23 failed**; `main` (`ab1c352`): 69 passed, 23 failed |

**`test_from_location_on_the_corpus` was stale; it is fixed in `minmod_data_issues` `92db179`** (local, not pushed).
- It asserted "the country is never repaired", which predates Option A.
- It now allows only a listed Option A move, and pins the counts per pair: 49 / 15 / 5 / 3 / 2 / 1.
- That commit sits on `3630a37`: I fast-forwarded local `main` to `origin/main` first. `3630a37`'s `patches/0006` lists the same two UK pairs as `5f249a2` here.

**The full suite fails the same 23 tests, with the same errors, on `main` and on this branch:**
- 15 need the `vendor/ta2-table-understanding` schema, a submodule that is not checked out;
- 3 are `git status` exit 128 in the backup-listener tests;
- 5 are API/service assertion errors: 422, 403, a message mismatch, and a missing `get_update_args`.

The 43 extra passes are the new `tests/misc/test_state_repair.py`.

## Step 5 numbers

Harness `p2c/rerun`: **run D** is this branch at `6af4901` (snapshot in `code/kg-6af4901`) on data `250abc7`, compared with base and C from the same harness. Outputs are in `rerun/reports/p2e/`.

| | before (run C) | now (run D) |
|---|--:|--:|
| conflicted in base | 5,856 | **5,856** |
| still conflicted | 0 | **0** |
| state repointed | 5,543 | **5,543** |
| state filled from location (Katanga) | — | **92** |
| state emptied | 313 | **221** |
| `state_country_conflicts` | 5,856 → 0 | **5,856 → 0** |
| `merged_with_state` vs base | −313 | **−221** |
| `merged_with_country` count vs base | 0 | **0** |
| entities whose country value changes | 77 (70 Option A + 7 pairing) | **80 (73 Option A + 7 pairing)** |
| records moved by Option A | 72 | **75** (+ BVI 2, Cayman 1) |

**Katanga, per record (the 111 drop-list records):**

| outcome | records |
|---|--:|
| filled: Haut-Katanga | **49** |
| filled: Lualaba | **41** |
| filled: Tanganyika | **4** |
| filled: Haut-Lomami | **1** |
| empty: within 2 km of an internal border | **3** |
| empty: outside the four provinces (the sign flips) | **4** |
| empty: no location | **8** |
| empty: round placeholder | **1** |

- **The 3 near the border are exactly `02c41f98…`, `10400590` and `10400593`.**
- **This reconciles with p2c's 98 in-province records** (gbHumanitarian 51 / 42 / 4 / 1): 95 filled plus 3 left empty by the border rule. The 3 split Haut-Katanga 2, Lualaba 1.
- **Per entity, 92 are filled:** Haut-Katanga 46, Lualaba 41, Tanganyika 4, Haut-Lomami 1.
- **15 Katanga entities stay empty:**
  - 8 have no location;
  - 3 are outside;
  - 2 are near the border;
  - 1 is a placeholder;
  - 1 holds both an outside record and `02c41f98…`.

**No regressions:**
- **C → D, per record:** exactly 95 Katanga fills and 3 Option A moves, and nothing else.
- **C → D, per entity:** 92 fills and 3 country moves, and nothing else.
- **Against base:** the 80 rebuilt entities that were not conflicted are unchanged.
- **All 80 country changes are in the conflicted set:**
  - Option A, 73: New Caledonia 48, Greenland 15, Christmas Island 4, Montserrat 3, BVI 2, Cayman 1;
  - the pairing fix, 7.

**How it was measured:** the same scripts as before (`p2d_run_merge.py`, `p2d_merged.py rebuild` on the same 5,936 entities), plus `scripts/p2e_measure.py` for the diffs and the per-record checks.
- **One difference from the earlier runs: the diff leaves out lat/lon.** #108 changes them for 32,095 entities (every non-WGS84 record).
- **That is safe:** the merge ranks sites by source score, creator, ids and `modified_at`, and elects country and state from `location_view.country` and `location_view.state_or_province` only.
- **Every other field was compared.**
  - Base → D: 5,927 entities differ beyond lat/lon, the same count as the earlier base → A.
  - C → D: 95 differ.
  - All of them are in the rebuilt set.

## Review list

`data_issues/P2_REVIEW_LIST.csv` has 221 entities, written by `p2c/review_list.py`.

| reason group | entities |
|---|--:|
| Option A | 73 |
| other | 50 |
| abolished unit | 31 |
| Katanga | 15 |
| county | 14 |
| island | 14 |
| wrong recorded country | 14 |
| city | 6 |
| Greenland | 4 |

- C's geometry suggestion is "fillable" for 81 of them. By `name_check`, those are 49 agrees, 22 contradicts, 8 unclear and 2 n/a (Katanga).

## Noticed, not changed

1. **The data file is not under `misc/data/`.** The repo's `.gitignore` has `data*` (line 165), which ignores `minmodkg/misc/data/`. The file is therefore `minmodkg/misc/katanga_successors.geojson`, next to `state_repair.py`.
   - Poetry ships every non-ignored file under `minmodkg/`, so `pyproject.toml` needs no change.
   - An offline wheel build includes the file.
   - The attribution line is a top-level `attribution` member in the GeoJSON, next to a `source` URL pinned to geoBoundaries commit `9469f09`, and is repeated in the code comment.
2. **`EntityDeserFn` is in `minmodkg/etl/kgrel_entity.py`**, line 81, not `models/kgrel_entity.py`. That is the one I bumped.
3. **Katanga requires the recorded countries to be exactly {DR Congo}.** All 111 records have DR Congo alone, so on this data "exactly" and "includes" give the same result.
4. **The 2 km rule covers only borders between two of the four provinces.** 5 filled Haut-Katanga records lie within 2 km of the provinces' outer edge (the Zambia side), and they are filled.
5. **The polygon topology is clean.** Neighbours share identical boundary lines with no overlaps, before and after rounding, and Lualaba and Tanganyika do not touch. "Shared border" is the union of the pairwise boundary intersections.
6. **The compare notes say nothing about `state_table_with_code`.** Every row of the data branch's table has a code (5,086), so after migration 005 and the entity reload it should go from 0 or absent to 5,086.
7. **The licence was read from geoBoundaries' metadata only** (see `GB_EDITIONS.md`). The HDX page itself was not checked.
8. **New files outside the repo:**
   - `p2c/naturalearth/gb_editions/extract_katanga_successors.py`, which writes the GeoJSON;
   - `p2c/review_list.py`;
   - `p2c/rerun/scripts/p2e_measure.py`;
   - `p2c/rerun/code/kg-6af4901`, `runs/kg-D`, the `work/*_D.json` files and `reports/p2e/`.
