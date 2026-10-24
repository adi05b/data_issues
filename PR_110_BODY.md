# Repair states recorded in the wrong country at merge time

**Summary:** 5,856 merged sites had a state from another country. After this PR: 5,543 are repointed to the right state, 92 Katanga sites get their 2015 province from their location, and 221 are left empty on purpose (listed in the attached `P2_REVIEW_LIST.csv`). No other site changes.

**Depends on usc-isi-i2/ta2-minmod-data#5 — merge that first.**

Branch `fix/p2-state-repair`, rebased on `main` `63ab67e`. **Merge the `ta2-minmod-data` PR first** (see Deploy).

**5,856 merged sites have a state that belongs to another country than their own** (Florida → Puerto Rico, La Paz → La Pampa, Potosí → Porto). The upstream state matcher looks states up by name alone and never sees the record's country. MinMod holds every state with its country at merge time, so the merge repairs the choice. Only `location_view` changes: the KG `location` keeps what the source said.

## What changes

- **Repair tiers, plus aliases** (`minmodkg/misc/state_repair.py`, called from `LocationView.from_location`):
  - **When:** only for a state whose country is none of the record's countries.
  - **How:** it is re-resolved inside those countries, stopping at the first tier that matches:
    1. the exact folded name;
    2. the name without administrative words ("La Paz" → La Paz Department);
    3. the `state_code`;
    4. an alias from the new `alt names` column, exact match only.
  - **Result:** one hit repoints the state. No hit, or more than one, drops it. There is no fuzzy matching.
- **Option A, now 6 pairs.** An explicit list, used only when the repair would drop the state. The record moves to the dependency's own country, and the state stays empty.

  | sovereign | dependency |
  |---|---|
  | France | New Caledonia |
  | Denmark | Greenland |
  | Australia | Christmas Island |
  | United Kingdom | Montserrat |
  | United Kingdom | Virgin Islands (British) |
  | United Kingdom | Cayman Islands |

  Listing China/Taiwan, US/Georgia, Nigeria/Niger, Belgium/Luxembourg or Guinea/Mali raises an error.
- **Katanga from the record's location.**
  - **When:** the record's country is DR Congo, its state is "Katanga" or "Katanga Province", and the repair would drop it.
  - **Then:** the record takes the 2015 successor province that contains its point: Haut-Katanga, Lualaba, Haut-Lomami or Tanganyika.
  - **Left empty:**
    - a point within 2 km of a border between two of the four (measured in UTM 35S);
    - a point outside all four (sign flips are not corrected);
    - a multipoint that spans provinces;
    - 0,0 and round placeholders.
  - **Boundaries:** `minmodkg/misc/katanga_successors.geojson`, 4 polygons, 212 KB, read once per process. **Province boundaries: OCHA / Référentiel Géographique Commun, via HDX and geoBoundaries (gbHumanitarian), CC BY 3.0 IGO.**
- **The pairing fix.** A merged site takes its country and its state from the same record: the highest-ranked one that carries both. Before, two independent scans could pair one record's country with another record's state.
- **`state_or_province.state_code`**, plus `migrations/006_state_or_province_state_code.{up,down}.sql` and its row in `migrations/status.sql`. It is 006 because main already has a 005 (`005_sample_element`).
- **Cache bumps:**
  - `merge-v107` → `merge-v108`;
  - `EntityDeserFn.VERSION` `v107` → `v108`. The entity reader now writes `state_code` and the aliases, and a cached `state_or_province.json` from older code would have neither.
- **`run_acceptance.sh`:** the compare notes now give this branch's expected numbers.

## Numbers

From this repo's entity, same-as and merge stages, run locally on `ta2-minmod-data` with the data PR applied, compared with `main`.

| | before | after |
|---|--:|--:|
| `state_country_conflicts` | **5,856** | **0** |
| ↳ state repointed | | 5,543 |
| ↳ state filled from location (Katanga) | | 92 |
| ↳ state left empty | | 221 |
| `merged_with_state` | | −221 |
| `merged_with_country` (count) | | unchanged |
| merged sites whose country value changes | | 80 (73 Option A, 7 pairing fix) |

- **Per record:** 6,158 conflicting state candidates.

  | outcome | candidates |
  |---|--:|
  | repointed | 5,818 (385 of them through an alias) |
  | filled from location (Katanga) | 95 |
  | dropped, record moved to a dependency | 75 |
  | dropped | 170 |

- **No collateral changes:**
  - all 412,155 consistent candidates are kept;
  - no merged site becomes conflicted;
  - no non-conflicted merged site changes state or country.
- **Tests:** `tests/misc/test_state_repair.py` has 43 tests: the tiers, aliases, Option A including the two new pairs, and Katanga. Together with #108's `tests/test_misc.py`, 46 pass.
- **The full suite, with the Fuseki and Postgres containers:**

  | | passed | failed |
  |---|--:|--:|
  | `main` `63ab67e` | 133 | 24 |
  | this branch | 176 | 24 |

  The 24 failures are the same tests with the same errors on both. 16 of them need the `ta2-table-understanding` submodule, which was not checked out. The difference in passes is the 43 new tests.

## Stays empty on purpose

**221 merged sites keep no state.** They are listed in `P2_REVIEW_LIST.csv`, attached to this PR, with a reason group and a geometry suggestion for each.

| reason | entities |
|---|--:|
| Option A: the dependency has no state rows in the table | 73 |
| other | 50 |
| abolished units | 31 |
| Katanga: no location, outside DR Congo, placeholder, or within 2 km of a border | 15 |
| county-level names | 14 |
| islands | 14 |
| wrong recorded country | 14 |
| cities | 6 |
| Greenland | 4 |

- **A geometry suggestion is not a fix.** 22 of the suggested fills contradict the record's own state name.

## Out of scope

- **Records whose recorded country is wrong.** The repair trusts the country and never changes it, apart from the Option A list.
- **"Ozernoe":** one merged site joins two different deposits about 3,400 km apart. That is a same-as defect, not a state one.
- **Iran's `state_code`s do not follow ISO 3166-2.**
- **Albania and Guinea:** County and District rows (Albania), and Prefecture and Region rows (Guinea), cover the same areas. Those records stay ambiguous until the table is decided. This is a follow-up.

## How to verify

1. **Quick (no Docker, seconds):** `pytest tests/misc/test_state_repair.py`. 43 tests, one per rule: the tiers, aliases, Option A and Katanga.
2. **Before/after on a full build:** `run_acceptance.sh` is read-only; every query runs in a read-only transaction.

   ```bash
   ./run_acceptance.sh before     # on a build of main
   # deploy this branch and let the ETL rebuild the merged table, then:
   ./run_acceptance.sh after
   ./run_acceptance.sh compare
   ```

   - **Postgres:** it reads through the running `kgrel-version-NNN` container, or `PG_CONTAINER=<name>`, or `DATABASE_URL=postgresql://…`.
   - **Environment snapshot:** `REPO_DIR` (default `./ta2-minmod-kg`) and `KGDATA_DIR` (default `./kgdata`, the statickg workdir) give the commit and the merge-cache name.
   - **Output:** each run writes to `./acceptance_runs/before/` or `./acceptance_runs/after/` (`OUT_ROOT`).
   - **`compare`** prints each count before and after (`state_country_conflicts`, `merged_with_state`, `merged_with_country` and the rest) and diffs the two environment snapshots. "after" must list `merge-v108`.

   On `main`, `state_country_conflicts` is 5,856. On this branch it's 0, with the other changes as listed in Numbers.
3. **Spot-check after deploy:** these sites, in the MinMod UI or Postgres:

   | site | recorded country | source said (observed name) | state before | state after | why |
   |---|---|---|---|---|---|
   | `dedup_site__mrdata-usgs-gov-mrds__10021584__sri` | United States | "Florida" | Florida, Puerto Rico (`Q5307`) | Florida, United States (`Q6850`) | Three rows are named Florida, and the matcher keeps the first, Puerto Rico's. Repointed by exact name inside the United States. |
   | `dedup_site__doi-org-10-4095-295581__123__usc` | Bolivia | "La Paz" | La Pampa, Argentina (`Q2181`) | La Paz Department (`Q2453`) | No row is named "La Paz", so the matcher fuzzy-matched La Pampa, Argentina. Repointed by the name without administrative words. |
   | `dedup_site__mrdata-usgs-gov-mrds__10003861__sri` | India | "Orissa" | Garissa, Kenya (`Q3993`) | Odisha (`Q3657`) | "Orissa" was fuzzy-matched to Garissa, Kenya. Repointed through the alias Orissa → Odisha. |
   | `dedup_site__mrdata-usgs-gov-mrds__10008515__sri` | Denmark | "Greenland" | Burgenland, Austria (`Q2214`) | empty, and the country becomes Greenland (`Q1086`) | "Greenland" was fuzzy-matched to Burgenland, Austria. Greenland has its own country entry, so Option A moves the site there. |
   | `dedup_site__mrdata-usgs-gov-mrds__10038701__sri` | DR Congo | "Katanga" | Tanga, Tanzania (`Q6152`) | Haut-Katanga (`Q3000`) | "Katanga" was fuzzy-matched to Tanga, Tanzania. Katanga was split in 2015, and the site's point is in Haut-Katanga. |

## Deploy

1. **Merge the `ta2-minmod-data` PR first.** The merge cache is keyed on the site files and the same-as file, not the entity files, so a table change that lands after this build would not be picked up.
2. Build with this branch. The two cache bumps above force the entity transform and the merge to re-run.
3. Run `migrations/apply_all.sh` before starting the new API. It backs up the database, then applies every migration in order, 006 included.

## Merge order

#110 and #111 both use `merge-v108`, so build dev once, after both are merged. #115 uses `merge-v109`.

## After deploy

`acceptance/problem2_state_country_conflict.sql` is read-only (plain SELECTs):

```
PGOPTIONS='-c default_transaction_read_only=on' psql "$DATABASE_URL" -f acceptance/problem2_state_country_conflict.sql
```

- **Run it once before the deploy and once after.** The first query's count should go to 0 (5,856 on a local build of the same data); the second lists whatever is left, for triage.
- `./run_acceptance.sh before`, `after` and `compare` give the other counts (How to verify, step 2).
- **The merge cache should be `merge-v108` (or later)** in the statickg workdir (`services/mineralsiteetl/merge-v*.sqlite`). If it isn't, the merge didn't re-run and nothing will have changed.
- **Migration first:** `migrations/apply_all.sh <postgres container | postgresql://…>` before the new API starts. Then `migrations/status.sql` shows `006_state_or_province_state_code | t`.
