# P6_FIX.md: KG sync orphans numeric values (issue ta2-minmod-kg#107)

*Aditi Bombe · 2026-10-09 · branch `fix/p6-kgsync-orphan-numbers` (local, not pushed), based on `main` @ `ab1c352` (includes the #108 merge).*
*No live or dev graph was touched and no API was called. All runs are local. Run record: `probe-runs/2026-10-09-p6-fix/`.*

## Commits

| sha | message |
|---|---|
| `95628e1` | Sync: delete stored terms instead of normalized ones (#107) |
| `67340a3` | Write xsd:decimal without exponent notation |
| `20c5915` | Tests: sync must not change datatypes or leave orphans (#107) |

Formatted with **black 25.9.0**, the newest version that leaves main's versions of these files unchanged. Black 26.10 would also reformat existing SPARQL helpers in `kgsync_listener.py`, which are outside this change. Black only reflowed lines this branch adds (2 calls in `rdf_model.py`, 2 conditions in the tests), and each fix is folded into its own commit. Run C below is after formatting. Runs A and B and the probes were before it; the code is otherwise identical.

## Diff summary (3 files, +198 / −35)

| file | +/− | what |
|---|---|---|
| `minmodkg/services/sync/kgsync_listener.py` | +27 / −27 | `handle_site_update` (l. 69) and `handle_sample_update` (l. 122) now both call one private helper `_sync_graph(og, ng)` (l. 124–149). It keys triples by `(s, p, norm_literal(o))` → list of original terms. DELETE = every stored `og` term whose key is not in the new keys. INSERT = every model `ng` term whose key is not in the old keys. `norm_literal` itself, the add handlers and `handle_same_as_update` are unchanged. |
| `minmodkg/libraries/rdf/rdf_model.py` | +21 / −8 | New `lexical(value, datatype)` (l. 380–385): for `xsd:decimal` and a Python float, returns `format(Decimal(repr(x)), "f")`; anything else is unchanged. Used by all four writers: `to_triples` (l. 232–234, 242–244) and `to_graph` (l. 289–291, 299–301). |
| `tests/services/sync/test_kgsync_listener.py` | +150 / −0 | `TestKGSyncSiteDatatypes::test_site_saved_twice`, `TestKGSyncSampleDatatypes::test_sample_saved_twice`, `test_small_decimal_written_without_exponent`, plus helpers that query the store directly (`count_doubles`, `untyped_orphans`, `numbers`, `assert_stored_as_model`). |

Decimal format check: `1.25 → 1.25`, `1.0 → 1.0` (what is written today for whole numbers, kept), `12.5 → 12.5`, `5e-05 → 0.00005`, `8.9e-05 → 0.000089`, `1e+20 → 100000000000000000000`. Nothing needed stripping: `repr` is already the shortest form, and `"f"` formatting only expands the exponent.

## Tests before and after

**C. Normal run with Docker, after black** (main result). Command: `pytest -rA tests/services/sync/test_kgsync_listener.py`, using the real conftest and the real `test-kg` / `test-kgrel` containers.
- Images built locally from the repo's own Dockerfiles: `minmod-fuseki` `670676e6a842` (from `containers/fuseki`) and `minmod-postgres` `3b61d2d28efd` (from `containers/postgres`), with default build args, on Docker 29.4.0.
- One deviation: `CFG_FILE` points to a scratch copy of `tests/resources/config.yml` in which only the kgrel host is changed, `kg-postgres` → `127.0.0.1`, because `kg-postgres` does not resolve on this Mac. `/etc/hosts` was not touched.
- On main, the branch's test file (`20c5915`) was copied into a throwaway worktree of `ab1c352`.
- Logs: `{main,branch}/pytest-sync-file-docker.txt`.

| test | main `ab1c352` | branch `20c5915` |
|---|---|---|
| 1 `test_site_saved_twice` | **FAIL**: `assert 2 == 0` doubles, at the check after the first name-only update (l. 180) | pass |
| 2 `test_sample_saved_twice` | **FAIL**: `assert 2 == 0` doubles, at the check after the name-only sample update (l. 234) | pass |
| 3 `test_small_decimal_written_without_exponent` | **FAIL**: `'"0.00005"^^xsd:decimal' in ['mo:Measure', '"5e-05"^^xsd:decimal']` | pass |
| existing `test_add_site` / `test_update_site` / `test_update_same_as` | pass | pass |
| **total** | **3 failed, 3 passed** (7.6 s) | **6 passed** (8.1 s) |

This matches run B exactly. The line numbers are 2 lower than in run B because black shortened two lines above them.

Runs A and B came first, when **Docker was not running** (`failed to connect to the docker API`), so the `kg` / `kgrel` fixtures could not start their containers:

**A. Plain run, same setup as the earlier baseline** (`pytest tests`, submodule `vendor/ta2-table-understanding` initialised at `da0f8d0`):

| | passed | errors | failed |
|---|---|---|---|
| main `ab1c352` | **65** | **27** | 0 |
| branch | **66** | **29** | 0 |

- The difference is exactly the 3 new tests: test 3 passes (+1), and tests 1–2 error on Docker (+2).
- Main is 65, not the earlier 63, because #108 added 2 tests to `tests/test_misc.py` (`9cd4f56`).

**B. Docker-free harness, so tests 1–2 actually run** (`probe-runs/2026-10-09-p6-fix/jena_harness.py`):
- `FusekiDB` queries go to a throwaway **Apache Jena 5.2.0 TDB2** directory through the `tdb2.tdbquery` / `tdb2.tdbupdate` CLIs. This is the same version as `containers/fuseki/Dockerfile`, and the tarball's SHA-512 matches Apache's.
- `kgrel` is a throwaway local Postgres 18 on 127.0.0.1. The Docker image uses 17.
- The conftest's `docker run` calls are no-ops, and `httpx.post` raises.

Sync test file (`tests/services/sync/test_kgsync_listener.py` from the branch), run on each side:

| test | main | branch |
|---|---|---|
| 1 `test_site_saved_twice` | **FAIL**: `assert 2 == 0` doubles after the first name-only update (l. 182) | pass |
| 2 `test_sample_saved_twice` | **FAIL**: `assert 2 == 0` doubles after the name-only sample update (l. 236) | pass |
| 3 `test_small_decimal_written_without_exponent` | **FAIL**: `'"0.00005"^^xsd:decimal' in [..., '"5e-05"^^xsd:decimal']` | pass |
| existing `test_add_site` / `test_update_site` / `test_update_same_as` | pass | pass |
| **total** | **3 failed, 3 passed** | **6 passed** |

- On main, test 2 stops at the doubles check, so its final single-depth assertion is never reached there. The two-valued depth on main is shown by probe step S6 below.
- Full suite through the harness: main **83 passed, 9 failed**; branch **86 passed, 9 failed**. The 9 failures are the same tests on both sides and come from the harness, not the code: the backup listener needs a git repo dir, `test_mineral_site` gets 422/403 from its fixtures, and one lock-timing test runs slow on per-call JVMs.

## S1–S6 probe (`p6_repro.py`, local Jena 5.2.0 TDB2, unchanged script)

orphans / `xsd:double` literals / two-valued fields on a live node:

| step | main `ab1c352` | branch |
|---|---|---|
| S1 site add | 0 / 0 / 0 | 0 / 0 / 0 |
| S2 site update, name only | **11 / 11** / 0 | 0 / 0 / 0 |
| S3 site update, grade 1.25 → 1.3 | 11 / 11 / 0 | 0 / 0 / 0 |
| S4 sample add | 11 / 11 / 0 | 0 / 0 / 0 |
| S5 sample update, name only | **15 / 15** / 0 | 0 / 0 / 0 |
| S6 sample update, top_depth 12.5 → 12.75 | **15 / 16 / 1** | 0 / 0 / 0 |
| prod detection queries `pf1` / `o1` / `o2` on the final store | 5 / 8 / 2 rows | 0 / 0 / 0 rows |

- Main reproduces the 2026-10-07 numbers exactly.
- On the branch, S6 deletes `top_depth_m "12.5"^^xsd:decimal` and inserts `"12.75"^^xsd:decimal`. No `xsd:double` appears anywhere in the branch's SPARQL log.

## Noticed, not changed

1. **A legacy `"5e-05"^^xsd:decimal` that is already stored still gets orphaned on update** (`p6_legacy_exponent.py`: 1 orphan). This was the 🔴 open item in P6_DIAGNOSIS §7.3.
   - Cause: rdflib rewrites the lexical form to `0.00005` when it parses the CONSTRUCT result. The DELETE then asks for `"0.00005"`, and Jena treats that as a different term from the stored ill-formed `"5e-05"` (checked directly).
   - Reach: the 6 such literals in prod sit on umn/inferlink ETL sites, which this path does not edit. The next ETL rebuild writes them as `0.00005`, because ETL uses the same `to_triples` writer (`etl/mineral_site.py:477`).
   - A full fix would parse CONSTRUCT results without literal normalisation in `TripleStore.construct`. That is outside this change.
2. **A store that already holds doubles does not heal itself.** A stored `"1.25"^^xsd:double` and the model's `"1.25"^^xsd:decimal` share a key, so an unchanged value keeps its double. That is why dev needs a rebuild. Prod has 0 doubles, so nothing is needed there.
3. **Nested node URIs are still a new uuid4 on every save**, so every save deletes and re-inserts all nested triples. It now does so cleanly. Stable URIs are left for a separate issue.
4. `to_graph` decimal literals now carry a `Decimal` value instead of a `float`, because the lexical form is passed in. `_normalize_graph_for_shacl` is untouched; its decimal re-coercion is now a no-op for these, and `tests/test_validators.py` passes.
5. Non-finite floats would now write `Infinity` / `NaN` instead of `inf` / `nan`. Neither form is a legal `xsd:decimal`, before or after.
6. Existing behaviour: calling `to_graph()` on an object after `to_triples()` fails, because `to_triples` caches the nested URI as a `str`.
7. The Docker test setup did not work on this Mac as is. The `minmod-fuseki` and `minmod-postgres` images had to be built first (both are now built locally). `tests/resources/config.yml` points kgrel at `kg-postgres:15432`, which does not resolve here and has no environment override in `config.py`, so run C used a scratch config. Adding `127.0.0.1 kg-postgres` to `/etc/hosts` would make the plain command work.
