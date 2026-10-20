# Apply commodity corrections when loading sites (Problem 5)

Branch `fix/p5-commodity-corrections` @ `3766487` (3 commits on `45a2a16`).

**Merge the `ta2-minmod-data` PR "Commodity corrections list" first.** Without `data/corrections/commodity.csv` this change does nothing.

## What it does

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
  - 10 merged sites move grade/tonnage from Nonmetal to Metal, and 2 from Slate to Water.
- **Tests:** 25 new tests, also added to the CI Docker-free list. Full suite with Docker: main 80 passed / 23 failed; this branch 105 passed / the same 23 failed.

## Defaults you may want to change

- **`Metal` → Q628 Metal.** All 21 `Metal` grade rows copy the record's Titanium row, so those 10 merged sites show Titanium's numbers as Metal. Q674 Titanium > Metal is the alternative.
- **`Water` → Q680 Water.** Its grade rows copy a rare-earth row (2 merged sites). A drop loses nothing unique.
- **Oregon: remap rather than drop.** `SC`/`CS` → Stone > Crushed/Broken, `SD` → Stone > Dimension, and `S` is dropped next to Sand and Gravel. A drop of `SC`/`CS`/`SD` would keep only `Stone`.
- **API edits are not corrected.** A site created or edited through the API keeps the candidate it was sent. Today no user-owned copy of a listed record exists in the data repository.
