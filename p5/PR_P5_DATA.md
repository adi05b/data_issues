# Commodity corrections list (Problem 5)

Branch `adi05b/ta2-minmod-data` `p5-commodity-corrections` @ `5dcac22` (1 commit on `0c8b827`). Adds one file: `data/corrections/commodity.csv`.

**Merge this before the `ta2-minmod-kg` PR "Apply commodity corrections when loading sites".** Without this file the kg change does nothing.

## What it is

- **A reviewed list of known wrong commodity matches in the site JSON**, and what kg should do with each one at load time.
- **Columns:** `source_id, observed_name, context, action, normalized_uri, note`.
  - A row matches a *matched* commodity candidate: same record `source_id`, same `observed_name`, and either an empty `context` or a `context` equal to the record's own commodity text (its observed names in order, joined by ` | `).
  - Matching is exact.
  - `drop` removes the inventory.
  - `remap` sets `normalized_uri` to the row's QID with confidence 1.0, and keeps `observed_name` and the matcher.
- **Why `data/corrections/` and not `data/entities/`:** `data/entities/` holds the Q-id entity tables, and kg's filename check globs `data/entities/*.csv`. Nothing reads `data/corrections/`.
- CRLF line endings, like the entity tables.

## The 15 rows

| source | observed | context | action | target | records |
|---|---|---|---|---|--:|
| mrds | `Construction` | | drop | | 46,221 |
| mrds | `Industrial` | | drop | | 11 |
| mrds | `Soda Ash` | | drop | | 8 |
| mrds | `Tripoli` | | drop | | 1 |
| mrds | `Metal` | | remap | Q628 Metal | 840 |
| mrds | `Volcanic Materials` | | remap | Q679 Volcanic Materials | 487 |
| mrds | `Water` | | remap | Q680 Water | 221 |
| mrds | `Gilsonite` | | remap | Q649 Petroleum (Oil) > Gilsonite | 1 |
| NC Geological Survey | `Construc` | | drop | | 980 |
| NC Geological Survey | `Halloysite` | | drop | | 1 |
| NC Geological Survey | `Metal` | | remap | Q628 Metal | 76 |
| Oregon DOGAMI | `SC` | `stone \| crushed \| SC` | remap | Q664 Stone > Crushed/Broken | 7,074 |
| Oregon DOGAMI | `CS` | `stone \| crushed \| CS` | remap | Q664 Stone > Crushed/Broken | 6 |
| Oregon DOGAMI | `SD` | `stone \| dimension \| SD` | remap | Q665 Stone > Dimension | 41 |
| Oregon DOGAMI | `S` | `sand and gravel \| S \| G` | drop | | 2,337 |

## How the rows were chosen

- **Every row is a match the Problem 5 investigation judged wrong**, against today's data (`0c8b827`).
- **`drop`** is used only where every record already carries the commodity the string stands for:
  - `Construction` and `Construc`: all 47,201 records also have Sand and Gravel.
  - Oregon `S`: the record has `sand and gravel` and `G`.
  - `Industrial`: Sand and Gravel. `Soda Ash`: Sodium. `Tripoli`: Silica. `Halloysite`: Clay.
- **`remap`** is used only where the target is a fact:
  - Oregon's own record text gives `stone | crushed` and `stone | dimension`.
  - `Metal`, `Volcanic Materials` and `Water`: the matcher's commodity table lacked Q628, Q679 and Q680, which `commodity.csv` has.
  - `Gilsonite`: `commodity.csv` has an entity of that name.
- **Left out on purpose:**
  - 11 Oregon `stone | crushed | S | G` and 2 `sand and gravel | SC`: they can't be decoded from the record.
  - The Last Chance Sulfur Mine (`ID_04514`, `sulfur and pyrite | S`): S really is sulfur.
  - 8 mineral names judged wrong (Galena, Chalcopyrite, Hematite, Apatite, Monazite, Sillimanite, Tourmaline, Vesuvianite; 25 records). The string is the record's own information, and `commodity.csv` has no matching entity.
- **Checked** with the kg tests, run on this branch (`MINMOD_DATA_DIR=<checkout>/data`): every remap target is in `commodity.csv`, and no row matches the sulfur mine.

## Open questions

- **`Metal`:** Q628 Metal or Q674 Titanium > Metal?
  - All 916 `Metal` records also carry Titanium.
  - Their 21 grade rows copy the Titanium row, so with Q628, 10 merged sites show Titanium's grade/tonnage as Metal.
- **`Water`:** remap to Q680 or drop?
  - Its 45 grade rows copy a rare-earth row.
  - Every Water record has other commodities, so a drop would lose nothing unique.
- **Oregon:** remap `SC`/`CS`/`SD` to the stone subtypes, or drop them (every record keeps `Stone`)?
- **DOGAMI's code book**, to decode the 13 records left out.
