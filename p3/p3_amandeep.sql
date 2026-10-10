-- Problem 3, Amandeep's funnel, rows 1-3, against the kgrel Postgres schema.
-- One read-only SELECT. Rows 4-5 need the precision logic: see p3_amandeep.py.
--
-- mineral_site.location_view and dedup_mineral_site.ranked_sites are bytea
-- columns holding orjson JSON (DataclassType / ListDataclassType in
-- minmodkg/models/kgrel/custom_types). The scores are MinMod's own, as stored
-- in ranked_sites: [{"site_id", "score": {"score", "suborder"}}], where
-- suborder[0] is true for expert/curator records (ExpertCmpKey) and false for
-- system records (SystemCmpKey: source_id, record_id, modified_at).
--
--   psql "$KGREL_URL" -f p3_amandeep.sql

WITH member AS (
    SELECT d.id                                          AS dedup_id,
           rs ->> 'site_id'                              AS site_id,
           (rs -> 'score' ->> 'score')::float8           AS score,
           (rs -> 'score' -> 'suborder' ->> 0)::boolean  AS is_expert
    FROM dedup_mineral_site d
    CROSS JOIN LATERAL jsonb_array_elements(convert_from(d.ranked_sites, 'UTF8')::jsonb) AS rs
),
m AS (
    SELECT member.*,
           ms.source_id,
           (lv ->> 'lat') IS NOT NULL AND (lv ->> 'lon') IS NOT NULL  AS has_coord
    FROM member
    JOIN mineral_site ms ON ms.site_id = member.site_id
    CROSS JOIN LATERAL (SELECT convert_from(ms.location_view, 'UTF8')::jsonb AS lv) v
),
g AS (   -- per merged site: members, members with a coordinate, top score among those
    SELECT dedup_id,
           COUNT(*)                              AS n_members,
           COUNT(*) FILTER (WHERE has_coord)     AS n_coord,
           MAX(score) FILTER (WHERE has_coord)   AS top
    FROM m
    GROUP BY dedup_id
),
t AS (   -- the members with a coordinate that hold that top score
    SELECT g.dedup_id,
           COUNT(*)                     AS n_top,
           COUNT(DISTINCT m.source_id)  AS n_top_sources,
           bool_or(m.is_expert)         AS expert_top
    FROM g
    JOIN m ON m.dedup_id = g.dedup_id AND m.has_coord AND m.score = g.top
    GROUP BY g.dedup_id
)
SELECT
    COUNT(*) FILTER (WHERE n_members >= 2)                                     AS row1_two_plus_members,
    COUNT(*) FILTER (WHERE n_coord >= 2)                                       AS row2_two_plus_with_coordinate,
    COUNT(*) FILTER (WHERE n_coord >= 2 AND expert_top)                        AS row2a_top_is_expert,
    COUNT(*) FILTER (WHERE n_coord >= 2 AND NOT expert_top AND n_top >= 2)     AS row3_top_score_tied,
    COUNT(*) FILTER (WHERE n_coord >= 2 AND NOT expert_top AND n_top >= 2
                       AND n_top_sources = 1)                                  AS row3_same_source,
    COUNT(*) FILTER (WHERE n_coord >= 2 AND NOT expert_top AND n_top >= 2
                       AND n_top_sources >= 2)                                 AS row3_different_sources
FROM g
LEFT JOIN t USING (dedup_id);
