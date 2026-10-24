# Report 06: #110 migration number, Problem 3 acceptance query

*2026-10-23. Read-only throughout. Both kg branches are rebased and committed locally; **neither is pushed**, and the PRs on GitHub are not edited. No live graph, Postgres or API touched.*

`handoff/reports/` had no P2 or P3 reports, only P5's. For P2 and P3 I read `P2_FINISH.md`, `PR_KG.md`, `p3/P3_NULL_ISLAND_FIX.md`, `p3/P3_TIEBREAK_FIX.md`, `p3/PR_P3.md`, `p3/p3_amandeep.sql`, `p3/verify_p3.py` and `p3/out/`.

## Step 1: #110, migration renumbered to 006

- **Rebased** `fix/p2-state-repair` onto `origin/main` `63ab67e`. All 8 commits applied cleanly; the old head was `61fda35`.
- **New commit `04a79c7`** "Renumber the state_code migration to 006":
  - `migrations/005_state_or_province_state_code.{up,down}.sql` → `006_…`;
  - the down script's header names the new file;
  - `migrations/status.sql` has a `006_state_or_province_state_code` row, in the same style as the others. It is applied when `state_or_province.state_code` exists.
- **Other references:** the down script's header was the only one in the repo. In the PR text, `PR_KG.md` now says 006, and so does the new `PR_110_BODY.md`.
- **Merge cache:** `run_acceptance.sh`'s note says `merge-v108`, matching `merge-v108.sqlite` in `etl/mineral_site.py`.
- **The migration, on a throwaway database** (the repo's Postgres 17.11 image), with tables made from main's models, so `state_code` was missing:
  - `migrations/apply_all.sh` ran 001 to 006 in order, 006 after 005;
  - the status row went from `f` to `t`;
  - running 006 up again is a no-op, and down sets it back to `f`.
- **Tests:**

  | | passed | failed |
  |---|--:|--:|
  | #110's own tests (`tests/misc/test_state_repair.py` + `tests/test_misc.py`) | 46 | 0 |
  | full suite with Docker, main `63ab67e` | 133 | 24 |
  | full suite with Docker, #110 `04a79c7` | 176 | 24 |

  - The 24 failures are the same tests with the same messages: 16 need the `vendor/ta2-table-understanding` SHACL files (submodule not checked out), 4 are API tests, 3 backup-listener tests and 1 the mineral-site service upsert. That is main's baseline from report 05.
  - The +43 passes are the state repair tests.

## Step 2: #111, `acceptance/problem3_coordinates.sql`

- **Rebased** `fix/p3-null-island` onto `origin/main` `63ab67e`. All 5 commits applied cleanly; the old head was `a8f2596`. `tests.yml` keeps main's addition and the two P3 test files.
  - Main added no new election call site. All 9 still pass `crs_names`: 5 in `services/mineral_site.py`, 2 in the ETL, 2 in the GeoChem loader.
- **New commit `d995f62`** "Acceptance query for coordinate fixes (Problem 3)". It adds only the new file; `run_acceptance.sh` is identical to main's.
- **Tests:**

  | | passed | failed |
  |---|--:|--:|
  | #111's own tests (`tests/test_misc.py`, `tests/misc/test_coord_precision.py`, `tests/models/kgrel/test_dedup_mineral_site.py`) | 28 | 0 |
  | `tests/services/test_mineral_site_service.py` | 4 | 1 (the upsert, also on main) |
  | full suite with Docker, #111 `6c475ec` | 160 | 24 (the same 24 as main) |

- **The query.** One read-only `WITH … SELECT`, 16 rows of `metric`, `value`, `expected`, in P5's style. The header says what it checks and how to run it, that the numbers come from data `0c8b827` and may drift a little, and that the merge cache must be `merge-v108` or later. It also says why `mineral_site.location` still holds `POINT (0 0)`, and that #110 in the same build lowers the state count by 221.
  1. Merged sites whose point is (0, 0).
  2. Raw sites whose lat/lon is (0, 0). The source WKT keeps `POINT (0 0)` by design, so this reads `location_view`.
  3. The 168 tie-break sites: how many now have their coordinate from the expected record (`coordinates.refid`).
  4. The 29 Null Island sites: how many now have no point (25), and how many are on the expected other member's point (4).
  5. Sanity: merged sites total, raw sites total, merged sites with a coordinate, with a country, with a state.
  6. The funnel, rows 1 to 3, with the same logic as `p3_amandeep.sql`.
- **The fixed list** is inline as `VALUES`: 197 rows of (kind, merged-site id, expected record id), taken from `p3/out/verify_p3_local_changes.csv`. That file agrees with `tiebreak_both_changes.csv`, and its 168 tie-break rows are the same sites and records as `amandeep_row5.csv`. No new data file. The query file is 33 KB, most of it ids.
- **Tables read:** `dedup_mineral_site` (`id`, `coordinates`, `ranked_sites`, `country_val`, `state_or_province_val`) and `mineral_site` (`site_id`, `source_id`, `location_view`). The bytea columns are read with `convert_from(…, 'UTF8')::jsonb`, as the P1 and P5 files do.

## Where it ran

- **Builds:** offline merges with `p2c/rerun/scripts/p2d_run_merge.py`, the same harness as P3 and P5, with `PYTHONHASHSEED=0`.

  | build | code | merge cache | records | merged sites |
  |---|---|---|--:|--:|
  | main | `63ab67e` | `merge-v107` | 679,778 | 419,098 |
  | branch | #111 `6c475ec` | `merge-v108` | 679,778 | 419,098 |

  - **Data:** P5's clone at `7ae473f`, which is `0c8b827` plus `data/corrections/commodity.csv`. Neither main nor #111 reads that file. A separate `0c8b827` checkout would have needed 1.5 GB the disk didn't have.
- **Loads:** `p5/p5_load_kgrel.py`, into the repo's Postgres 17.11 image, on loopback only, so both the full data and dev's Postgres version are covered in one setup.
  - **Loader change:** on #111, `from_dedup_sites` requires `crs_names` and reads each member's location for the tie-break. The loader now passes the run's CRS names when the election takes them, and each member's `site_id`, `location` and `location_view` instead of an id-only stub.
  - Main's election reads only `site_id` from the members, so main's load is unaffected. The main load was made before this edit.
  - Row counts are identical to report 05's main load: 702,056 merged and 1,119,946 record commodity rows.
- **Run** with `PGOPTIONS='-c default_transaction_read_only=on'`, about 13 s on main and 12 to 19 s on the branch.
  - Main's run used the query before its last edit: the same SQL, with `?` in `expected`, and before a comment rewording and the funnel rows' line breaks.
  - The final file gives values identical to that draft on the branch build.
- **Offline cross-check, `p3/p3_merged_diff.py`:** it elects all 419,098 merged sites from both run dirs, as the loader does, and compares them (`p3/out/p3_merged_diff.txt`).
  - **197** merged sites change their coordinate: 25 to no point, 4 to another member, 168 by the tie-break.
  - All 197 are the listed sites, each going from the listed old record to the listed new one.
  - 0 changed sites are unlisted, and 0 listed sites are unchanged.
  - 0 merged sites change any other field.

  So P3's 197 reproduce exactly on `0c8b827` with the rebased branch.

## Before / after (full data)

Raw outputs: `p3/out/p3_acceptance_kgrel_main.txt` (before) and `p3/out/p3_acceptance_kgrel_branch.txt` (after).

| metric | before (main build) | after (branch build) | expected | in the P3 report |
|---|--:|--:|---|---|
| merged sites whose point is (0, 0) | 29 | 0 | 0 (before 29) | yes: 29 Null Island sites |
| raw sites whose lat/lon is (0, 0) | 37 | 0 | 0 (before 37) | yes: 37 records |
| tie-break (168 listed): on the expected more precise point | 0 | 168 | 168 (before 0) | yes: 168 |
| Null Island (25 listed): now with no point | 0 | 25 | 25 (before 0) | yes: 25 |
| Null Island (4 listed): now on another member's point | 0 | 4 | 4 (before 0) | yes: 4 |
| merged sites total | 419,098 | 419,098 | unchanged (419,098) | report 05 |
| raw sites total | 679,778 | 679,778 | unchanged (679,778) | report 05 |
| merged sites with a coordinate | 400,446 | 400,421 | 400,421 (before 400,446; the 25 Null Island sites lose theirs) | new; the −25 matches |
| merged sites with a country | 402,429 | 402,429 | unchanged (402,429) | report 05 |
| merged sites with a state | 374,202 | 374,202 | unchanged (374,202); 221 lower if #110 is in the same build | report 05 |
| funnel 1: merged sites with >= 2 member records | 198,129 | 198,129 | unchanged (198,129) | yes |
| funnel 2: ... >= 2 members with a coordinate | 23,283 | 23,281 | 23,281 (before 23,283) | before: yes |
| funnel 2a: ... top score held by an expert/curator | 23 | 23 | unchanged (23) | yes |
| funnel 3: ... top score tied (system records) | 18,583 | 18,580 | 18,580 (before 18,583) | before: yes |
| funnel 3: ... tied, same source | 17,730 | 17,728 | 17,728 (before 17,730) | before: yes |
| funnel 3: ... tied, different sources | 853 | 852 | 852 (before 853) | before: yes |

## Mismatches

**None.**
- Every value that the P3 report gives matches.
- The funnel's "after" values (23,281 / 18,580 / 17,728 / 852) and the coordinate total (400,446 → 400,421) are not in the P3 report; they come from these loads.
  - The funnel moves slightly because the 37 (0, 0) records no longer count as having a coordinate.
- The #110 effect on the state row (−221) is from #110's own numbers. It was not measured in a combined build.

## Step 3: PR text

- **`PR_110_BODY.md`**, next to the existing draft `PR_KG.md` (there is no `p2/` folder):
  - 006 in place of 005;
  - "rebased on `63ab67e`";
  - the new suite numbers (133 / 24 and 176 / 24);
  - Deploy step 3 is now `migrations/apply_all.sh` before the new API starts;
  - a Merge order section;
  - an After deploy section: the read-only `psql` command for the existing `acceptance/problem2_state_country_conflict.sql` (0 after, 5,856 before on a local build), run before and after, `run_acceptance.sh` for the other counts, the `merge-v108` check, and the migration step with its `status.sql` row.
- **`p3/PR_111_BODY.md`**, from the live body (`p3/PR_P3.md` without its title line):
  - the numbers hold on `0c8b827` after the rebase;
  - the new suite numbers (133 / 24 and 160 / 24);
  - the old "whichever merges second moves to `merge-v109`" note is replaced by Merge order;
  - an After deploy section like #115's: the `psql` command, before and after, what `expected` covers, the `merge-v108` check, the #110 effect on states, and how it was tested.
- **Both bodies:** "#110 and #111 both use `merge-v108`, so build dev once, after both are merged. #115 uses `merge-v109`."
- The live PR bodies matched the drafts before these edits. Nothing was changed on GitHub.

## Push commands (not run)

Both branches were rebased, so the push must replace the PR heads. `--force-with-lease` names the current remote heads, so it refuses if anyone else has pushed since. Run from this folder (`data_issues`):

```bash
git -C ../ta2-minmod-kg-p2 push --force-with-lease=fix/p2-state-repair:61fda35 origin fix/p2-state-repair
git -C ../ta2-minmod-kg-p3 push --force-with-lease=fix/p3-null-island:a8f2596 origin fix/p3-null-island
```

Then paste `PR_110_BODY.md` into #110 and `p3/PR_111_BODY.md` into #111.

## Notes

- **Disk.** The first attempt at the branch load filled the Mac's disk: Docker's disk image grows and does not shrink when a database is dropped. The throwaway Postgres died, and `dentcloud-postgres` reported unhealthy. The first restart of Docker Desktop hadn't taken effect (its processes still dated from Oct 9), so I restarted it with `docker desktop restart`.
  - The second load used a small WAL and a guard that stops the load below 1.5 GB free.
  - After the restart, `dentcloud-postgres` came back healthy.
  - The throwaway container is removed.
- **Noticed, not changed:**
  - The README has a short note for each of migrations 003 to 005, but #110 adds none for 006. The Deploy step and `apply_all.sh` cover it.
  - #110's body still says to merge ta2-minmod-data#5 first. That PR is merged already (`0c8b827`).
- **Scratch:** the test runs, builds and logs were in the session's scratch directory and are deleted. No shared database was used.
