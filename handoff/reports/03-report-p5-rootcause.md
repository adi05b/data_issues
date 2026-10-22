# Report 03: Problem 5, where the wrong commodities come from

*2026-10-22. Part A and Part B are read-only. Nothing in ProcMine, `ta2-minmod-data` or `ta2-minmod-kg` was changed, apart from the two list rows in Part C (local, not pushed). No graph, Postgres or API was touched. Raw sources were downloaded outside `data_issues`, into a `p5_sources/` folder beside it. Only short excerpts are quoted here. Every claim is marked **verified** (seen in data or code) or **hypothesis**.*

## Summary

**`Construction` is never a commodity in any source.** It is half of one commodity name.
- **MRDS:** MRDS writes a commodity with its subtype as one name, `Sand and Gravel, Construction` (code `SDG`). ProcMine splits every commodity string on commas. The second half becomes a candidate of its own, and fuzzy matching with no minimum score sends it to Strontium.
- **NC:** NC copied those MRDS names, cut to 25 characters, so the same split leaves `Construc`, which the matcher sends to Cobalt.
- **Oregon:** the codes come from a column of their own, `CommodityAbbreviation`. The older UMN reader read it as commodity names, and DOGAMI's codes are exact keys in MinMod's commodity table, where the MRDS codes and element symbols live (`SC` = Scandium's `mrds_code`).

**The split causes more than the list fixes:**
- 39 MRDS names of the form "Parent, Subtype" are broken on 71,281 records. On 53,135 of them the lone subtype lands on a different parent's entity.
- The same ProcMine step rewrites `Water, Free` into Water + 15 phantom rare earths (221 records).

## Part A: from the source to the candidate

Sources (all verified):
- **MRDS:** the comprehensive download `rdbms-tab-all.zip` (tables dated 2019-03-06) and the flattened `mrds-csv.zip` (`mrds.csv`, dated 2022-08-23) from mrdata.usgs.gov/mrds.
  - UMN's archived raw input (`DARPA-CRITICALMAAS/ta2-minmod-data-archive`, `data/umn/raw_databases/MRDS.csv`, commit `1091fab`, an LFS pointer) has sha256 `ac1b70dc…53e37`, byte-identical to today's `mrds.csv`.
  - ProcMine's own `sample_mapfile.csv` is an MRDS map: `commodity ← Commodity.commod` (line 7) and `Resource_detail.commod` (line 6), `grade ← Resource_detail.grd` (line 15).
- **NC:** the NC DEQ service `DEMLR/NC_MRDS`, MapServer layer 2 "Location point" (6,538 points, fetched 2026-10-22). The service the search engines list, `North_Carolina_Mineral_Resource_Data_System`, now returns 404.
- **Oregon:** DOGAMI MILO-4, `Public/MILO`, MapServer layer 1 "MILO Points" (24,664 points, fetched 2026-10-22), and its layer metadata.

ProcMine is `umn-ta2-database-processing` @ `ce1ed70`. `DARPA-CRITICALMAAS` and `usc-isi-i2` point to the same repo.

### MRDS `Construction` (46,221 records)

| step | value | where | |
|---|---|---|---|
| raw (comprehensive) | `Commodity.txt`: `10004382 · 1 · "Sand and Gravel, Construction" · "SDG" · group "Sand and Gravel" · Primary`. **One row = one commodity**; the comma is part of the name | USGS `Commodity.txt`; schema "COMMOD: Name of the commodity", "CODE: Distinct abbreviated code" | verified |
| raw (flattened) | `mrds.csv` `commod1` = `Sand and Gravel, Construction`; `10115528` `commod3` = `Gold, Hafnium, Iron, Sand and Gravel, Construction` | MRDS defines `commod1..3` as "a comma-separated list", so the list separator and the name's own comma are the same character | verified |
| title-case | `Sand And Gravel, Construction` | `procmine/converting/_attribute.py:74` | verified |
| REE/PGE replace | no change here (but see `Water, Free` in Part B) | `_procmine.py:210-212` | verified |
| split | `Sand And Gravel` · `Construction` | `_procmine.py:215-218`, regex `\s*[\|,;]\s*` | verified |
| match `Construction` | no exact key, so fuzzy against all 438 keys of ProcMine's table, **no minimum score**. Best: key `strontium` 0.5453 (next `co` 0.4860, `stone` 0.4356) → **Q609 Strontium** | `converting/_entity.py:46` (start 0.0001), `:59-92` (mean of 6 similarities, highest wins) | verified: re-run with ProcMine's pinned strsimpy 0.2.1 gives 0.5453, the JSON's value |
| match `Sand And Gravel` | exact key `sand and gravel` → Q656 at 0.9999 | `_entity.py:54-56` | verified |
| grade/tonnage | `Resource_detail`: `10115528 · SDG · "Sand and Gravel, Construction" · grd 65 wt-pct`. The split hands that one row's grade to both pieces | `_procmine.py:100-144` joins the commodity columns, then the same split | verified (both JSON inventories carry 65 % and 1.92 Mt) |

**Scale (verified).** For **all 304,638** MRDS records, ProcMine's steps run on `Commodity.commod` + `Resource_detail.commod` give exactly the observed names in the site JSON (`p5_rootcause_mrds.py`). `Sand and Gravel, Construction` is on exactly 46,221 records, the `Construction` count.

**Samples** (`data/mineral-sites/umn/mrdata_mrds/`):

| file | record_id | source rows (`Commodity.commod [code]`) | JSON `commodity` (observed → QID, confidence, matcher) |
|---|---|---|---|
| `b000.json` | `10004382` Portaluppi and Vita Pits | `Sand and Gravel, Construction [SDG]` | `Sand And Gravel` → Q656 0.9999; `Construction` → Q609 0.5453; both `UMN Matching System-ProcMinev2` |
| `b009.json` | `10115528` Pacoima Canyon Placers | `Gold [AU]`, `Hafnium [HF]`, `Iron [FE]`, `Sand and Gravel, Construction [SDG]`, `Zirconium [ZR]`, `Titanium [TI]` | as the rows, plus `Construction` → Q609 carrying `Resource_detail`'s 65 % and 1.92 Mt |
| `b014.json` | `10186268` Strontium Group | `Gypsum-Anhydrite [GYP]`, `Sand and Gravel, Construction [SDG]`, `Flagstone [STN_F]`, `Strontium [SR]` | `Construction` → Q609 0.5453 **and** a genuine `Strontium` → Q609 0.9999 |

No other field holds the original text. MRDS records have no `deposit_type_candidate`, and `name` is the site name.

### NC Geological Survey `Construc` (980 records)

| step | value | where | |
|---|---|---|---|
| raw | `MajorCommodity` = `Sand and Gravel, Construc` (NCGS_ID 1886, OBJECTID 1495) | NC_MRDS layer 2; the field is `esriFieldTypeString` 150 | verified |
| the cut | `Sand and Gravel, Construc` is exactly 25 characters. In today's service, 918 `MajorCommodity` values have length 25, against 2 at 24 and 2 at 26. The cut also appears inside longer lists (`Clay, Sand and Gravel, Construc`), and the only other cut name is `Aluminum, Contained or Me` (MRDS's `Aluminum, Contained or Metal`, also 25) | `p5_rootcause_nc.py` | **verified** that the source already holds the cut text. **Hypothesis:** each MRDS commodity *name* was stored at most 25 characters wide somewhere upstream of NC's database. Today's 150-character field doesn't cause it |
| title-case, join | `Major; Minor; Trace` joined with `"; "` | `_attribute.py:74, 77-89` | verified |
| split | `Sand And Gravel` · `Construc` | `_procmine.py:215-218` | verified |
| match `Construc` | fuzzy, best key **`co`** (Cobalt's alias `Co`) 0.5368 → **Q537 Cobalt** | `_entity.py:59-92` | verified (re-run gives 0.5368) |
| deposit type | `DepositType` `Sedimentary` + `" "` + commodity → `Sedimentary Sand And Gravel` · `Construc`: the raw comma survives in NC's deposit-type candidates | `_procmine.py:157-164`, then the same split | verified on 711 of 773 records with a deposit type. The other 62 keep the two strings apart |

**Scale (verified).** 6,535 of the 6,538 records in today's service rebuild exactly. The other 3 differ by a leading space, the typo `Unkown` and a number. The other **470 JSON records are not in today's service**, so those can't be traced here.

**Samples** (`umn/nc_geological_survey/`):

| file | record_id | source `MajorCommodity` (`DepositType`) | JSON |
|---|---|---|---|
| `b000.json` | `1886` Delbert E Barefoot Pit | `Sand and Gravel, Construc` | `Construc` → Q537 0.5368; `Sand And Gravel` → Q656 0.9999 |
| `b000.json` | `787` Harrison Pit | `Sand and Gravel, Construc` (`Sedimentary`) | same, plus deposit types `Sedimentary Sand And Gravel` and `Construc` |
| `b062.json` | `3008` Tunis Pit | `Clay, Sand and Gravel, Construc` | `Clay` → Q521; `Sand And Gravel` → Q656; `Construc` → Q537 |

### Oregon DOGAMI `SC` / `S` / `CS` / `SD` (9,472 inventories)

| step | value | where | |
|---|---|---|---|
| raw | `Commodity` = `stone, crushed`, `Type` = `aggregate`, **`CommodityAbbreviation` = `SC`** (ID_05048). The code has **its own column** | MILO-4 layer 1. Metadata: Commodity is "a comma separated list"; CommodityAbbreviation is "Commodity abbreviation for major commodities present, a 'space' separated list" | verified |
| the codes in MILO-4 | `SC` next to `stone, crushed` 7,686 times (`sand and gravel` 2). `SD` next to `stone, dimension` 58. `CS` next to `stone, crushed` 8. **`S&G`** next to `sand and gravel` 2,455 and `stone, crushed` 15. `S` alone next to `sulfur and pyrite` once | `p5_rootcause_oregon.py` | verified. **No official DOGAMI code list was found**: not in the layer metadata, the MILO-3 or MILO-4 release pages, or any repo. The MILO-4 pamphlet (60 pages) could not be text-searched here |
| reader | not ProcMinev2: these candidates are labelled `UMN Matching System v1` (modified 2024-10-26, before ProcMinev2). No public repo or commit contains that label | GitHub code search; ProcMine history | verified that the code is unavailable |
| what the output proves | the observed names are `Commodity` split on commas, plus `CommodityAbbreviation` split on **`&`**, with a later piece dropped when it exactly matches an entity an earlier piece has. This rebuilds **22,479 of 23,306** records in order, and **9,450 of the 9,471** records with a code defect. The rest differ by wording between releases (`gemstone material` vs `gem materials`) | `p5_rootcause_oregon.py` | **hypothesis** (inferred from input and output). ProcMinev2's rule (no `&` split) rebuilds only 14,824 |
| match | exact, case-insensitive key: `sc` → Q607 (Scandium's `mrds_code` and alias `Sc`); `sd` → **Q655 Sand, whose only key is `mrds_code`**; `cs` → Q591 (`mrds_code`, alias `Cs`); `s` → Q633 (`mrds_code`, alias `S`); `g` → no key, so 0.001 | `data/entities/commodity.csv` | verified that these keys exist. **Hypothesis:** v1 used an exact lookup on these columns; `SD` can only have matched through `mrds_code` |

**Samples** (`umn/oregon_department_geology_mineral_industries/`):

| file | MILO_ID | MILO-4 `Commodity` · `CommodityAbbreviation` | JSON (all `UMN Matching System v1`) |
|---|---|---|---|
| `b000.json` | `ID_05048` quarry | `stone, crushed` · `SC` | `stone` → Q663 1.0; `crushed` → none 0.001; `SC` → Q607 1.0 |
| `b000.json` | `ID_06010` gravel pit | `sand and gravel` · `S&G` | `sand and gravel` → Q656 1.0; `S` → Q633 1.0; `G` → none 0.001 |
| `b001.json` | `ID_03975` G.Heden No.5,6,7,8 | `stone, dimension` · `SD` | `stone` → Q663; `dimension` → none; `SD` → Q655 1.0 |

The leftovers decode in MILO-4 too:
- the 11 `stone | crushed | S | G` are `stone, crushed` · `S&G` (e.g. `ID_20680`);
- the 2 `sand and gravel | SC` are `sand and gravel` · `SC` (`ID_23259`);
- the Last Chance Sulfur Mine is `sulfur and pyrite` · `S`.

In the first two kinds, the source's own code and text disagree. Oregon records keep no other field with the raw text: `deposit_type_candidate` holds MILO's `DepositType`.

## Answers to Amandeep

- **MRDS:** from a **table**: the `COMMOD` field of MRDS's Commodity table (one row per commodity, e.g. `Sand and Gravel, Construction`, code `SDG`), also written comma-joined in `mrds.csv` `commod1..3`. **ProcMine's comma split** (`_procmine.py:215-218`) made `Construction` a candidate. Its fuzzy matcher with no minimum (`_entity.py:59-92`) made it Strontium.
- **NC:** from a **table**: the `MajorCommodity` field of NC DEQ's NC_MRDS layer, which already holds the MRDS name cut to 25 characters (`Sand and Gravel, Construc`). The **same ProcMine comma split** made `Construc` a candidate, and the same fuzzy matcher made it Cobalt (via the key `co`).
- **Oregon:** from a **table**: MILO's separate **`CommodityAbbreviation` column** (`SC`, `SD`, `CS`, `S&G`). The **older UMN reader (v1, code not public)** read that column as commodity names and split `S&G` at `&`. An exact lookup on MinMod's `mrds_code`/alias keys turned DOGAMI's codes into Scandium, Sand, Cesium and Sulfur.

**None of it is free text or a document section.**

## Part B: where a root fix could go (proposal only)

Counts are offline, against the site JSON at `0c8b827` and the data branch's list (`7ae473f`). A "pair" is one (record, commodity) pair. "Root" means a reader that keeps each source commodity whole and maps it by code.

**MRDS** (304,544 records with commodities)

| option | where it would change | what changes | records |
|---|---|---|--:|
| **M1. Keep each MRDS commodity row whole; map it by its MRDS code via `commodity.csv`'s `mrds_code`; replace REE/PGE only when the whole value is `REE`/`PGE`** | ProcMine's MRDS reading: `_procmine.py:215-218` (no comma split inside one `COMMOD`), `:210-212` (whole-value replace), and a code lookup instead of `entity2id` (`_entity.py`) for sources that have codes | matched commodities change on **72,536** records. On **46,345** of them the list already gives the same result. Root-only changes: | |
| | | · wrong matches the list doesn't know about: Clay > General 3,426 (`Limestone, General`); Limestone > Dimension 2,404 (Stone/Marble/Slate/Granite/Sandstone `, Dimension`); Alunite 450 (Halite); Aluminum 450 (Salt); Mineral Pigments 65 (`Titanium, Pigment`); Gold > Refinery 64 (Zinc/Lead/Nickel/Silver/Tungsten refiners); Emerald 49 (Emery); Lead > Smelter 10; Chlorine 3 | **6,823** |
| | | · 15 phantom rare earths from `Water, Free` | **221** (3,315 pairs) |
| | | · a parent next to its own subtype goes (Stone beside Stone > Crushed/Broken, etc.). This is a policy choice, not an error | 20,987 |
| | | · **cost:** 15 codes have no `mrds_code` row in `commodity.csv` (e.g. `NA_SS` 40, `NA_SC` 30, `K_P` 19, `SDG_FRAC` 14, `SIL_SDG` 11); their 161 candidates would be lost unless rows are added | 101 |
| M2. Regenerate `umn/mrdata_mrds` (64 files) with M1 | `ta2-minmod-data` | as M1. Each grade/tonnage row also stays with its own commodity | 304,638 |
| M3. The corrections list (built) | — | 47,789 wrong pairs removed and 1,549 added (`Construction`, `Metal`, `Industrial`, `Soda Ash`, `Tripoli`, `Water`, `Volcanic Materials`, `Gilsonite`) | 47,768 |

**A plain ProcMine re-run fixes nothing for MRDS.** The split (`_procmine.py:217`) and the no-minimum matcher are unchanged, so it reproduces `Construction` → Strontium.

**NC** (6,538 records in today's service; 470 more in the JSON only)

| option | where | what changes | records |
|---|---|---|--:|
| **N1. Rejoin `Parent, Subtype` when MRDS has that name before splitting; repair the two 25-character cuts; map by MRDS code** | ProcMine's NC reading (map file + `_procmine.py:215-218`) | matched commodities change on **1,284**; the list already gives the same on 920. Root-only: Limestone > Dimension 52, Clay > General 19, Vermiculite 1; 318 parent-next-to-subtype pairs | 1,284 |
| N2. Regenerate `umn/nc_geological_survey` with N1 | `ta2-minmod-data` | as N1. The 470 records not in today's service would need NC's older extract, or would drop out | 7,008 |
| N3. Ask NC DEQ to restore the full names | NC's database | removes the cut at its origin: 921 + 1 records | 922 |
| N4. The corrections list | — | `Construc` 980, `Metal` 76, `Halloysite` 1 | 1,057 |

**Oregon** (23,316 records)

| option | where | what changes | records |
|---|---|---|--:|
| O1. Don't read `CommodityAbbreviation` as commodity names | the Oregon reader (v1 or a new ProcMine map) | removes all 9,472 code collisions, including the 13 leftovers. **Cost:** the column also holds material words (coal 337, limestone 190, `Mn` 132, diatomite 127, clay 101, …), so **945** records would lose their only matched commodity, the Last Chance Sulfur Mine among them | 9,472 fixed / 945 lost |
| **O2. Read `CommodityAbbreviation` with DOGAMI's code list:** `S&G` whole → Sand and Gravel, `SC`/`CS` → Stone > Crushed/Broken, `SD` → Stone > Dimension, element symbols as symbols, other words as now | same | fixes all 9,472 without the 945 loss. **Needs DOGAMI's list (not found).** A list inferred from MILO-4 co-occurrence is possible but not official | 9,472 |
| O3. Keep `stone, crushed` / `stone, dimension` whole | same | Q664 / Q665 instead of `Stone` + an unmatched `crushed`/`dimension` | 8,278 + 57 |
| O4. Regenerate the Oregon files from MILO-4 | `ta2-minmod-data` | as O2 + O3, but MILO-4 has 24,664 points against 23,316 in the JSON (10 JSON ids are gone), so the record set changes too | 24,664 |
| O5. The corrections list | — | `SC` 7,074, `CS` 6, `SD` 41, `S` 2,337 | 9,458 |

**A re-run of today's ProcMinev2 on Oregon wouldn't fix it either.**
- Its keys still include `mrds_code` and aliases, so `SC`/`SD`/`CS`/`S` would match exactly at 0.9999 (re-run of its matcher, `p5_procmine_match.py`).
- Only `S&G` would change: it stays whole and fuzzy-matches `sdg` → Sand and Gravel at 0.4667.

**Does the same split or cut hit more than the list? Yes:**
- **MRDS:**
  - 39 commodity names contain a comma, on 71,281 records.
  - On **53,135** records the lone subtype lands on another entity. The list covers `Construction` 46,221, `Metal` 840 and Water's own match (221). The other **5,906** (`Limestone, General`, the five `, Dimension` names, `Titanium, Pigment`, the refiners and smelters) are not in the list; they are part of M1's root-only rows.
  - On 18,739 records it lands on the right subtype by luck (`Stone, Crushed/Broken` → Stone > Crushed/Broken), and 48 have no MinMod entity.
  - The case-insensitive `REE`/`PGE` replacement hits only `Water, Free`: 221 records, 3,315 phantom pairs including `FLanthanum`.
- **NC:**
  - 1,290 records in today's service carry an MRDS compound name: 921 the cut `Construc`, then `Stone, Crushed/Broken` 205, `Titanium, Metal` 72, `Stone, Dimension` 25, `Marble, Dimension` 23, `Limestone, General` 19, `Iron, Pig Iron` 16 and others.
  - Only 2 names are cut, `Construc` (921) and `Contained or Me` (1).
- **Oregon:** 8,278 + 57 records have `stone, crushed` / `stone, dimension` split, and every `S&G` (2,475 records in MILO-4) is split into `S` + `G`.

## Recommendation

- **Fix the readers, then regenerate the three sources' site JSON. Keep the corrections list as the fallback until then.**
  - **MRDS and NC:** keep each commodity name whole and map it by MRDS code (M1/N1). That alone removes `Construction`, `Construc`, `Metal`, the 6,823 + 72 wrong subtype matches the list doesn't know about, and the 221 phantom rare-earth sets. Add `commodity.csv` rows for the 15 unmapped codes first.
  - **Oregon:** read `CommodityAbbreviation` with DOGAMI's own code list (O2). Ask DOGAMI for that list rather than inferring it.
- A plain ProcMine re-run would reproduce all three defects, so it is not a fix on its own.

## Part C: the two list rows (local)

- **`Metal` (mrds and NC Geological Survey) → Q674 Titanium > Metal. Done.**
  - Q674 exists (`commodity.csv`: `Q674,Titanium > Metal,Q614,…,TI_M`).
  - Its note now gives the cause: MRDS writes `Titanium, Metal` (code `TI_M`), and Q674 is that code's entity.
- **`Water`: not changed to drop. Your decision, after this report's finding.**
  - The facts: MRDS writes `Water, Free` (code `H2O`), and none of the 221 Water records has a real REE row, so the 15 rare earths on each are phantoms of "Free".
  - Their grade rows copy Water's, not the other way round: all 46 graded rows are `Water, Free` in `Resource_detail`.
  - 7 records have `Water, Free` as their only MRDS commodity.
  - So the row stays a remap to Q680. Its note now says MRDS writes `Water, Free` (code `H2O`) and Q680 is that code's entity.
  - The list can't remove the 14 phantom names other than `FLanthanum`, because the same names come from genuine `REE` rows on 1,392 records.
- **Data commit amended, same message: `7ae473f` "Add a commodity corrections list (Problem 5)".**
- **Checks:**
  - kg data checks with `MINMOD_DATA_DIR`: 25 passed.
  - `p5_fix_measure.py` (main vs branch, `PYTHONHASHSEED=0`): **0 unintended changes**. Every defect is at its earlier result.
  - Q674 merged sites go 774 → 821 (records 811 → 1,727). SRI's copy of MRDS already maps `Titanium, Metal` → Q674 on 811 records.
  - The 10 grade/tonnage rows that moved off Nonmetal are now under Titanium > Metal.
  - Water is unchanged: Q680 1 → 221 merged sites.
- **Nothing is pushed.**

## Corrections to the earlier reports

- **Earlier hypothesis: MRDS's comma split.** Now verified, on all 304,638 records.
- **`Metal`.** Earlier: "missing from ProcMine's table". The cause is MRDS's `Titanium, Metal` split; Q628 is also missing from that table, but it isn't the target.
- **`Water`.** Earlier: "its grade rows copy a rare-earth row". It's the reverse.
- **`General` → Clay > General, `Dimension` → Limestone > Dimension, `Refiner` → Gold > Refinery.** The earlier diagnosis called these correct. They are mostly wrong once the parent is known (MRDS 6,823 records, NC 71).
- **Oregon's 13 "undecodable" records** decode in MILO-4, where the source's code and text disagree (`stone, crushed` · `S&G`; `sand and gravel` · `SC`).

## Reproduce

| script | reads | writes |
|---|---|---|
| `p5/p5_rootcause_mrds.py` | `rdbms-tab-all/` (`Commodity.txt`, `Resource_detail.txt`), `commodity-codes.html`, the site JSON, the list | `p5/out/p5_rootcause_mrds.json`, `p5/out/p5_mrds_compound_names.csv` |
| `p5/p5_rootcause_nc.py` | `nc_location_points.json` (NC_MRDS layer 2), `Commodity.txt`, the site JSON, the list | `p5/out/p5_rootcause_nc.json` |
| `p5/p5_rootcause_oregon.py` | `milo4_points.json` (MILO layer 1), the site JSON | `p5/out/p5_rootcause_oregon.json` |
| `p5/p5_procmine_match.py` | ProcMine's `_entities/commodity.csv`, `commodity.csv` | `p5/out/p5_procmine_match.txt` |

All run with `python3 -I`. The match script needs strsimpy 0.2.1 (ProcMine's pin, installed hash-checked in a throwaway environment).
