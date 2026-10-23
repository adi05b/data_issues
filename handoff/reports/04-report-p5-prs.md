# Report 04: Problem 5, branch updated and issue opened

*2026-10-23. Nothing pushed except `data_issues`. No PR opened. No graph, Postgres or API touched.*

## Issue

- **https://github.com/usc-isi-i2/ta2-minmod-data/issues/6**: "Problem 5: wrong commodity matches (Construction → Strontium, Oregon codes → elements)". Opened by `adi05b`.
- Body, from report 03:
  - the 7 defects with record and merged-site counts;
  - one line of root cause per source;
  - the agreed fix (corrections list in data, applied in kg, ProcMine unchanged);
  - the four open points;
  - the follow-ups.
- **One number differs from the prompt.**
  - The prompt's "~6,800 other MRDS/NC subtype mismatches caused by the same comma split" is report 03's root-only MRDS count (6,823).
  - That count also includes about 950 fuzzy mismatches that are not from the split (Halite → Alunite 450, Salt → Aluminum 450, Emery → Emerald 49).
  - So the issue gives the split's own share, **5,906 MRDS + 71 NC records**, and lists the ~950 separately as also fixed by a code-based reader.
- `p5/PR_P5_DATA.md` and `p5/PR_P5_KG.md` now start with `Part of usc-isi-i2/ta2-minmod-data#6`. The kg draft's first line also says to merge the data PR first.

## Rebase

- `ta2-minmod-kg-p5`, branch `fix/p5-commodity-corrections`: `git fetch origin` then `git rebase origin/main`, onto `63ab67e` (#113, #114). It was clean, with no conflicts.

  | | before | after |
  |---|---|---|
  | Apply commodity corrections when loading sites (Problem 5) | `0f8f5a5` | `ee028a9` |
  | Bump merge cache for commodity corrections | `8f657d0` | `e549ec1` |
  | Tests: commodity corrections | `3766487` | `1198d04` |

- No branch file overlaps #113/#114.
- #113/#114 change no file on the merge path. Their one `models/` file is the new GeoChem `sample_element` table. So the offline Step 3 numbers from report 02 still hold. They were not re-measured.
- The data branch `p5-commodity-corrections` @ `7ae473f` is still on upstream `0c8b827`. Nothing was needed there.

## Tests (rebased branch `1198d04`)

| run | result |
|---|---|
| `tests/misc/test_commodity_corrections.py`, fixture | **25 passed** |
| same, `MINMOD_DATA_DIR=<data branch 7ae473f>/data` | **25 passed** |
| full suite with Docker, **main `63ab67e`** | 133 passed, **24 failed** |
| full suite with Docker, **branch `1198d04`** | 158 passed, **24 failed**: the same 24 tests, same messages; the 25 extra passes are the new tests |
| `black` 25.9.0 `--check` on the 3 changed Python files | clean, 3 files unchanged |

**Setup:**
- The repo's own Fuseki and Postgres test images (ids `670676e6a842` and `3b61d2d28efd`), on Docker 29.4.0.
- A scratch copy of the test config pointing kgrel at the local test container, as in reports 02 and P6.
- The `vendor/ta2-table-understanding` submodule is not checked out.

**The 24 pre-existing failures:**
- 16 `FileNotFoundError` for `vendor/ta2-table-understanding/schema/geochem_v1.2.1.shacl.ttl` (12 `test_sample.py`, 4 `test_validators.py`).
- 4 `api/test_mineral_site.py`, 3 `test_backup_listener.py`, 1 `test_mineral_site_service.py`.
- Main had 23 at `45a2a16`. The new one, `test_sample.py::TestSampleElements::test_publish_writes_rows`, came with #113/#114 and has the same missing-SHACL cause.

## Not done, as asked

- Neither code branch is pushed, and no PR is opened.
- The kg worktree `ta2-minmod-kg-p5` holds `1198d04`; the data clone `p5/ta2-minmod-data` holds `7ae473f`.
- The scratch main worktree used for the suite was removed.

## PRs opened (2026-10-23)

- Data: **https://github.com/usc-isi-i2/ta2-minmod-data/pull/7**, from `adi05b:p5-commodity-corrections` @ `7ae473f` (1 commit on `0c8b827`). Body: `p5/PR_P5_DATA.md`.
- kg: **https://github.com/usc-isi-i2/ta2-minmod-kg/pull/115**, from `fix/p5-commodity-corrections` @ `3d1cdc0` (4 commits on `63ab67e`, including the acceptance query from report 05). Body: `p5/PR_P5_KG.md`. Its first line now names the data PR by number: "Merge usc-isi-i2/ta2-minmod-data#7 first".
- Both bodies start with `Part of usc-isi-i2/ta2-minmod-data#6` and carry no attribution lines.
