"""Measurement only, never on a real build: with P3_NULL_ISLAND_OFF=1 and this
directory on PYTHONPATH, every process (including joblib's loky workers, which
re-import modules) runs fix/p3-null-island with the Null Island step disabled,
so the tie-break can be measured on its own."""

import os

if os.environ.get("P3_NULL_ISLAND_OFF") == "1":
    import minmodkg.models.kgrel.custom_types.location as location

    location.drop_null_island = lambda geometry: geometry
