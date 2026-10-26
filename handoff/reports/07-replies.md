# Replies for #110 and #111

One per comment, to post under it. Commit ids are on the local branches until they are pushed.

## #110 (review, 2026-10-26)

**1. Curator's country**
> Fixed in `0401627`. The merged country is again the top-ranked record's, so the curator's. The state now comes only from the highest-ranked record in that country, otherwise it stays empty. Same rule in `from_sites` and `from_dedup_sites`. Tests are in `tests/misc/test_state_repair.py`: a curator with a country only, merged with a higher-scored source that has both, in one partial and across two. On the full data (`0c8b827`) there are no curator records, but 8 system-record sites change. 7 keep the top record's country with no state, and 1 gets a state from a record in its own country. Conflicts stay 0, and the empty states go from 221 to 228. The PR body lists the 7 (`29b2c72` updates the compare notes).

**2. Cache key on the entity file**
> Fixed in `6ebb5e4`. `MergeFn.invoke` now takes `state_or_province_file`, the entity stage's `state_or_province.json`, keyed by its content next to `corrections_files`. A new test shows that adding an alias re-runs a cached merge.

**3. Duplicates on the repoint path**
> Fixed in `90d27ca`. The repoint path now skips a state that's already listed, as the Katanga path does. The new test is a US record with Florida (PR) twice, Florida (PR) + (UY), and Florida (US) + (PR): each gives `['Q6850']`.

**4. Cache version and rebase**
> Rebased onto `c8f4471` (#115 and #116) with `merge-v111`, and `corrections_files` stays in `cache_ser_args`. #111 now uses `merge-v110`; I'll rebase this again once #111 is merged. The rebase also needed `45d5ace`: #115's merge tests now write a `state_or_province.json`, which the merge reads.

**5. Formatting**
> Fixed in `9e0e0e7`: black and `ruff format --check` are clean on `tests/misc/test_state_repair.py`. Black is clean on all 12 Python files this PR touches. Ruff also wants two lines changed in `etl/mineral_site.py` and `services/kgrel_entity.py`, but those lines are the same on main, so I left them.

## #111 (conversation, 2026-10-26)

**1. Cache version**
> Done. Rebased onto `c8f4471`, the cache line resolved to `merge-v110`, and `corrections_files` is still in `cache_ser_args`. The acceptance query's header now says `merge-v110` (`29805e8`). #110 takes `merge-v111`. `4d236e4` updates the query's #110 note from 221 to 228, after the #110 review change.

**2. Failing unit-tests check**
> Thanks. The rebase includes #116, so the check will run on `ubuntu-24.04` once I push.
