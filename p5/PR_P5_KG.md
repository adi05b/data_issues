Part of usc-isi-i2/ta2-minmod-data#6. **Merge the `ta2-minmod-data` PR "Commodity corrections list" first:** without `data/corrections/commodity.csv` this change does nothing.

# Apply commodity corrections when loading sites (Problem 5)

Branch `fix/p5-commodity-corrections` @ `3d1cdc0` (4 commits on `63ab67e`: `ee028a9` apply, `e549ec1` cache bump, `1198d04` tests, `3d1cdc0` acceptance query).

## What it does

- **Why:** these matches are made upstream.
  - ProcMine splits MRDS names such as `Sand and Gravel, Construction` at the comma and fuzzy-matches the half (`Construction` → Strontium at 0.5453).
  - Oregon's DOGAMI codes hit `commodity.csv`'s MRDS codes (`SC` = Scandium).
  - This PR applies the reviewed list as a fallback until the readers are fixed and the site JSON regenerated.

- **The ETL now reads the corrections list from the data repository** (`etl.yml`: `commodity_corrections: ::REPO::data/corrections/commodity.csv`).
- **Hook: `MergeFn.invoke` (`etl/mineral_site.py:449`).**
  - The list is applied to each raw site dict just before `MineralSiteAndInventory.from_raw_site`.
  - This is the one place the ETL reads a site's inventories ahead of both the kgrel views and the KG export, so the stored inventories, `mineral_inventory_view`, `dedup_mineral_inventory_view`, the KG triples, the dashboard counts and the CDR report all see the corrected value.
- **New `minmodkg/misc/commodity_corrections.py`:** reads the CSV once per process and file version, and refuses bad rows.
  - A row matches a matched candidate by record `source_id`, `observed_name` and an optional `context` (the record's own commodity text, e.g. `stone | crushed | SC`). Matching is exact.
  - `drop` removes the inventory.
  - `remap` sets `normalized_uri`, with confidence 1.0, and keeps `observed_name` and the matcher.
  - Unmatched candidates, and candidates already at the remap's target, are left alone.
- **Merge cache `merge-v107` → `merge-v109`.**
  - Not v108, because #110 and #111 both use v108.
  - The list's content hash is also in the merge cache key, so later edits to the list re-merge by themselves.
  - The export and entity caches don't need a bump: the export is keyed on the merged file's content.
- **Not changed: the API/editor and the GeoChem loader.** A curator's own edit stays as entered.
- **A missing or empty list changes nothing.** Verified byte for byte on all 2,446 merged files, with `PYTHONHASHSEED=0`. Main's own output is not byte-stable without a fixed seed, because view rows follow set order.

## Numbers (offline merge, all 679,778 records, main vs this branch on the data branch)

Measured before the rebase, on main `45a2a16`. #113 and #114 change no file on the merge path, so the numbers hold.

| defect | records | merged sites listing the wrong commodity |
|---|--:|--:|
| `Construction` → Strontium | 46,221 → 0 | Strontium 46,612 → **393** |
| Oregon `SC` → Scandium | 7,076 → 2 (left out) | 2,998 → 51 |
| Oregon `S` → Sulfur | 2,349 → 12 (11 left out + the sulfur mine) | 4,174 → 1,837 |
| `Construc` → Cobalt | 980 → 0 | 4,042 → 3,062 |
| Oregon `CS` → Cesium | 6 → 0 | 42 → 36 |
| Oregon `SD` → Sand | 41 → 0 | 688 → 647 |
| `Metal` → Nonmetal | 916 → 0 | 824 → 3 |

- 8 more rows (`Volcanic Materials`, `Water`, `Industrial`, `Soda Ash`, `Tripoli`, `Halloysite`, `Gilsonite`, and `Metal` for NC) go to 0.
- **Unintended changes: 0.**
  - No other candidate or site field changed.
  - No merged name, coordinate, country or state changed.
  - Every merged commodity removed is a corrected one, and every one added is a remap target.
- 0 merged sites are left with no commodity.
- **Grade/tonnage:**
  - The 2 dropped inventories with grade/tonnage duplicate the same record's Sand and Gravel row.
  - 10 merged sites move grade/tonnage from Nonmetal to Titanium > Metal, and 2 from Slate to Water.
- **Tests:** 25 new tests, also added to the CI Docker-free list. They pass on the fixture and on the data branch.
- **Full suite with Docker:** main `63ab67e` 133 passed / 24 failed; this branch 158 passed / the same 24 failed, with the same messages.
  - The 24 pre-existing failures: 16 need the `vendor/ta2-table-understanding` SHACL files (submodule not checked out), 4 are API tests, 3 backup-listener tests, and 1 is a mineral-site service test.
- `black` 25.9.0 `--check`: clean.

## After deploy

`acceptance/problem5_commodity_corrections.sql` is one read-only query that returns one row per metric (`metric`, `value`, `expected`):

```
PGOPTIONS='-c default_transaction_read_only=on' psql "$DATABASE_URL" -f acceptance/problem5_commodity_corrections.sql
```

- **Run it once before the deploy and once after.**
- **The `expected` column says what each row should show after the deploy**, with the value before it in brackets. It covers:
  - the 15 listed raw candidates (0, except the leftovers SC 2 and S 12);
  - merged sites listing each wrong commodity and each target;
  - totals that must not move;
  - the two keepers (Strontium Group, Last Chance Sulfur Mine).
- **The merge cache should be `merge-v109` (or later)** in the statickg workdir. If it isn't, the merge didn't re-run and nothing will have changed.
- **Tested on a local load of the full data** (Postgres 14, data `0c8b827`). Main's build gives every "before" value and this branch's build every "expected" value, in about 4 s each. It also runs on the repo's own Postgres image (17.11).
- **If anything is off, empty the corrections list** (keep its header row). The next rebuild restores today's state: the list's content is part of the merge cache key, so the merge re-runs by itself, and an empty list gives output byte-for-byte the same as main's (all 2,446 merged files, `PYTHONHASHSEED=0`).

## Decided defaults

- **`Metal` → Q674 Titanium > Metal.** Its grade rows are MRDS's own `Titanium, Metal` row (code `TI_M`).
- **`Water` → Q680 Water.** MRDS writes `Water, Free` (code `H2O`). The rare-earth rows on those records copy Water's grade, not the reverse; they are phantoms of "Free".

## Defaults you may want to change

- **Oregon: remap rather than drop.** `SC`/`CS` → Stone > Crushed/Broken, `SD` → Stone > Dimension, and `S` is dropped next to Sand and Gravel. A drop of `SC`/`CS`/`SD` would keep only `Stone`.
- **API edits are not corrected.** A site created or edited through the API keeps the candidate it was sent. Today no user-owned copy of a listed record exists in the data repository.
