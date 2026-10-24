- **What:** (0, 0) is how extractors write "no coordinate", so the location view now treats it as missing.
  - `LocationView.from_location` drops points at exactly (0, 0), compared as numbers in the source's own CRS before reprojection, so `POINT(0 0)`, `POINT (0.0 0.0)` and `POINT(-0.0 0.0)` all count.
  - A point there gets no lat/lon. A multipoint keeps its other points, or gets no lat/lon if none are left.
  - Country and state are kept. The raw location written to the KG is unchanged.
  - One small helper, `drop_null_island`. Every writer goes through it: the ETL merge, the API create/update path and the GeoChem loader.
- **Precision tie-break:**
  - Among records tied on trust score, a more precise coordinate replaces the picked one only if it refines the same point, i.e. it lies inside the picked point's rounding box.
  - Precision is measured from the source's own WKT, ignoring padded zeros, float noise and degree-minute conversions.
  - 168 merged sites change, median 4 m, max 2.8 km.
- **Why it's limited to the same point:** 3,205 other tied sites have a "more precise" record that is a **different** location (median 0.43 km away, 99 over 50 km). Those are left alone. https://github.com/adi05b/data_issues/blob/main/p3/P3_AMANDEEP_AND_SONORA.md
- **Code:**
  - The precision and rounding-box logic is in `minmodkg/misc/coord_precision.py`.
  - Both elections, `from_sites` and `from_dedup_sites`, apply it after the current pick.
  - Both now take a required `crs_names` (a CRS's unit and grid come from the entity table), and every caller passes it from its entity service. So an API edit re-elects with the same rule.
- **Numbers** (offline rebuild on `ta2-minmod-data` `3a086a5`, and again on `0c8b827` after the rebase onto `63ab67e`, with the same result): **197 merged sites change**, coordinate only.
  - **Null Island: 37 records** lose their coordinate, all Inferlink, so **29 merged sites** change: **25** end with no point, **4** fall back to another member's point.
  - **Tie-break: 168** merged sites, none of them among the 29.
  - Nothing else changes: no other record's lat/lon, and no merged site's country, state or any other field.
- **Tests:**
  - 10 Null Island cases in `tests/test_misc.py`.
  - 8 precision cases in `tests/misc/test_coord_precision.py` (padded zeros, DMS grid, float noise in a projected CRS, a per-axis box).
  - 7 election cases in `tests/models/kgrel/test_dedup_mineral_site.py`: switches inside the box, keeps outside it, keeps a higher score, keeps an expert/curator, keeps equal precision, skips (0, 0), and switches across partials in `from_dedup_sites`.
  - The two new files are added to the Tests workflow.
  - 2 service-level cases in `tests/services/test_mineral_site_service.py` (they need the Docker test database):
    - `MineralSiteService.create` re-elects a merged site with the tie-break, with `crs_names` coming from a stubbed `EntityService.get_instance()`;
    - `EntityService.get_instance()` is a cached singleton that reads the CRS names once.
  - With either change reverted, its switching cases fail and its "keeps" cases still pass.
  - The full suite with Docker fails the same 24 tests, with the same messages, on main `63ab67e` (133 passed) and on this branch (160 passed); nothing new.
- **Cache:** `merge-v107` → `merge-v108`, because `location_view` is computed inside the merge. #110 also uses `merge-v108` (see Merge order).
- **Out of scope:** Inferlink lat/lon sign errors are a separate issue. Two of the four Null Island fallbacks look sign-flipped: Oropesa (Spain) → `MULTIPOINT(-5.475 -19.00)` and Ambatovy (Madagascar) → `MULTIPOINT(48.0 17.5)`.

## How to verify

Read-only, against any kgrel Postgres (dev or prod), with this branch checked out:

    python verify_p3.py --db "$KGREL_URL" --out p3_check/

Script: https://github.com/adi05b/data_issues/blob/main/p3/verify_p3.py

On the 28 Jul data it reports 197 changed merged sites (29 Null Island, 168 tie-break), every safety check PASS, and exit code 0. It writes nothing to the database.

Run it on a kgrel database built from current main (after #108). Prod was built before #108, so the control will report a mismatch there (exit code 2) for sites with non-WGS84 points.

## Merge order

#110 and #111 both use `merge-v108`, so build dev once, after both are merged. #115 uses `merge-v109`.

## After deploy

`acceptance/problem3_coordinates.sql` is one read-only query that returns one row per metric (`metric`, `value`, `expected`):

```
PGOPTIONS='-c default_transaction_read_only=on' psql "$DATABASE_URL" -f acceptance/problem3_coordinates.sql
```

- **Run it once before the deploy and once after.**
- **The `expected` column says what each row should show after the deploy**, with the value before it in brackets. It covers:
  - merged sites and records still at (0, 0): 29 and 37 before, 0 after;
  - the 168 tie-break sites, listed in the file: all on their more precise point;
  - the 29 Null Island sites: 25 with no point, 4 on another member's point;
  - totals that must not move, and merged sites with a coordinate (−25);
  - the funnel, rows 1–3 (198,129 / 23,283 / 23 / 18,583 before).
- **The merge cache should be `merge-v108` (or later)** in the statickg workdir (`services/mineralsiteetl/merge-v*.sqlite`). If it isn't, the merge didn't re-run and nothing will have changed.
- **With #110 in the same build**, merged sites with a state also drop by 221 (#110's state repair). No other row depends on #110.
- **Tested on a local load of the full data** (data `0c8b827`, the repo's Postgres 17.11 image). Main's build gives every "before" value and this branch's build every "expected" value, in about 15 s each.
