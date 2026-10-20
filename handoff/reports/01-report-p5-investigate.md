# Report 01: Problem 5 investigation (wrong commodity normalizations)

*Read-only, 2026-10-20. Data `ta2-minmod-data` @ `0c8b827`. kg main @ `45a2a16`. ProcMine @ `ce1ed70`, read only. Full evidence: `p5/P5_INVESTIGATION.md`.*

## Summary

- **The data has not changed since the earlier diagnosis.**
  - `data/mineral-sites` has the same tree hash at `0c8b827` as at `3a086a5`.
  - The site JSON holds exactly 1,379,833 commodity candidates, which is the graph's node count on 2026-09-21.
  - Every earlier count reproduces at its own grain.
- **57,569 records (of 679,778) and 53,346 merged sites (of 419,098) carry one of 7 defects.**
  - `Construction`→Strontium: 46,221 records / 46,220 merged sites
  - `SC`→Scandium: 7,076 / 2,949
  - `S`→Sulfur: 2,349 / 2,349
  - `Construc`→Cobalt: 980 / 980
  - `Metal`→Nonmetal: 916 / 821
  - `SD`→Sand (new): 41 / 41
  - `CS`→Cesium: 6 / 6
- **Grade/tonnage harm is small and always duplicated.**
  - 12 merged sites show grade/tonnage under a wrong commodity: 2 Strontium, 10 Nonmetal.
  - In every case, the same ore and grade sit on a correct Sand and Gravel or Titanium row of the same record.
  - The main harm is in listings and counts. For example, 46,219 of the 46,612 merged sites that list Strontium list it only because of `Construction`, and the dashboard counts 46,220 Strontium records that aren't strontium.
- **kg trusts the candidate as-is.**
  - `normalized_uri` is copied verbatim and used at `models/kgrel/mineral_site.py:72-75`.
  - The ETL, API/editor and GeoChem all go through that `from_raw_site`.
  - The API validator only checks that the QID exists.
- **Matchers.**
  - Only ProcMinev2 emits graded confidences.
  - All four Oregon codes come from `UMN Matching System v1`, which stamps 1.0 on every match, so no floor can reach them.
  - Below 0.62, all 23 graded pairs were judged: 47,997 inventories wrong, 30 right, 7 partial. In a random sample of 100, all 100 were wrong.

## Results

| # | Hypothesis | Result | Evidence |
|---|---|---|---|
| H1 | Wrong value stored as a candidate in the site JSON | REPRODUCED | `mineral_inventory[i].commodity` = `{source, confidence, observed_name, normalized_uri}`, one per inventory; one real record per defect. The writer of the v1 rows is not traceable in the ProcMine repo. |
| H2 | kg trusts `normalized_uri` as-is | REPRODUCED | `candidate_entity.py:31-38` → `kgrel/mineral_site.py:72-75`. The API (`public_mineral_site.py:188`) and GeoChem (`geochem_loader.py:83`) use the same `from_raw_site`. The validator only checks the QID exists (`validators.py:412-418`). |
| H3 | Counts reproduce on today's data | REPRODUCED | All earlier counts match. Merged-site counts are new. Grade/tonnage under a wrong commodity on 12 merged sites, all duplicates. |
| H4 | Dropping is lossless | PARTIAL | `Construction`/`Construc`: 47,201 of 47,201 records already have Sand and Gravel. Oregon: decodable from the record for 9,459 of 9,472 code inventories, 1 of them a genuine sulfur `S`. 13 can't be decoded. The sulfur `S` (Last Chance Sulfur Mine) is that record's only commodity. Targets Q664, Q665, Q655 and Q656 exist. |
| H5 | A confidence floor works | PARTIAL | Only ProcMinev2 is graded. At 0.62: 47,203 of 57,612 defect inventories caught (`Construction`, `Construc`), plus 794 other wrong ones. Costs 37 right/partial inventories. Leaves 291 merged sites with no commodity, 9 of which lose their only correct commodity. Misses SC, S, CS, SD (constant 1.0) and `Metal` (0.7599). |
| H6 | Fix could live in (a) overrides, (b) floor, (c) JSON edit | PARTIAL | (a) reaches the ETL; it reaches the API/GeoChem only if the table is in Postgres (the #110 alt-names pattern is file-only). (b) reaches all three paths but catches 2 of 7 defects. (c) reaches the ETL only and is lost on a ProcMine re-run. (a) and (b) need a merge-cache bump, and #110 and #111 both already use `merge-v108`. |
| H7 | Downstream uses of commodity | REPRODUCED | 8 consumers. The dashboard, KG export and CDR mining report read the raw candidate. Search, the merged commodity list and grade/tonnage read the views. A views-only fix leaves the dashboard counting 46,220 Strontium records. |
| H8 | Out-of-scope counts | REPRODUCED | Unmatched records: PGE 10,400, REE 1,573, HAL 935. |

## What contradicts the earlier diagnosis

1. **`SD` → Sand is wrong, not correct.**
   - All 41 records are `stone | dimension | SD`, the dimension-stone counterpart of `stone | crushed | SC`.
   - The target is Q665 Stone > Dimension.
2. **`Apatite` → Graphite is wrong, not correct** (1 record).
   - At 0.62, the floor's cost is 30 right + 7 partial records. The earlier figures were 33 good, with partials counted separately.
   - The 0.62 trade-off otherwise reproduces: 47,956 wrong records.
3. **The Oregon patterns are not uniform.**
   - `S` sits in `sand and gravel | S | G` on 2,337 of 2,349 records, not on all of them. The rest are 11 `stone | crushed | S | G` and 1 genuine sulfur record.
   - `SC` sits in `stone | crushed | SC` on 7,074 of 7,076. The other 2 are `sand and gravel | SC`.
4. **Earlier H8 totals left out rows that were in that run's own CSV.**
   - PGE: +17 (major-deposits 16, sir20105090z 1).
   - REE: +176 (nicrpge 172, major-deposits 4).
   - HAL: +11 (OFR-757).
5. **`Metal` → Nonmetal has a narrower cause than "needs a blocklist".**
   - ProcMine's bundled commodity table (198 rows) lacks 5 entities that today's has (203 rows): Q628 Metal, Q674 Titanium > Metal, Q675 Titanium > Pigment, Q679 Volcanic Materials, Q680 Water.
   - The wrong mappings `Metal`, `Volcanic Materials` and `Water` all have their right target in that missing set. *Hypothesis:* the table was out of date when ProcMine ran.
   - All 916 `Metal` records also carry Titanium.
6. **These are confirmations rather than contradictions:**
   - The brief's 4,174 for Sulfur is exactly the merged-site count.
   - `Construction` 46,223 vs 46,221 is inventories vs records: 2 records carry it twice.

## Open questions for you

1. **Oregon codes that can't be decoded:** 11 `stone | crushed | S | G` and 2 `sand and gravel | SC`. Nothing in the repos explains DOGAMI's code field. Can Adriana or DOGAMI provide the code book?
2. **Remap or drop for Oregon and `Metal`?** Q664, Q665, Q656 and Q674 exist. Dropping `SC`/`SD`/`CS` keeps `Stone` but loses the crushed/dimension subtype, and dropping all Oregon `S` empties Last Chance Sulfur Mine.
3. **Should a fix change the raw candidate or only the views?** Only the raw candidate reaches the KG, the dashboard counts and the CDR mining report.
4. **The editor.** When a user edits a ProcMine record, does the editor send back its candidates, creating a user-owned copy that wins in `select_inventories`? The data repo has 0 such copies today. The live database was not checked.
5. **Cache names.** #110 and #111 both use `merge-v108`. Any P5 change in kg would need a third, distinct name. Who coordinates?
6. **Live graph.** It was not queried in this run; every number comes from the data repo plus an offline merge with main. Do you want one light SPARQL check that the deployed graph still matches?
7. **The prompt file.** `handoff/prompts/01-prompt-p5-investigate.md` doesn't exist in this folder. I didn't add it, because its text contains a word the folder's scan rejects.
