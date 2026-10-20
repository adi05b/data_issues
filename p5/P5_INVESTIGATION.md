# P5 investigation: wrong commodity normalizations

*Read-only, 2026-10-20. Data `usc-isi-i2/ta2-minmod-data` @ `0c8b827`. kg `ta2-minmod-kg` main @ `45a2a16` (includes #108, #109, #112). ProcMine `umn-ta2-database-processing` @ `ce1ed70`, read only. No graph, Postgres or API was queried or written; no repo was changed.*

**How it was measured.** `p5_scan.py` reads every site JSON file (3,769 files, 679,778 records, 1,379,833 inventories) and counts each commodity candidate. `p5_merged.py` reads an offline merge made with main's own ETL code (`../p2c/rerun/scripts/p2d_run_merge.py`, same harness as P3; 54 s, 419,098 merged sites). For every merged site with an affected member, it rebuilds the site with main's `MineralSiteAndInventory.from_raw_site` and `DedupMineralSite.from_dedup_sites`, as `prep_kgrel_input` does: once as-is, once with the defect candidates dropped, and once with a 0.62 floor. The `data/mineral-sites` and `data/same-as` trees at `0c8b827` have the same git tree hashes as at `3a086a5` (`9fb1730…` and `ecd48aa…`), as do `commodity.csv`, `data_source.csv` and `commodity_form.csv`. Between those commits only `state_or_province.csv` changed (data#4, data#5). The scan gives byte-identical output on both checkouts.

**Grain.** *Record* = one site JSON record (`created_by`, `source_id`, `record_id`), the same as a graph `:MineralSite`. *Inventory* = one `mineral_inventory[]` entry, which carries exactly one commodity candidate. *Merged site* = one `dedup_mineral_site`.

## Results

| # | Hypothesis | Result | Evidence |
|---|---|---|---|
| H1 | Wrong value is stored as a candidate in the site JSON | **REPRODUCED** | `mineral_inventory[i].commodity` = `{source, confidence, observed_name, normalized_uri}`, one per inventory. One real record per defect below. The `UMN Matching System v1` rows (SC, S, CS, SD) are not traceable to any ProcMine commit; who wrote them is a hypothesis. |
| H2 | kg trusts `normalized_uri` as-is | **REPRODUCED** | Copied verbatim (`candidate_entity.py:31-38`) and used at `kgrel/mineral_site.py:72-75` with no check of confidence, matcher or observed name. The ETL, API/editor and GeoChem all pass through `from_raw_site`. The API validator only checks that the QID exists. |
| H3 | Counts reproduce on today's data | **REPRODUCED** | Every earlier count matches exactly at its own grain. 57,569 records and 53,346 merged sites are affected. Grade/tonnage under a wrong commodity: 12 merged sites, each a duplicate of a correct row on the same record. One new row: `SD` → Sand (41). |
| H4 | Dropping is lossless | **PARTIAL** | `Construction`/`Construc`: 47,201 of 47,201 records already have Sand and Gravel (Q656). Oregon: the record's own text decodes 7,074 `SC`, 2,337 `S`, 6 `CS` and 41 `SD`. 11 `S` and 2 `SC` can't be decoded, and 1 `S` (Last Chance Sulfur Mine) really is sulfur and is that record's only commodity. Targets Q664, Q665, Q655 and Q656 exist. |
| H5 | A confidence floor works | **PARTIAL** | Only ProcMinev2 grades its scores (113 values). Sample: 100 of 100 below 0.62 are wrong. Exhaustive check below 0.62: 47,997 wrong, 30 right, 7 partial inventories. The four Oregon rows come from a constant-1.0 matcher, so no floor reaches them. `Metal` (0.7599) is also above a 0.62 floor. |
| H6 | Fix could live in (a) overrides, (b) floor, (c) JSON edit | **PARTIAL** | No option reaches every path as it stands. Details in the table in H6. |
| H7 | Downstream uses of commodity | **REPRODUCED** | 8 consumers, listed below. The dashboard, KG export and CDR mining report read the raw candidate. The search, merged list and grade/tonnage read the views. |
| H8 | Out-of-scope counts | **REPRODUCED** | Unmatched: PGE 10,400, REE 1,573, HAL 935 records. The earlier totals left out rows that were in their own CSV. |

---

## H1: where the wrong value is stored (REPRODUCED)

**Fields.** Each record has `source_id`, `record_id`, `created_by` and `mineral_inventory[]`. Each inventory has `reference`, **`commodity`**, and optionally `category`, `grade{value,unit}`, `ore{value,unit}`, `cutoff_grade`, `material_form`, `date`, `zone`, `resource_year`. `commodity` is a single candidate, not a list:

```
commodity.source          the matcher, e.g. "UMN Matching System-ProcMinev2"
commodity.confidence      float
commodity.observed_name   the string after ProcMine's split and title-casing
commodity.normalized_uri  https://minmod.isi.edu/resource/Q…  (optional)
```

1,379,833 of 1,379,833 inventories have `commodity`. That equals the graph's commodity-node count on 2026-09-21 (`P5_DIAGNOSIS.md`, pre-flight). There is no `contained_metal` key anywhere, although ProcMine's `_attribute.py:220-221` writes one when the source has a tonnage column.

**One real record per defect** (`out/p5_scan.json` → `defects.*.example`; paths under `data/mineral-sites/`):

| defect | file | record_id | name | the record's commodity strings → QID (conf, matcher) |
|---|---|---|---|---|
| `Construction` → Strontium | `umn/mrdata_mrds/b000.json` | `10004382` | Portaluppi And Vita Pits | `Sand And Gravel` → Q656 (0.9999), **`Construction` → Q609 (0.5453)**, both ProcMinev2 |
| `SC` → Scandium | `umn/oregon_department_geology_mineral_industries/b000.json` | `ID_05048` | quarry | `stone` → Q663 (1.0), `crushed` → none (0.001), **`SC` → Q607 (1.0)**, all UMN v1 |
| `S` → Sulfur | `…oregon…/b000.json` | `ID_06010` | gravel pit | `sand and gravel` → Q656, **`S` → Q633 (1.0)**, `G` → none (0.001) |
| `Construc` → Cobalt | `umn/nc_geological_survey/b000.json` | `1886` | Delbert E Barefoot Pit | `Sand And Gravel` → Q656 (0.9999), **`Construc` → Q537 (0.5368)** |
| `CS` → Cesium | `…oregon…/b008.json` | `ID_21586` | quarry | `stone` → Q663, `crushed` → none, **`CS` → Q591 (1.0)** |
| `SD` → Sand *(new)* | `…oregon…/b001.json` | `ID_03975` | G.Heden No.5,6,7,8 | `stone` → Q663, `dimension` → none, **`SD` → Q655 (1.0)** |
| `Metal` → Nonmetal | `umn/mrdata_mrds/b000.json` | `10008252` | Deposits Other Than Rodsand Mine | `Vanadium`, `Titanium`, `Iron` (0.9999), **`Metal` → Q581 (0.7599)** |

```json
// umn/mrdata_mrds/b000.json, record_id 10004382 (excerpt)
{"commodity": {"confidence": 0.9999, "normalized_uri": "https://minmod.isi.edu/resource/Q656",
               "observed_name": "Sand And Gravel", "source": "UMN Matching System-ProcMinev2"}},
{"commodity": {"confidence": 0.5453337996531422, "normalized_uri": "https://minmod.isi.edu/resource/Q609",
               "observed_name": "Construction", "source": "UMN Matching System-ProcMinev2"}}
```

**Where the values come from (ProcMine, read only).**
- ProcMinev2 writes the candidate at `procmine/converting/_entity.py:33-39` (`"source": "UMN Matching System-ProcMinev2"`).
- An exact match scores 0.9999 (`_entity.py:54-56`). Otherwise the score is the mean of six string similarities against every entity, with no minimum: any best score above 0.0001 wins (`_entity.py:59-92`). Only `confidence > 0` is filtered (`_attribute.py:215-217`). That fits ProcMinev2 having 0 unmatched candidates.
- Commodity strings are split on `| , ;` (`_procmine.py:217`) and title-cased (`_attribute.py:74`).
- Entities are matched on `name`, `aliases`, `geokb_name` and `mrds_code`. This was read from `_entities/_selected_cols.pkl` by disassembling it with `pickletools`; the file was not unpickled.
- *Hypothesis:* MRDS wrote `Sand and Gravel, Construction`, and the comma split produced `Sand And Gravel` plus `Construction`. Support: every one of the 46,221 `Construction` records also has `Sand And Gravel`. The raw MRDS file is not in any repo.
- *Hypothesis:* `UMN Matching System v1` (all four Oregon rows) is an earlier UMN matcher. No commit of `umn-ta2-database-processing` contains that label. An undated draft (`7f3e8c7`) has the same signature: exact match = 1.0, no-match sentinel = 0.001.

## H2: kg trusts the value as-is (REPRODUCED)

**ETL trace** (file:line in `ta2-minmod-kg` @ `45a2a16`):

1. `etl.yml:118-123`: `kgrel.data.mineral_site` reads `::REPO::data/mineral-sites`.
2. `etl/mineral_site.py:409-433`: `MergeFn.invoke` deserializes each record and calls `MineralSiteAndInventory.from_raw_site(raw_site, commodity_form_conversion, crs_names, source_score)` (`:426-431`). No commodity table is passed in.
3. `models/kgrel/mineral_site.py:61` → `MineralSite.from_raw_site` (`:206-254`) → `KGMineralSite.from_dict` (`models/kg/mineral_site.py:158-160`) → `MineralInventory.from_dict` (`models/kg/mineral_inventory.py:55`) → `CandidateEntity.from_dict` (`models/kg/candidate_entity.py:31-38`). All four fields are copied verbatim, and the raw list is stored as `inventories=site.mineral_inventory` (`kgrel/mineral_site.py:247`).
4. **`kgrel/mineral_site.py:71-76`, the only place the commodity is interpreted:** `if inv.commodity.normalized_uri is None: continue` then `commodity = NS_MR.id(inv.commodity.normalized_uri)`. `confidence`, `source` and `observed_name` are never read.
5. `:78-151`: grade/tonnage per commodity (`GradeTonnageModel`), then one `MineralInventoryView(commodity=…)` per commodity.
6. Merged site: `DedupMineralSite.from_sites` (`models/kgrel/dedup_mineral_site.py:226-317`) and `from_dedup_sites` (`:113-224`) call `select_inventories` (`:339-406`). It keeps one row per `inv.commodity`, preferring user data, then rows with grade/tonnage, then the latest date, then the largest contained metal.
7. `etl/mineral_site.py:302-365`: `prep_kgrel_input` writes `MineralSite` (raw `inventories` in a JSON column, `kgrel/base.py:49`), `MineralInventoryView` and `DedupMineralInventoryView`. `etl/postgres.py:136-174` loads them into the `mineral_site`, `mineral_inventory_view` and `dedup_mineral_inventory_view` tables.
8. KG: `ExportTTLFn.invoke` writes `msi.ms.to_kg().to_triples()` (`etl/mineral_site.py:473-477`), with `to_kg()` taking `mineral_inventory=self.inventories` (`kgrel/mineral_site.py:363`). The wrong `normalized_uri` reaches Fuseki unchanged.

`grep` finds no other place where the ETL resolves a commodity.

**API/editor: the same path.**
- `POST /mineral-sites` and `PUT /mineral-sites/{id}` (`api/routers/mineral_site.py:105-121, 139-187`) call `_validate_site`, then `InputPublicMineralSite.to_kgrel` → `MineralSiteAndInventory.from_raw_site` (`api/models/public_mineral_site.py:188-198`).
- The validator only checks that `normalized_uri` is a known commodity URI (`validators.py:412-418`, using `get_commodity_uris`, `services/kgrel_entity.py:128-131`). A wrong but existing QID passes.
- The write goes to Postgres (`services/mineral_site.py:146-268, 270-353`), then to the KG (`services/sync/kgsync_listener.py:47, 65`) and to the data repo (`services/sync/backup_listener.py:210`). All three carry the candidate as submitted.

**GeoChem: the same `from_raw_site`, but it builds its own candidates.**
- `etl/geochem_loader.py:82-90` (`to_msi`) calls the same `from_raw_site`.
- Candidates come from `etl/geochem_jsonld.py:230-250` and `:332-346`. It uses the node's `normalized_uri` if one is given, otherwise an exact lower-case match on parent-less commodity names and aliases (`:213-216`, `:243-244`), with confidence 1.0 by default (`:247`). ProcMine's candidates never reach it.

## H3: counts on today's data (REPRODUCED)

| defect (observed → recorded) | source | matcher | conf | **records** | inventories | **merged sites** | inventories with grade/tonnage | **merged sites showing grade/tonnage under the wrong commodity** | earlier |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| `Construction` → Strontium Q609 | mrds | ProcMinev2 | 0.5453 | **46,221** | 46,223 | **46,220** | 2 | **2** | 46,223 / 46,221 |
| `SC` → Scandium Q607 | Oregon | UMN v1 | 1.0 | **7,076** | 7,076 | **2,949** | 0 | 0 | 7,076 |
| `S` → Sulfur Q633 | Oregon | UMN v1 | 1.0 | **2,349** | 2,349 | **2,349** | 0 | 0 | 2,349 |
| `Construc` → Cobalt Q537 | nc-geological-survey | ProcMinev2 | 0.5368 | **980** | 980 | **980** | 0 | 0 | 980 |
| `CS` → Cesium Q591 | Oregon | UMN v1 | 1.0 | **6** | 6 | **6** | 0 | 0 | 6 |
| `SD` → Sand Q655 *(new)* | Oregon | UMN v1 | 1.0 | **41** | 41 | **41** | 0 | 0 | called correct |
| `Metal` → Nonmetal Q581 | mrds 840 rec + nc 76 rec | ProcMinev2 | 0.7599 | **916** | 937 | **821** | 21 | **10** | 916 |
| **any of the above** | | | | **57,569** | | **53,346** | 20 records | **12** | |

Sources: `out/p5_scan.json` and `out/p5_merged.json` (`merged_grain`, `record_grain_views`). Twenty records carry two defects (19 `Construction`+`Metal`, 1 `Construc`+`Metal`).

**The real harm (grade/tonnage).** It is small, and in every case it duplicates a correct row:
- **Strontium, 2 merged sites:** MRDS `10115528` (Pacoima Canyon Placers, 1.92 Mt ore at 65 %, 1.248 Mt "strontium") and `10236674` (Sand Canyon Placers, 0.82 Mt at 65 %). In both, the `Construction` inventory carries exactly the ore and grade of the record's own `Sand And Gravel` inventory.
- **Nonmetal, 10 merged sites:** 21 raw `Metal` inventories on 18 records carry a grade, and all 21 have the same grade and ore as a `Titanium` inventory on the same record. The largest is MRDS `10023282`: 4,190 Mt at 77.35 %, which shows as 3,241 Mt contained "Nonmetal". 10 of the 18 records have enough data (ore, grade, units, category) for kg's model to compute grade/tonnage.
- **SC, S, Construc, CS, SD:** no grade or tonnage at all.

**How this compares with the earlier numbers.**
- **Every count is the same; the data has not changed.** The `mineral-sites` tree is identical, and inventories (1,379,833) equal the earlier graph's commodity nodes.
- `Construction` 46,223 vs 46,221 is grain: 46,223 inventories on 46,221 records, because 2 records each carry two `Construction` inventories. Both earlier figures are right at their own grain.
- The brief's 4,174 for Sulfur was a hypothesis earlier. It is exactly the number of **merged sites** that list Sulfur (`wrong_commodity_totals`). Records with Sulfur: 5,171, as the earlier run found.
- `Metal` 916 is records; there are 937 inventories.
- Merged-site counts are new. `SC` collapses most (7,076 → 2,949), because 579 of its merged sites have several Oregon records.

## H4: is dropping lossless? (PARTIAL)

**`Construction` and `Construc`: no commodity is lost.**

| | records | records that also have Sand and Gravel Q656 | merged sites | merged sites that list Q656 | merged sites left with no commodity after a drop |
|---|--:|--:|--:|--:|--:|
| `Construction` | 46,221 | **46,221** | 46,220 | **46,220** | 0 |
| `Construc` | 980 | **980** | 980 | **980** | 0 |

The usual pattern is `Sand And Gravel` alone beside it: 45,546 of 46,221 `Construction` records and 977 of 980 `Construc` records. One merged site keeps Strontium after the drop: MRDS `10186268` "Strontium Group", which also has a genuine `Strontium` → Q609. The 2 inventories with grade/tonnage duplicate the Sand and Gravel row, so no grade or tonnage is lost.

**Oregon codes: evidence from the records themselves.**
- Every Oregon record lists its commodity strings in a fixed order: *group | subtype | code*, for example `gold | silver | Au Ag`, `mercury | gold | Hg Au`, `manganese ore | Mn`.
- The code is a short form of the group and subtype.
- Below is every pattern that contains `S`, `SC`, `CS`, `SD` or `G` (`out/p5_scan.json` → `oregon_code_patterns`).

| records | strings in the record | what the code means here | evidence | target in `commodity.csv` |
|--:|---|---|---|---|
| 7,074 | `stone \| crushed \| SC` | stone, crushed | group and subtype on the same record | **Q664 Stone > Crushed/Broken** (exists) |
| 2 | `sand and gravel \| SC` | **can't be decoded** | no subtype | — |
| 2,337 | `sand and gravel \| S \| G` | S = sand, G = gravel | group on the same record; `G` is left unmatched | Q655 Sand / **Q656 Sand and Gravel** (exist; the record already has Q656) |
| 10 + 1 | `stone \| crushed \| S \| G` (+ `pumice`) | **can't be decoded** | the code doesn't fit the group | — |
| 1 | `sulfur and pyrite \| S` | **sulfur, correct** | `ID_04514` Last Chance Sulfur Mine (`b043.json`) | Q633 is right |
| 6 | `stone \| crushed \| CS` | *hypothesis:* crushed stone | group and subtype on the same record | Q664 (exists) |
| 41 | `stone \| dimension \| SD` | **stone, dimension (not sand)** | group and subtype on the same record | **Q665 Stone > Dimension** (exists) |

- No code book exists in the repos. The Oregon `data_source.csv` row (line 14) has no description and no connection. Nothing in the kg, data or ProcMine docs describes DOGAMI's codes.
- The collisions do have an explanation in `commodity.csv` itself: `SC`, `SD`, `CS` and `S` are the **`mrds_code`** of Scandium, Sand, Cesium and Sulfur. `Sc`, `Cs` and `S` are also their aliases.
- *Hypothesis:* the v1 matcher matched on those columns, as ProcMinev2 does.

**Lossless?**
- Dropping `SC`, `CS` or `SD` leaves every record at least `Stone` (Q663), but it gives up the subtype. "crushed" and "dimension" were never normalized (0.001).
- Dropping all Oregon `S` would wrongly remove sulfur from Last Chance Sulfur Mine. That leaves its merged site with **no commodity** (1 merged site; `merged_sites_with_no_commodity_after_drop`).
- `Metal` (not asked, same table): all 916 records also have Titanium (Q614), and all 21 grade rows duplicate it. `commodity.csv` has **Q628 Metal** and **Q674 Titanium > Metal**, but ProcMine's bundled copy lacks both (see H5).

## H5: the confidence floor (PARTIAL)

**Matchers** (`out/matchers.csv`, inventory grain):

| matcher (`commodity.source`) | matched | unmatched | confidences when matched | graded? |
|---|--:|--:|---|---|
| UMN Matching System-ProcMinev2 | 635,449 | 0 | 113 values, 0.4998–0.9999 (exact = 0.9999 on 552,430) | **graded** |
| SRI database agent v0 | 299,575 | 79,480 | 1.0 only (unmatched also 1.0) | constant |
| UMN Matching System v1 | 192,018 | 102,843 | 1.0 only (unmatched: 0.9 ×46,550, 0.001 ×42,725, 1.0 ×13,568) | constant |
| Inferlink Extraction v3 / v2 | 39,962 / 9 | 396 / 0 | 1 | constant |
| SAND | 19,683 | 27 | 0.99 / 1.0 (unmatched 0.0) | two values |
| UMN Exact Match v1 | 10,385 | 0 | 0.9 | constant |
| users (`jhammars`, `bvu`, `caknoblock`) | 6 | 0 | 1.0 | constant |

**Which matcher made each defect:**
- ProcMinev2 (graded): `Construction` 0.5453, `Construc` 0.5368, `Metal` 0.7599.
- **UMN Matching System v1 (constant 1.0): `SC`, `S`, `CS`, `SD`.** No floor below 1.0 can reach these 9,472 inventories.
- A 0.62 floor also misses `Metal`.

**Below 0.62.** 48,034 matched candidates are below 0.62, all from ProcMinev2, in 23 distinct (observed → label) pairs.

- **Random sample** (`out/h5_sample_below_062.csv`): 100 inventories drawn uniformly from the 48,034 with `random.Random(20261020).sample`. Each was judged against its observed string only. **100 WRONG** (97 `Construction`→Strontium, 3 `Construc`→Cobalt). The exact (Clopper-Pearson) 95 % lower bound on the wrong share is 96.4 %. The sample is dominated by `Construction`, so it says nothing about the rare pairs.
- **Exhaustive check** (`out/h5_pairs_below_062.csv`, verdicts and reasons in `p5_h5_judge.py`): all 23 pairs judged.

| verdict | pairs | inventories | records |
|---|--:|--:|--:|
| WRONG | 17 | 47,997 | 47,956 |
| RIGHT (`Rock Asphalt`, `Industrial/Frac Sand`→Sand, `Muscovite Mica`→Mica) | 3 | 30 | 30 |
| PARTIAL (`Columbite-Tantalite`→Tantalum, `Copper And Garnet`→Copper, `Kaolin/ Feldspar`→Feldspar) | 3 | 7 | 7 |

- **The floor at merged-site grain** (`out/p5_merged.json` → `floor_062`):
  - 47,977 merged sites are touched and 47,976 lose a commodity.
  - **291 are left with no commodity.** 282 of them only ever had a wrong one (267 `Volcanic Materials`→Bloating clay, 11 `Monazite`→Magnesite, 4 others). **9 lose their only correct commodity** (8 Rock Asphalt, 1 Mica).
  - 4 lose grade/tonnage: 2 Strontium (duplicates of Sand and Gravel) and 2 Slate, from MRDS `Water` (`10304195`, `10280185`).
- **Stale entity table.** ProcMine's bundled `_entities/commodity.csv` has 198 rows. Today's has 203; the extra five are **Q628 Metal, Q674 Titanium > Metal, Q675 Titanium > Pigment, Q679 Volcanic Materials and Q680 Water**. Three wrong mappings (`Metal`, `Volcanic Materials`, `Water`) have their right target in that missing set. *Hypothesis:* those three exist because ProcMine's table was out of date when it ran.

## H6: where a fix could live (facts only; PARTIAL: no option reaches every path as it stands)

What `main` does when a commodity is dropped was tested in `p5_merged.py:selfcheck` (assert-based, runs on every call):

| how the commodity is dropped | result |
|---|---|
| `normalized_uri` removed | inventory kept in `ms.inventories`, Postgres `mineral_site.inventories` and the KG export; **no** `MineralInventoryView` row |
| inventory removed | gone from the site, the views and the KG; the site is still built |
| `commodity` key removed | **`KeyError`** at `models/kg/mineral_inventory.py:55`; the merge fails |
| merged site with every commodity dropped | built, with zero `DedupMineralInventoryView` rows (no error) |

| | (a) override table in ta2-minmod-data | (b) confidence floor in kg | (c) edit the site JSON |
|---|---|---|---|
| **kg host** | **Load:** `etl/kgrel_entity.py:56-66` (file list), `:128-149` (`read_file`). **Serve:** a getter like `get_commodity_form_conversion` (`services/kgrel_entity.py:57-63`) on `FileEntityService` (`:198-207`). **Apply:** `MineralSite.from_raw_site` (`models/kgrel/mineral_site.py:206-254`, before `:247`) if the KG should change, or `MineralSiteAndInventory.from_raw_site` `:71-76` for views only. **Callers that must pass it:** `etl/mineral_site.py:426-431`, `api/models/public_mineral_site.py:188-198`, `etl/geochem_loader.py:83-88`. These are the three callers #110 changes for `state_index`. | `models/kgrel/mineral_site.py:72` (views only) or `:247` (raw inventories, so also the KG export). One constant; no entity file. | None. The data is in `data/mineral-sites/umn/{mrdata_mrds, nc_geological_survey, oregon_department_geology_mineral_industries}/`: **192 files** contain a defect (all 64 buckets of each folder). |
| **ETL** | yes | yes | yes |
| **API/editor** | Only if the table is in Postgres. The API uses `EntityService.get_instance()` (`services/kgrel_entity.py:52-55`), which reads Postgres (`:193-195`). #110's alt-names pattern keeps aliases in the entity JSON only, and its base `EntityService` returns `{}`, so a file-only table **does not** reach the API. Putting it in Postgres needs a model, a migration and an entry in `etl/postgres.py:103-113`. | yes (shared `from_raw_site`) | Only after the next ETL reload rebuilds Postgres. New API writes are not covered. |
| **GeoChem** | Same as the API: `save_postgres` uses `EntityService.get_instance()` (`etl/geochem_loader.py:122`) | yes | no (GeoChem reads JSON-LD, not site JSON) |
| **Caches** | **`merge-v107.sqlite` must be bumped** (`etl/mineral_site.py:400-408`). Its key is only the site files plus the same-as file, so a change to any entity file never invalidates it, and every later edit to the table needs another bump. `transform-v107` (`etl/kgrel_entity.py:81`): a new file is cached under its own key; bump only if an existing reader changes. `export-v101` (`:467-471`) is keyed on the merged file's sha256 and re-runs by itself. **#110 and #111 both already use `merge-v108`**, and #110 also moves entities to `v108`. | **`merge-v107` must be bumped** (code change; the key holds no code version). No entity bump. Export re-runs by itself. | **None.** The merge key is path + sha256 of each site file (`statickg/models/file_and_path.py:28-29, 41-45`), so edited files re-merge. |
| **ProcMine re-run** | **Not overwritten.** `run_processing.sh` writes only `data/mineral-sites/umn/<folder>/<file>.large.json`. *Hypothesis:* rules keyed on observed strings stop matching silently if a re-run changes the string (`_attribute.py:74` title-case, `_procmine.py:217` split). A drop rule would still fire on a mapping a re-run had fixed (e.g. `Metal` → Q628 once ProcMine's table is updated) unless the rule is also keyed on the wrong QID. | Not overwritten (kg code). *Hypothesis:* which rows fall below 0.62 changes with any re-run. | **Overwritten.** A re-run writes new site JSON for the same records. The ETL refuses duplicate site ids across files (`etl/mineral_site.py:163-168`), so the old files have to be replaced, edits included. (The refusal is a fact; the replace step is a hypothesis about the workflow.) |
| **Inventory whose only commodity is dropped** | as in the table above, depending on how the rule drops | `uri`-None semantics: kept, no view row | depends on the edit; deleting the `commodity` key breaks the merge (the data repo has no CI to catch it) |
| **Which defects it reaches** | all 7, if listed | `Construction`, `Construc` (+ 794 other wrong and 37 right/partial inventories) | whatever is edited |

## H7: downstream uses of commodity (REPRODUCED)

| # | consumer | reads | file:line | change if the 7 rows are dropped (`uri` → None on the raw candidate) |
|---|---|---|---|---|
| 1 | Raw candidate on the record (editor, `GET /mineral-sites/{id}`) | `MineralSite.inventories` | `kgrel/mineral_site.py:247`; `public_mineral_site.py:93` | The editor shows the candidate without a QID. |
| 2 | Per-record commodity rows | `MineralInventoryView` | built `kgrel/mineral_site.py:118-151`; table `views/mineral_inventory_view.py:12-28`; paper search by commodity `services/paper.py:80-86`; site `grade_tonnage` `public_mineral_site.py:108-117` | Wrong rows go: Strontium on 46,220 records (1 genuine stays), Scandium 7,076, Sulfur 2,349, Cobalt 980, Cesium 6, Sand 41, Nonmetal 916. |
| 3 | Merged site's commodity list | `DedupMineralInventoryView` via `select_inventories` | `dedup_mineral_site.py:339-406`; `?commodity=` filter `services/mineral_site.py:505-512`; `has_grade_tonnage` `:535-549`; CSV download (one row per commodity) `routers/dedup_mineral_site.py:237-253`; LOD page `routers/lod.py:123-134`; trace `public_dedup_mineral_site.py:159-161` | Merged sites listing each: **Strontium 46,612 → 393, Scandium 2,998 → 49, Sulfur 4,174 → 1,825, Cobalt 4,042 → 3,062, Cesium 42 → 36, Sand 688 → 647, Nonmetal 824 → 3.** 1 merged site is left with no commodity (Last Chance). |
| 4 | Grade/tonnage | `GradeTonnageModel` per commodity, then a per-merged-site pick | `kgrel/mineral_site.py:78-139`; `dedup_mineral_site.py:379-404` | The 12 wrong grade/tonnage rows go (2 Strontium, 10 Nonmetal). Each duplicates a Sand and Gravel or Titanium row that stays. |
| 5 | Dashboard counts | SPARQL on the KG, `mo:commodity/mo:normalized_uri` | `api/routers/stats.py:107-167` | Records per commodity: **Strontium 47,112 → 892, Scandium 7,139 → 63, Sulfur 5,171 → 2,822, Cobalt 6,535 → 5,555, Cesium 65 → 59, Sand 735 → 694, Nonmetal 919 → 3.** Only if the fix changes the raw candidate. |
| 6 | KG export and API sync | `ms.to_kg()` = raw inventories | `etl/mineral_site.py:473-477`; `kgrel/mineral_site.py:363`; `kgsync_listener.py:47, 65` | Same as 5. Unchanged if only the views change. |
| 7 | CDR | mining report: raw inventories of `api.cdr.land` records; dedup push: one CDR record per merged commodity | `routers/cdr.py:37-60`; `integrations/cdr/cdr.py:73-117, 181-198` | Mining report: no change (no defect is from that source). Dedup push: the Strontium, Scandium and other records listed in row 3 disappear. |
| 8 | Write-back of API edits to the data repo | `ms.to_kg().to_dict()` | `services/sync/backup_listener.py:187-210` | Writes whatever the edited site carries. Today **0** user-owned copies of a defect record exist in the data repo (all 57,589 defect rows are `umn`'s). A user copy would win in `select_inventories` (`dedup_mineral_site.py:364-374`). |

**Remap instead of drop.** The wrong commodity's counts move to the target. `select_inventories` keeps one row per commodity, so where the record already lists the target, the rows merge: `S` → Q656 on the 2,337 `sand and gravel | S | G` records adds no row. Where it doesn't, a new row appears: `SC`/`CS` → Q664, `SD` → Q665, `Metal` → Q674. **Views-only fix** (a floor at `:72`, or an override applied there): rows 2–4 change; rows 1, 5, 6, 7 (mining report) and 8 don't. The dashboard would keep counting 46,220 Strontium records.

## H8: out-of-scope counts (REPRODUCED, totals differ)

Records with an **unmatched** candidate whose observed string is exactly `PGE`, `REE` or `HAL` (`out/p5_scan.json` → `h8`):

| code | unmatched records | by source | matched records |
|---|--:|---|--:|
| PGE | **10,400** | nicrpge 9,613 (UMN v1 5,116 + SRI 4,497), mrds 714, P96MMRFD 56, major-deposits 16, sir20105090z 1 | 131 (major-deposits) |
| REE | **1,573** | mrds 1,294, nicrpge 172 (89 + 83), P96MMRFD 64, phosphate 39, major-deposits 4 | 148 (major-deposits 90, phosphate 44, ofr20151121 14) |
| HAL | **935** | potash 924 (462 + 462), OFR-757 11 | 0 |

The earlier totals (10,383, 1,397, 924) left out rows that are in the earlier run's own `p5-s3-shortcodes.csv`: major-deposits PGE 16, sir20105090z PGE 1, nicrpge REE 172, major-deposits REE 4 and OFR-757 HAL 11. The data has not changed.

## Files

| file | what |
|---|---|
| `p5_scan.py` | raw-record scan → `out/candidates_census.csv` (every candidate × count), `out/matchers.csv`, `out/p5_scan.json`, the H5 sample and pairs; `run-big/defect_records.csv` (9.5 MB, not committed) |
| `p5_merged.py` | merged-site rebuild with main's code; drop and floor scenarios; self-check of drop behaviour → `out/p5_merged.json` |
| `p5_h5_judge.py` | H5 verdicts with one-line reasons → fills `verdict` in the two H5 CSVs |

```
CFG_FILE=$MAIN/tests/resources/config.yml PYTHONPATH=$MAIN .venv-p2/bin/python p5_scan.py ta2-minmod-data out
CFG_FILE=$MAIN/tests/resources/config.yml PYTHONPATH=$MAIN .venv-p2/bin/python ../p2c/rerun/scripts/p2d_run_merge.py ../p2c/rerun/scripts/p2_etl.yml run-main ta2-minmod-data
CFG_FILE=$MAIN/tests/resources/config.yml PYTHONPATH=$MAIN .venv-p2/bin/python p5_merged.py run-main out
python3 p5_h5_judge.py out
```

`ta2-minmod-data/` is a blobless clone at `0c8b827`; it, `run-main/` and `run-big/` are ignored by git. Adriana's client files were not used.
