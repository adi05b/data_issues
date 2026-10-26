# Report 07: #110 and #111 after Amandeep's review

*2026-10-26. Both kg branches are rebased onto `c8f4471`. After your review they were **pushed** (#111 first), both PR bodies were updated, the replies were posted, and CI passed on both: see Pushed, posted, CI at the end. No live graph, Postgres or API was touched: every load went into a throwaway local Postgres.*

**New heads:** #110 `fix/p2-state-repair` → **`29b2c72`** (was `04a79c7`), then **`34759de`** (CI list, see the end). #111 `fix/p3-null-island` → **`4d236e4`** (was `d995f62`).

Reply text: `handoff/reports/07-replies.md`; posted as one comment per PR (links at the end).

## The review

Read with `gh pr view --comments` and the `pulls/N/comments` and `pulls/N/reviews` APIs, for both PRs:
- #110 has one review, CHANGES_REQUESTED on `04a79c7`, with 5 points. It has no line comments and no conversation comments.
- #111 has one conversation comment with 2 points. It has no reviews and no line comments.

The review is a summary, not line comments, so the file and line column gives where each point lands, at the reviewed commit.

| # | file and line | his words (exact) | asks for | kind |
|---|---|---|---|---|
| 110-1 | `minmodkg/models/kgrel/dedup_mineral_site.py:223` and `:297` | "This lets a source record override a curator's country. A curator who corrects only the country has no state, so their site is skipped and the merged country comes from a lower-ranked source that has both. This affects both `from_sites` and `from_dedup_sites`. Please add a test with a curated site that has a country only, merged with a source that has both; the merged country must be the curator's." | The curator's country must win; add that test for both functions. | Clear for the country. The state was a decision (below). |
| 110-2 | `minmodkg/etl/mineral_site.py:402` (`cache_ser_args`) | "Any later edit to `state_or_province.csv`, such as a new alias, is ignored on a cached build until someone bumps the version again. Please add the entity file's ident to `cache_ser_args`, the way #115 does for `corrections_files`." | Key the merge cache on the state entity file. | Clear fix |
| 110-3 | `minmodkg/models/kgrel/custom_types/location.py:173` | "In `LocationView.from_location`, the repoint path doesn't remove duplicates. Two candidates for Florida, Puerto Rico on a US record give ['fl_us', 'fl_us']. The Katanga path already checks state not in states; please do the same on the repoint path." | Skip a state already listed on the repoint path. | Clear fix |
| 110-4 | `minmodkg/etl/mineral_site.py:401`, `run_acceptance.sh:130`, PR body "Merge order" | "#115 is merged with merge-v109, and #111 is moving to merge-v110. Please rebase onto main after #111 and use merge-v111, keeping the corrections_files entry in `cache_ser_args`. Rebasing also picks up #116's CI fix." | Rebase, use `merge-v111`, keep `corrections_files`. | Clear, but it conflicted with prompt 07 (`merge-v110` on both). You chose his version. |
| 110-5 | `tests/misc/test_state_repair.py` | "black --check / ruff format --check want to reformat tests/misc/test_state_repair.py." | Format the test file. | Clear fix |
| 111-1 | `minmodkg/etl/mineral_site.py:403`, PR body line 29 | "#115 is merged with `merge-v109`. When you rebase, please use `merge-v110` and keep #115's `corrections_files` entry in `cache_ser_args`. A `merge-v108.sqlite` built before #115 has no commodity corrections, so reusing that name could undo them on a cached build. #110 should then take `merge-v111`." | Rebase with `merge-v110`, keep `corrections_files`. | Clear fix |
| 111-2 | CI (`.github/workflows/tests.yml`) | "The failing `unit-tests` check is not this PR. `ubuntu-latest` moved to `ubuntu-26.04`, where `pygraphviz` 1.14 fails to build during `poetry install`, and `main` fails the same way. #116 pins the runner to `ubuntu-24.04`. Once it is merged, the rebase picks it up." | Nothing to change; the rebase brings #116. | Information |

**Two decisions were asked before any code changed:**
1. **Cache names.** Prompt 07 said `merge-v110` on both; Amandeep (110-4, 111-1) asked for #111 → `merge-v110` and #110 → `merge-v111`. **You chose his version.**
2. **110-1, where the state comes from** when the top record has a country and no state. **You chose:** from the highest-ranked record in the merged country, otherwise none.

## Step 2: rebases onto `c8f4471` (#115 and #116)

| branch | before | rebased (pre-review) | conflicts |
|---|---|---|---|
| #111 `fix/p3-null-island` | `d995f62` | `cb50370` | one: the cache line in `minmodkg/etl/mineral_site.py`, `merge-v109` vs `merge-v108`. Resolved to **`merge-v110`**. |
| #110 `fix/p2-state-repair` | `04a79c7` | `8e458fe` | one: the same line. Resolved to **`merge-v111`**. |

- No other conflict on either branch. `tests.yml` merged cleanly, keeping #116's runner pin and #111's two test files.
- Both keep #115's `corrections_files` parameter, its `cache_ser_args` entry, the call site and `CommodityCorrections.from_file`.
- **One problem caused by the rebase itself, outside the review:** on #110, 2 of #115's merge tests failed with `FileNotFoundError: …/entities/state_or_province.json`, because #110's merge reads the state table. Both tests are in CI's list. Fixed in `45d5ace`, a two-line test fixture change: the fixture also writes `state_or_province.json`.

## What changed, per comment

### #110 (`8e458fe` → `29b2c72`, 6 commits)

| commit | comment | change |
|---|---|---|
| `9e0e0e7` Format the state repair tests with black | 110-5 | `black` on `tests/misc/test_state_repair.py`, two places. `black --check` passes on all 12 Python files the PR touches. `ruff format --check` also passes on the test file; it wants two lines in `etl/mineral_site.py` and `services/kgrel_entity.py` that are identical on main, so they are left alone. |
| `90d27ca` Drop duplicate states on the repoint path | 110-3 | `if state not in states` on the repoint path. New test: on a US record, Florida (PR) twice, Florida (PR) + (UY), and Florida (US) + (PR) all give `['Q6850']`. The test fails before the fix. |
| `45d5ace` Give the commodity correction merge tests a state_or_province entity file | (rebase) | see Step 2 |
| `6ebb5e4` Key the merge cache on the state_or_province entity file | 110-2 | `MineralSiteETLService.merge` builds `InputFile.from_relpath(entity_dir / "state_or_province.json")` and passes it to `MergeFn.invoke` as `state_or_province_file`. `cache_ser_args` keys it with `get_ident()`, which includes the file's sha256. New test `test_merge_cache_is_keyed_on_the_state_file`: a cached merge is reused, and adding an alias re-runs it. With a path-only key, the test fails on the alias step. |
| `0401627` Keep the top record's country; take the state from a record in that country | 110-1 | Both functions: the merged country is the old scan again (the highest-ranked record with a country). The merged state is the highest-ranked state from a record (or partial merge) that has countries, all of them in the merged country. With no merged country, the old top-state scan is kept. A new helper does the check: `state_fits(record_countries, countries)`. The two "both" override blocks from `03e86a9` are gone, so the diff against main is now a hoisted country scan and one condition on the state scan. Three new tests: the curator case in `from_sites` and across two partials in `from_dedup_sites`, a state from a same-country record, and a state-only record is never paired with a country. On old #110, 2 fail (the curator case and the same-country case); on main, all 3 fail. |
| `29b2c72` Acceptance notes: numbers for the country/state rule | 110-1 | `run_acceptance.sh` compare notes: drops by 228 (5,536 repointed + 92 Katanga), and 74 country changes, all Option A. |
| `1490e1a` Acceptance notes: the merge cache is now merge-v111 | 110-4 | The `run_acceptance.sh` note: `merge-v108` → `merge-v111`. The cache line itself was resolved in the rebase. |

(Listed in topic order, not commit order. Commit order: `9e0e0e7`, `90d27ca`, `45d5ace`, `6ebb5e4`, `0401627`, `1490e1a`, `29b2c72`.)

### #111 (`cb50370` → `4d236e4`, 2 commits)

| commit | comment | change |
|---|---|---|
| `29805e8` Acceptance query: the merge cache is now merge-v110 | 111-1 | The header of `acceptance/problem3_coordinates.sql`: `merge-v108` → `merge-v110`. |
| `4d236e4` Acceptance query: #110 now lowers the state count by 228 | none (**beyond the comments**) | The header and the "merged sites with a state" `expected` text: 221 → 228, because of the 110-1 change. It touches comment and label text only, not the numbers the query computes. Drop it if you'd rather keep #111 to his two points. |

111-2 needs no change: the rebase includes #116.

## Open decisions

### 1. Should the top record's country win for system records too, or only for curators?

**Decided 2026-10-26: option 1, for all records.** The branches stay as committed.

**What 110-1 does now:** on the full data there are **no curator records**, so the curator rule never fires. The rule as chosen still changes **8 system-record sites** compared with #110 before the review. In each one, the top-ranked record has a country but no usable state, and old #110 took a lower-ranked record's country and state.

| site | old #110 (lower record's pair) | now (top record's country) | which looks right |
|---|---|---|---|
| Aljustrel (`…0283468d…inferlink`) | Canada / British Columbia | Portugal / Beja | **now** |
| Reef Ridge (`…reef-ridge-837__usc`) | United States / Alaska | Uganda / none | **old** |
| Su-Lik (`…su-lik-843__usc`) | United States / Alaska | Uganda / none | **old** |
| Mount Keith (`…mrds__10256361`) | Australia / Western Australia | Christmas Island / none (top record moved by Option A) | **old** |
| Whistler (`…02c4dfe3…inferlink`) | United States / Washington | Canada / none | old for the country |
| phosphate 1134 / 1 / 954 | Thailand / Roi Et; Afghanistan / Helmand; Australia / Queensland | Solomon Islands; Pakistan; New Zealand; no state | unclear: equal scores, members in different countries (a same-as defect) |

The member records behind each site, in rank order, are in `p2/out/p2_review_8_sites.txt`.

**Options:**
1. **Keep it as is (my pick).** The merged country is the top-ranked record's, as for every other merged field (name, type, coordinates). It is the simplest rule and does what the comment asks. The 7 sites are listed in the PR body. The wrong top-ranked countries (Uganda for two Alaska sites, Christmas Island for Mount Keith) are source data errors, better fixed by a curator, who will now win.
2. **Curators only.** A curator's or expert's country always wins (the same state rule as now). Among system records, keep old #110's pair rule. On this data that gives exactly the pre-review numbers (80 country changes, 221 empty), and the curator test still passes. The cost is two rules instead of one, and a lower-ranked source can still override a higher-ranked source's country.
3. **Option 1, plus a list.** Add the 4 likely-wrong top-ranked records to the P2 review list, for a curator to fix.

### 2. The 7 new empty-state sites in `P2_REVIEW_LIST.csv`

**Done.** The CSV now has 228 rows: the 221, unchanged byte for byte, plus the 7, in the same columns and `review_list.py`'s sort order.
- **Reef Ridge, Su-Lik, Mount Keith, Whistler:** `wrong recorded country`, with the note "top-ranked record's country looks wrong; needs a curator fix". These are the 4 wrong-country sites, so they are not listed twice.
- **The three phosphate sites:** `other`, with the note "the merged site joins records from different countries; a same-as question".
- **`observed_state`:** what the source wrote for main's conflicting state.
- **Geometry columns:** "not checked: not in run C's emptied set". Every other row's suggestion comes from run C's point-in-shape check, which never saw these 7.
- **The #110 body's reason table** is updated to match: other 53, wrong recorded country 18.
- **`p2c/review_list.py`** still writes only the 221 (from run D). Re-running it would drop the 7.

## Tests

The full suites ran with a scratch copy of `tests/resources/config.yml` in which only the kgrel host is changed to the loopback address, as in P6_FIX: the configured host doesn't resolve on this Mac.

| | passed | failed |
|---|--:|--:|
| full suite with Docker, main `c8f4471` | 158 | 24 |
| full suite with Docker, #110 `1490e1a` | 206 | 24 |
| full suite with Docker, #111 `29805e8` | 185 | 24 |
| #110's own tests (`tests/misc/test_state_repair.py`, `tests/test_misc.py`, `tests/misc/test_commodity_corrections.py`) | 76 | 0 |
| #111's own tests (`tests/test_misc.py`, `tests/misc/test_coord_precision.py`, `tests/models/kgrel/test_dedup_mineral_site.py`, `tests/misc/test_commodity_corrections.py`) | 53 | 0 |

- **The 24 failures are the same tests with the same messages on all three:**
  - 16 need the `vendor/ta2-table-understanding` SHACL files (12 in `test_sample.py`, 4 in `test_validators.py`);
  - 4 are API tests;
  - 3 are backup-listener tests;
  - 1 is the mineral-site service upsert.

  This is report 06's baseline. Main has 25 more passes than in report 06 (133 → 158): #115's tests.
- **#110: +48 passes,** the state repair tests (43 before, plus 5 new). **#111: +27,** as in report 06.
- **Final heads:** `29b2c72` and `4d236e4` differ from the tested heads only in `run_acceptance.sh` and in the SQL comment and label text.
- **A local merge of the two branches** (`git merge-tree`; nothing committed) conflicts only on the cache line. `dedup_mineral_site.py` merges cleanly.
  - On that tree, #110's three new merge tests fail, because #111 makes `crs_names` a required argument of `from_sites` and `from_dedup_sites`.
  - With `crs_names={}` added to the test helpers, all 101 unit tests of both PRs pass.
  - That edit belongs in #110's rebase after #111 merges; it can't be made now, since #110 alone has no `crs_names`. The PR body says so.

## The full data, before and after

- **Data:** P5's clone at `7ae473f`, which is `0c8b827` plus `data/corrections/commodity.csv`. Main now reads that file (#115), and so do both branches.
- **Builds:** offline merges with `p2c/rerun/scripts/p2d_run_merge.py` and `p5/p5_etl.yml`, with `PYTHONHASHSEED=0`, about 1 to 2 minutes each.

  | build | code | merge cache |
  |---|---|---|
  | main | `c8f4471` | `merge-v109` |
  | #110 before review | `8e458fe` | `merge-v111` |
  | #110 | `1490e1a` | `merge-v111` |
  | #111 | `29805e8` | `merge-v110` |

- **Loads:** with `p5/p5_load_kgrel.py`, into the repo's Postgres 17.11 image (`3b61d2d28efd`).
  - The container was published on the loopback address only, with a 256 MB WAL and a stop below 2 GB free disk. One database at a time, dropped after its queries; the container is removed.
  - Each load: 419,098 merged sites and 679,778 records, 1,749 MB.
  - **Loader change:** it now also fills `country` and `state_or_province` from the run's entity files, because the P2 query joins them. Nothing else in it changed.
- **Queries** ran with `PGOPTIONS='-c default_transaction_read_only=on'`. The P2 query takes 2 s, the P3 query 12 to 14 s.

### #110: `acceptance/problem2_state_country_conflict.sql`

| | main | #110 |
|---|--:|--:|
| merged entities with a state in another country | **5,856** | **0** |
| query 2, the triage list | grouped by observed name: Florida 1,649, La Paz 531, Potosi 528, … | 0 rows |

From the P3 query's sanity rows on the same two loads:

| | main | #110 |
|---|--:|--:|
| merged sites with a state | 374,202 | **373,974** (−228) |
| merged sites with a country | 402,429 | 402,429 |
| merged sites total / raw sites | 419,098 / 679,778 | unchanged |

Offline, with `p2/p2_review_diff.py` (electing every merged site as the loader does; `p2/out/p2_review_diff.txt`):

| | #110 before review | #110 now |
|---|--:|--:|
| conflicts | 0 | 0 |
| merged sites changed vs main | 5,856 (exactly the conflicted set) | 5,856 (exactly the conflicted set) |
| state repointed / Katanga / left empty | 5,543 / 92 / 221 | **5,536 / 92 / 228** |
| country value changes | 80 (73 Option A + 7 pairing) | **74 (all Option A)** |
| merged sites that differ between the two | | **8** (all 110-1; see Open decisions) |
| records whose location view differs between the two | | **0** (110-3 changes nothing on this data; no record has two candidates that repoint to the same state) |

- **The pre-review numbers reproduce exactly on `c8f4471`:** 5,543 / 92 / 221 and 80 country changes, so the rebase changes nothing.
- **The P2 per-record numbers in the PR body are unchanged:** 6,158 candidates, 5,818 repointed, 95 Katanga, 75 moved, 170 dropped.

### #111: `acceptance/problem3_coordinates.sql`

Before is main's build, after is #111's build. Raw outputs: `p3/out/p3_acceptance_07_main.txt` and `p3/out/p3_acceptance_07_branch.txt`.

| metric | before | after | expected | match |
|---|--:|--:|---|---|
| merged sites whose point is (0, 0) | 29 | 0 | 0 (before 29) | yes |
| raw sites whose lat/lon is (0, 0) | 37 | 0 | 0 (before 37) | yes |
| tie-break (168 listed): on the expected point | 0 | 168 | 168 (before 0) | yes |
| Null Island (25 listed): now with no point | 0 | 25 | 25 (before 0) | yes |
| Null Island (4 listed): on another member's point | 0 | 4 | 4 (before 0) | yes |
| merged sites total | 419,098 | 419,098 | unchanged | yes |
| raw sites total | 679,778 | 679,778 | unchanged | yes |
| merged sites with a coordinate | 400,446 | 400,421 | 400,421 (before 400,446) | yes |
| merged sites with a country | 402,429 | 402,429 | unchanged | yes |
| merged sites with a state | 374,202 | 374,202 | unchanged; 228 lower with #110 | yes (373,974 on the #110 load) |
| funnel 1 | 198,129 | 198,129 | unchanged | yes |
| funnel 2 | 23,283 | 23,281 | 23,281 (before 23,283) | yes |
| funnel 2a | 23 | 23 | unchanged | yes |
| funnel 3: tied | 18,583 | 18,580 | 18,580 (before 18,583) | yes |
| funnel 3: same source | 17,730 | 17,728 | 17,728 (before 17,730) | yes |
| funnel 3: different sources | 853 | 852 | 852 (before 853) | yes |

- **Every value matches**, and both columns are identical to report 06's.
- **The "before" is now from the final committed file.** In report 06 it came from a draft.
- **#111 doesn't move the P2 count:** 5,856 on its build, as on main.
- **The offline cross-check** (`p3/p3_merged_diff.py`, `p3/out/p3_merged_diff_07.txt`) finds 197 changed merged sites: 25 / 4 / 168, all of them listed. Each goes from its listed old record to its listed new one. No listed site is unchanged, and no other field changes.

## PR text

- **`PR_110_BODY.md`:**
  - rebased on `c8f4471`;
  - data#5 shown as merged;
  - the new country/state rule;
  - cache `merge-v109` → `merge-v111`, plus the state file in the cache key;
  - Deploy step 1 (merge the data PR first, because the cache ignored entity files) is removed;
  - the numbers above, the 7 extra empty sites, and the tests (48 new; suites 158 / 24 and 206 / 24);
  - Merge order: #111 first, then #110 rebases, including the `crs_names={}` note;
  - After deploy: `merge-v111`.
- **`p3/PR_111_BODY.md`:**
  - cache `merge-v109` → `merge-v110`, keeping `corrections_files`;
  - the same Merge order;
  - the suites at 158 / 24 and 185 / 24;
  - the #110 effect, 228;
  - After deploy: `merge-v110`;
  - tested on `c8f4471`.
- Nothing is pasted into GitHub.

## Push commands (run after review; results at the end)

From this folder (`data_issues`). `--force-with-lease` names the current PR heads, so each push refuses if anyone has pushed since. Both heads were checked just now: `04a79c7` and `d995f62`.

```bash
git -C ../ta2-minmod-kg-p2 push --force-with-lease=fix/p2-state-repair:04a79c7 origin fix/p2-state-repair
git -C ../ta2-minmod-kg-p3 push --force-with-lease=fix/p3-null-island:d995f62 origin fix/p3-null-island
```

Then paste `PR_110_BODY.md` into #110 and `p3/PR_111_BODY.md` into #111, and post the replies from `07-replies.md`.

## Files in this folder

- `p2/p2_review_diff.py`: a new offline election and diff for country and state;
- `p2/out/p2_review_diff.txt` and `p2/out/p2_review_8_sites.txt`;
- `p2/out/p2_acceptance_07_{main,branch}.txt`;
- `p2/out/p3_query_on_110_build_07.txt`;
- `p3/out/p3_acceptance_07_{main,branch}.txt`;
- `p3/out/p3_merged_diff_07.txt`;
- `p5/p5_load_kgrel.py`: now also loads the two entity tables.

**Scratch:** the venv, code snapshots, the four run dirs and the logs were in the session's scratch directory and are deleted, now that decision 1 is settled. No shared database was used, and the throwaway Postgres container is removed.

## Pushed, posted, CI (after review)

**P2_REVIEW_LIST.csv first:** the 7 sites were added (see Open decisions, 2). The #110 body's counts were updated to match before it was pushed.

**Pushes, #111 first:**

| PR | push | PR head on GitHub | live body |
|---|---|---|---|
| [#111](https://github.com/usc-isi-i2/ta2-minmod-kg/pull/111) | `+ d995f62...4d236e4 fix/p3-null-island (forced update)` | `4d236e4`, open, mergeable | matches `p3/PR_111_BODY.md` |
| [#110](https://github.com/usc-isi-i2/ta2-minmod-kg/pull/110) | `+ 04a79c7...29b2c72 fix/p2-state-repair (forced update)` | `29b2c72`, open (mergeable still being computed when checked) | matches `PR_110_BODY.md` |

The bodies were set with `gh pr edit --body-file`. Each live body was compared with its file: identical, apart from the API's trailing newline.

**Replies:**
- **Not in threads, as asked:** the PRs have no review threads (GraphQL `reviewThreads` is 0 on both, and there are no line comments).
  - #110's feedback is the summary of a review (CHANGES_REQUESTED);
  - #111's is a conversation comment;
  - GitHub has no thread replies for either.
- **One comment per PR instead, as you chose:** each of his points is quoted in his own words, with the reply from `07-replies.md` under it.
  - The #110 point 1 reply was rewritten first, as you asked: the top record's country wins for all records, the state comes only from a record in that country, and 228 states are left empty instead of 221. 8 sites change: 7 are left without a state (listed in the PR body and the CSV), and Aljustrel gets a state from a Portuguese record. The PR body lists the 7, not all 8, so the reply says that.
  - #111 point 2 now says the check runs on `ubuntu-24.04`, not "once I push".
- **Posted** as adi05b; each posted body matches what was composed. **No threads were resolved.**
  - #110: https://github.com/usc-isi-i2/ta2-minmod-kg/pull/110#issuecomment-6429748520
  - #111: https://github.com/usc-isi-i2/ta2-minmod-kg/pull/111#issuecomment-6429748867

**CI (`Tests` / `unit-tests`, `pull_request`): both pass, on the `ubuntu-24.04` image.**

| PR | commit | run / job | result |
|---|---|---|---|
| #110 | `29b2c72` | [run 40419542271](https://github.com/usc-isi-i2/ta2-minmod-kg/actions/runs/40419542271/job/121910237299) | success, 105 passed, 1m31s |
| #111 | `4d236e4` | [run 40419499723](https://github.com/usc-isi-i2/ta2-minmod-kg/actions/runs/40419499723/job/121910091953) | success, 130 passed, 52s |

**Then added, as you asked:** #110 had never put `tests/misc/test_state_repair.py` in the workflow's test list (#111 added its two files), so CI didn't run #110's 48 state repair tests.
- **The change:** commit `34759de` "Run the state repair tests in CI", one line in `.github/workflows/tests.yml`, after `test_commodity_corrections.py`. #111 adds its lines elsewhere, and a trial merge of the two branches merges `tests.yml` cleanly.
- **Locally, CI's exact list:** 137 passed. The 16 failures are the SHACL tests, which need the submodule CI checks out.
- **Pushed** as a fast-forward, `29b2c72..34759de`; #110's head on GitHub is `34759de`.
- **CI:** [run 40420662402](https://github.com/usc-isi-i2/ta2-minmod-kg/actions/runs/40420662402/job/121913977962), `unit-tests` success on `ubuntu-24.04`, 3m50s: **153 passed** (105 before, plus the 48 state repair tests, all PASSED).
