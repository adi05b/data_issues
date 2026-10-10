# Treat POINT (0 0) as a missing coordinate in the location view (Problem 3)

- **What:** (0, 0) is how extractors write "no coordinate", so the location view now treats it as missing.
  - `LocationView.from_location` drops points at exactly (0, 0), compared as numbers in the source's own CRS before reprojection, so `POINT(0 0)`, `POINT (0.0 0.0)` and `POINT(-0.0 0.0)` all count.
  - A point there gets no lat/lon. A multipoint keeps its other points, or gets no lat/lon if none are left.
  - Country and state are kept. The raw location written to the KG is unchanged.
  - One small helper, `drop_null_island`. Every writer goes through it: the ETL merge, the API create/update path and the GeoChem loader.
- **Numbers** (offline rebuild on `ta2-minmod-data` `3a086a5`):
  - **37 records** lose their coordinate, all Inferlink.
  - **29 merged sites** change: **25** end with no point, **4** fall back to another member's point.
  - Nothing else changes: no other record's lat/lon, and no other merged site's coordinate, country or state.
- **Tests:**
  - 10 new cases in `tests/test_misc.py`, next to the reprojection tests, which the Tests workflow already runs. They cover every spelling of (0, 0), an all-zero multipoint, a partly zero multipoint, (0, 0) in a projected CRS, and four real points that must not change. With the fix reverted, the 6 Null Island cases fail and the 4 unchanged cases still pass.
  - The full suite with Docker fails the same 23 tests on main and on this branch; nothing new.
- **Cache:** `merge-v107` → `merge-v108`, because `location_view` is computed inside the merge. #110 also bumps `merge-v107` → `merge-v108`, so **whichever of this PR and #110 merges second should move it to `merge-v109`**.
- **Precision tie-break not included:** The precision tie-break discussed for Problem 3 is not included. Measured, it would refine only 168 merged sites, by a median of 4 m: https://github.com/adi05b/data_issues/blob/main/p3/P3_AMANDEEP_AND_SONORA.md
- **Out of scope:** Inferlink lat/lon sign errors are a separate issue. Two of the four fallbacks look sign-flipped: Oropesa (Spain) → `MULTIPOINT(-5.475 -19.00)` and Ambatovy (Madagascar) → `MULTIPOINT(48.0 17.5)`.
