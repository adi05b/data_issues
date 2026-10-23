# Report 05: Problem 5 acceptance query

*2026-10-23. Read-only throughout. Committed locally to the kg branch; nothing pushed, no PR opened. No live graph, Postgres or API touched.*

## What was added

- **`acceptance/problem5_commodity_corrections.sql`** on `fix/p5-commodity-corrections`, commit `3d1cdc0` "Acceptance query for commodity corrections (Problem 5)". It sits on `1198d04`; the branch is now 4 commits on `63ab67e`.
- **The header** says, like the P1, P2 and P4 files:
  - what it checks, how to run it, and that it is read-only;
  - where the expected numbers come from (`0c8b827` plus the list), and that newer data may drift a little;
  - that a merge cache other than `merge-v109` (or later) means the merge didn't re-run and nothing will have changed.
- **One query, 33 rows** of `metric`, `value`, `expected` (the after value, with the before value in brackets):
  1. **15 raw rows**, one per list row: records whose stored candidate (`mineral_site.inventories`) still has the listed source, observed name and wrong QID. The Oregon rows count any context, so the leftovers show: SC 2, S 12.
  2. **7 rows**: merged sites listing each wrong commodity (`dedup_mineral_inventory_view`).
  3. **4 rows**: merged sites listing each target (Q664, Q665, Q674, Q680).
  4. **5 sanity rows**: merged sites total, raw sites total, merged sites with a country (`country_val`), with a state (`state_or_province_val`), and with no commodity.
  5. **2 keepers**: MRDS `10186268` Strontium Group still lists Strontium, and Oregon `ID_04514` Last Chance Sulfur Mine still lists Sulfur.
- **Only kgrel's real tables and columns** (checked in `minmodkg/models/kgrel/`): `mineral_site` (`site_id`, `source_id`, `dedup_site_id`, `inventories`), `dedup_mineral_site` (`id`, `country_val`, `state_or_province_val`) and `dedup_mineral_inventory_view` (`commodity`, `dedup_site_id`). `inventories` is bytea holding orjson, read with `convert_from(…, 'UTF8')::jsonb` as `problem1_latitude_range.sql` does.
- **`run_acceptance.sh` is not touched** (identical to main), so the file doesn't conflict with #110.

## Where it ran

- **Full data, before/after.** A throwaway local PostgreSQL 14.18 (Homebrew) cluster in the scratchpad, on loopback only. It is the same kind of setup as P3's `amandeep_sql_local.txt`: tables created by MinMod's own SQLAlchemy models, loaded from an offline merge run by `p5/p5_load_kgrel.py`. That script is adapted from P3's loader and also builds the merged-site commodity rows with `from_dedup_sites`, as `prep_kgrel_input` does.

  | database | built from | records | merged sites | merged commodity rows | record commodity rows |
  |---|---|--:|--:|--:|--:|
  | `kgrel_main` | `p5/run-main0`: main merge code (`45a2a16`), data `0c8b827`, `merge-v107` | 679,778 | 419,098 | 702,056 | 1,119,946 |
  | `kgrel_fix` | `p5/run-fix0`: branch merge code + data branch `7ae473f`, `merge-v109` | 679,778 | 419,098 | 651,545 | 1,070,388 |

  - Both runs were built before the rebase. The branch's diff is identical after it, and #113/#114 change no file on the merge path, so the builds stand for `63ab67e` / `1198d04`.
  - Entity tables are not loaded; the query doesn't read them.
  - Run with `PGOPTIONS='-c default_transaction_read_only=on'`: 4.2 s on `kgrel_main`, 4.4 s on `kgrel_fix`.
- **Parses on dev's Postgres version.** The repo's own Postgres image (`3b61d2d28efd`, PostgreSQL 17.11), with an empty schema from the same models, read-only: all 33 rows come back, as zeros (`p5/out/p5_acceptance_pg17_empty.txt`).

## Before / after (full data)

Raw outputs: `p5/out/p5_acceptance_kgrel_main.txt` (before) and `p5/out/p5_acceptance_kgrel_fix.txt` (after). In this table, `|` inside the expected text is shown as `/`.

| metric | before (main build) | after (branch build) | expected | match |
|---|--:|--:|---|---|
| raw: MRDS Construction -> Strontium | 46,221 | 0 | 0 (before 46,221) | yes |
| raw: MRDS Metal -> Nonmetal | 840 | 0 | 0 (before 840) | yes |
| raw: MRDS Water -> Slate | 221 | 0 | 0 (before 221) | yes |
| raw: MRDS Volcanic Materials -> Clay > Bloating Material | 487 | 0 | 0 (before 487) | yes |
| raw: MRDS Industrial -> Indium | 11 | 0 | 0 (before 11) | yes |
| raw: MRDS Soda Ash -> Ash | 8 | 0 | 0 (before 8) | yes |
| raw: MRDS Tripoli -> Lithium | 1 | 0 | 0 (before 1) | yes |
| raw: MRDS Gilsonite -> Wollastonite | 1 | 0 | 0 (before 1) | yes |
| raw: NC Construc -> Cobalt | 980 | 0 | 0 (before 980) | yes |
| raw: NC Metal -> Nonmetal | 76 | 0 | 0 (before 76) | yes |
| raw: NC Halloysite -> Alunite | 1 | 0 | 0 (before 1) | yes |
| raw: Oregon SC -> Scandium | 7,076 | 2 | 2 (before 7,076; left: sand and gravel / SC) | yes |
| raw: Oregon S -> Sulfur | 2,349 | 12 | 12 (before 2,349; left: 11 stone / crushed / S / G + Last Chance) | yes |
| raw: Oregon CS -> Cesium | 6 | 0 | 0 (before 6) | yes |
| raw: Oregon SD -> Sand | 41 | 0 | 0 (before 41) | yes |
| merged sites listing Strontium (Q609) | 46,612 | 393 | 393 (before 46,612) | yes |
| merged sites listing Scandium (Q607) | 2,998 | 51 | 51 (before 2,998) | yes |
| merged sites listing Sulfur (Q633) | 4,174 | 1,837 | 1,837 (before 4,174) | yes |
| merged sites listing Cobalt (Q537) | 4,042 | 3,062 | 3,062 (before 4,042) | yes |
| merged sites listing Cesium (Q591) | 42 | 36 | 36 (before 42) | yes |
| merged sites listing Sand (Q655) | 688 | 647 | 647 (before 688) | yes |
| merged sites listing Nonmetal (Q581) | 824 | 3 | 3 (before 824) | yes |
| merged sites listing Stone > Crushed/Broken (Q664) | 17,689 | 20,643 | 20,643 (before 17,689) | yes |
| merged sites listing Stone > Dimension (Q665) | 344 | 385 | 385 (before 344) | yes |
| merged sites listing Titanium > Metal (Q674) | 774 | 821 | 821 (before 774) | yes |
| merged sites listing Water (Q680) | 1 | 221 | 221 (before 1) | yes |
| merged sites total | 419,098 | 419,098 | unchanged (419,098) | yes |
| raw sites total | 679,778 | 679,778 | unchanged (679,778) | yes |
| merged sites with a country | 402,429 | 402,429 | unchanged (402,429) | yes |
| merged sites with a state | 374,202 | 374,202 | unchanged (374,202) | yes |
| merged sites with no commodity | 44,884 | 44,884 | must not go up (44,884) | yes |
| keeper: MRDS 10186268 Strontium Group still lists Strontium | 1 | 1 | 1 | yes |
| keeper: Oregon ID_04514 Last Chance Sulfur Mine still lists Sulfur | 1 | 1 | 1 | yes |

## Mismatches

**None.**
- Every "after" value equals report 02's after number.
- Every "before" value equals report 02's before number (31 of 31 checked).
- The 5 sanity rows and 2 keepers are identical in both builds.
- The 7 rows of report 02's defect table (records 46,221 / 7,076 / 2,349 / 980 / 6 / 41 / 916) reproduce here as the raw rows. `Metal` is split by source, 840 + 76.

## Notes

- **The sanity values** (402,429 / 374,202 / 44,884) were not in report 02. They come from this load, and are the same in both builds.
- **For Amandeep, `p5/PR_P5_KG.md` now has an "After deploy" section:**
  - the `psql` command;
  - run once before the deploy and once after;
  - the `expected` column;
  - the `merge-v109` check;
  - the rollback: empty the list and rebuild. The list's content is in the merge cache key, so the merge re-runs by itself, and an empty list gives output byte-for-byte the same as main's.
- **Throwaway resources:** the local cluster is stopped and the PostgreSQL 17 container is removed. No shared database was used.
