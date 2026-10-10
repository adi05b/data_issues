# P3 — Amandeep's question, and why Sonora changed

*Read-only. "Local" is main `ab1c352` merged on `ta2-minmod-data` `3a086a5` (`p3/run-main`, as in P3_MEASURE). "Live" is read-only SPARQL `SELECT` on `minmod.isi.edu/sparql` plus one public API `GET`. Nothing was written anywhere.*

## Part 1 — Amandeep's question

**Q1. How many merged sites have multiple source records with the same trust score?** **18,583** merged sites. That is 80% of the 23,283 merged sites with 2 or more members that have a coordinate, and in each the top trust score is shared by 2 or more of those members. 95% of these ties (17,730) are between records of **one** source, and 853 are between different sources.

**Q2. Of those, how many have a better and accurate coordinate that MinMod didn't pick?** **168.** In 3,373 sites a tied member that MinMod didn't pick is strictly more precise. But in 3,205 of them that point lies outside the picked point's rounding box: it's a different location, a conflict rather than a precision win.

| # | merged sites … | local | same source | different sources | live |
|---|---|--:|--:|--:|--:|
| 1 | with ≥ 2 member records | 198,129 | | | 198,131 |
| 2 | … of which ≥ 2 members have a coordinate | 23,283 | | | 504† |
| | *(top score held by an expert/curator: not a source tie)* | *23* | | | *504†* |
| 3 | … of which the top trust score is shared by ≥ 2 of them | **18,583** | 17,730 | 853 | 504† |
| 4 | … of which a tied, not-picked member has strictly better real precision | 3,373 | 2,922 | 451 | — |
| 5 | … of which that point lies inside the picked point's rounding box | **168** | 89 | 79 | — |
| | 4 − 5: more precise, but points somewhere else (conflicts) | 3,205 | 2,833 | 372 | — |

How each row is defined:
- **Coordinate:** the record's location view has lat/lon (live: it has a `:location` WKT).
- **Trust score:** MinMod's own `SiteScore.score`: the data-source score (0.5 if missing), capped at 0.99; experts/curators get 1.0.
- **The tie (row 3):** main breaks it by `source_id`, then `record_id`, then `modified_at`, all descending. "Same source" means every tied record has one `source_id`.
- **Real precision (row 4):** P3_MEASURE's effective precision. Trailing zeros and float noise are dropped, DMS values count at their grid (arcmin 1.86 km, arcsec 31 m), and resolution is measured in each CRS's own unit (`ground_res_km`).
- **Rounding box (row 5):** ± half a unit of the picked point's last real digit, **each axis its own** (DMS: half its grid). Raw numbers are compared when both records are POINTs in the same CRS; otherwise the WGS84 location views are compared. With a truncation box (± one unit), row 5 is 286.
- **Why not P3_MEASURE's 711:** its gate was one distance on the coarser axis. A per-axis box is stricter, and it is what "rounding box" means. Example: `POINT(-83.08333 48)` is 0 dp in latitude but 5 dp in longitude.

**What row 5 buys:** a median move of **4 m**, p95 0.81 km, max 2.8 km. 26 sites move more than 100 m, and 6 more than 1 km.
- **By distance:** ≤ 10 m 126 · 10–100 m 16 · 100 m–1 km 20 · > 1 km 6.
- **By source pair:** MRDS siblings 75 (4th vs 5th decimal), porcu → major-deposits 32, P9HTERGK siblings 11, ree → P9K1HBNT 10, ree → carbonatite 8.
- **Cosmetic cases:** some of the 168 just restate the picked value with more digits. Serra do Diamante: the DMS value `-38.9166666666667` is re-rounded to `-38.9167`, 5 m away. Friedensville moves 0 m.

**The 3,205 conflicts** sit a median 0.43 km away (p95 26.6 km, max 12,378 km).
- **By distance:** ≤ 100 m 846 · 0.1–1 km 1,312 · 1–11 km 789 · 11–50 km 159 · > 50 km 99.
- **By source pair:** MRDS siblings 2,123, P9HTERGK siblings 370, Oregon float prints 176, podchrome → P9HTERGK 165.
- 2 of them are Null Island picks.

**Ten row-5 sites** (spread across the distance range):

| moved | merged site | name | picked (source, precision, WKT) | better (source, precision, WKT) |
|--:|---|---|---|---|
| 0 m | `mrdata-usgs-gov-pp1802__768__umn` | Friedensville | sedznpb, 3 dp, `POINT (-75.405 40.5544444444444)` | pp1802, 10 dp, `POINT (-75.4049999998 40.5544444442)` |
| 1 m | `mrdata-usgs-gov-mrds__10049096__sri` | La Dorada | mrds, 4 dp, `POINT (-110.8006599999999935 29.5640999999999998)` | mrds, 5 dp, `POINT (-110.8006599999999935 29.5640900000000002)` |
| 2 m | `mrdata-usgs-gov-mrds__10089480__sri` | Lonesome | mrds, 4 dp, `POINT (-109.6181899999999985 37.4902999999999977)` | mrds, 5 dp, `POINT (-109.6181899999999985 37.4902799999999985)` |
| 3 m | `mrdata-usgs-gov-mrds__10025092__sri` | Goforth Soapstone Mine | mrds, 4 dp, `POINT (-82.7173599999999993 35.7933999999999983)` | mrds, 5 dp, `POINT (-82.7173599999999993 35.7934300000000007)` |
| 4 m | `mrdata-usgs-gov-mrds__10089566__sri` | Little Dian | mrds, 4 dp, `POINT (-109.7638000000000034 37.7389000000000010)` | mrds, 5 dp, `POINT (-109.7637600000000049 37.7388899999999978)` |
| 4 m | `mrdata-usgs-gov-mrds__10052523__sri` | Parker Magnetic Process | mrds, 4 dp, `POINT (-124.2236900000000048 43.3641999999999967)` | mrds, 5 dp, `POINT (-124.2236900000000048 43.3642400000000023)` |
| 5 m | `mrdata-usgs-gov-major-deposits__964__sri` | Serra do Diamante | sedcu, DMS arcmin, `POINT (-38.9166666666667 -6.91666666666667)` | major-deposits, 4 dp, `POINT (-38.9167 -6.9167)` |
| 22 m | `mrdata-usgs-gov-sedcu__629__sri` | Pitchers Farm - 1 | sir20105090z, 3 dp, `POINT (-61.985 45.537222)` | sedcu, DMS arcsec, `POINT (-61.9847222222222 45.5372222222222)` |
| 391 m | `mrdata-usgs-gov-carbonatite__34__sri` | Ruri Complex | ree, DMS arcmin, `POINT (34.333333333333 -0.53333333333333)` | carbonatite, DMS arcsec, `POINT (34.3344444444444 -0.53)` |
| 2.8 km | `api-cdr-land-v1-docs-documents__02282971b6ef3459b289f53b69054519af9a099a7590ec1178cedd4bd35aa7b9f8__inferlink` | Kwanika Project | inferlink, 1 dp, `POINT(-125.3 55.5)` | inferlink, DMS arcsec, `POINT(-125.333333 55.516944)` |

### The queries Amandeep can run

**(a) kgrel Postgres, rows 1–3:** `p3_amandeep.sql`. In this schema, `mineral_site.location_view` and `dedup_mineral_site.ranked_sites` are `bytea` columns holding orjson JSON, so the query reads them with `convert_from(…, 'UTF8')::jsonb`. Scores come straight from `ranked_sites`.

I tested it on a throwaway local Postgres 14. The tables were created by MinMod's own SQLAlchemy models (`mineral_site`, `dedup_mineral_site`) and loaded from run-main with `p3_sql_check.py`. It returned exactly the Python funnel, in 4.7 s:

```
row1_two_plus_members | row2_two_plus_with_coordinate | row2a_top_is_expert | row3_top_score_tied | row3_same_source | row3_different_sources
               198129 |                         23283 |                  23 |               18583 |            17730 |                    853
```

```sql
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
```

**(b) Live SPARQL, the same-score ties:** `p3_amandeep.rq` (rows 2–3) and `p3_amandeep_row1.rq` (row 1). The live graph has no merged-site nodes. But the KG writes each merge group as a star, `hub owl:sameAs member` (`same_as.py`, `step4_save`), so a group is a hub plus its objects. I tested both queries in rdflib on 4,986 run-main groups (every 40th, plus Sonora and all 32 groups with an expert/curator record), and all six counts equalled the Python ones.

Live run, once each:
- `p3_amandeep_row1.rq` returned in 1.8 s.
- `p3_amandeep.rq`: my first submission, a heavier draft that also counted members without a coordinate, was cut off by my own 300 s client limit. The lighter version shown here then ran for 1,200 s and the endpoint's nginx returned **HTTP 504** (a 20-minute gateway limit), so there is no live result for rows 2–3. I didn't retry, to avoid loading prod a third time.

```
p3_amandeep_row1.rq   row1_two_plus_members = 198131   (local 198129; the +2 is not investigated)
p3_amandeep.rq        HTTP 504 after 1200 s (live/q3-amandeep-rows2-3.504.html)
```

† **For live rows 2–3, run (a) against prod's kgrel Postgres.** It returned in under 5 s on the same data volume locally, and Postgres holds the merged sites themselves rather than the sameAs approximation. The SPARQL is correct on the sample, but it is too heavy for the shared endpoint. Splitting it, e.g. one `VALUES ?src` per source, would cost many more queries.

```sparql
PREFIX : <https://minmod.isi.edu/ontology/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

# Problem 3, Amandeep's funnel, rows 2-3, on the live graph. Read-only SELECT.
# Row 1 is p3_amandeep_row1.rq.
#
# The KG has no merged-site nodes. It writes each merge group of >= 2 records as
# a star, hub owl:sameAs member (minmodkg/etl/same_as.py, step4_save), so a
# group is a hub plus its owl:sameAs objects.
#
# Only members with a coordinate (a :location WKT) take part. Score as
# SiteScore.get_score, times 100: a creator outside /users/s/ is an
# expert/curator (100); otherwise the source's DataSource :score, 50 when missing
# or negative, capped at 99; cast to xsd:integer, since GROUP BY keeps 50 and
# 50.0 apart.
#
# key = score * 1e8 + members at that score * 1e4 + distinct sources among them;
# MAX(key) per group is the top score's row (group sizes and source counts < 1e4).

SELECT (COUNT(*)                                                 AS ?row2_two_plus_with_coordinate)
       (SUM(IF(?top = 100, 1, 0))                                AS ?row2a_top_is_expert)
       (SUM(IF(?top < 100 && ?n_top >= 2, 1, 0))                 AS ?row3_top_score_tied)
       (SUM(IF(?top < 100 && ?n_top >= 2 && ?n_src = 1, 1, 0))   AS ?row3_same_source)
       (SUM(IF(?top < 100 && ?n_top >= 2 && ?n_src >= 2, 1, 0))  AS ?row3_different_sources)
WHERE {
  {
    SELECT ?hub (SUM(?n) AS ?n_coord) (MAX(?key) AS ?topkey)
    WHERE {
      {
        SELECT ?hub ?sc (COUNT(DISTINCT ?m) AS ?n) (COUNT(DISTINCT ?src) AS ?nsrc)
        WHERE {
          { ?hub owl:sameAs ?m }
          UNION
          { SELECT DISTINCT ?hub (?hub AS ?m) WHERE { ?hub owl:sameAs ?any } }
          ?m :location_info/:location ?wkt ; :source_id ?src ; :created_by ?by .
          BIND(IRI(STR(?src)) AS ?ds)
          OPTIONAL { ?ds :score ?dss }
          BIND(xsd:integer(IF(!STRSTARTS(STR(?by), "https://minmod.isi.edu/users/s/"), 100,
                  IF(BOUND(?dss) && ?dss >= 0, IF(?dss > 0.99, 99, ROUND(?dss * 100)), 50))) AS ?sc)
        }
        GROUP BY ?hub ?sc
      }
      BIND(?sc * 100000000 + ?n * 10000 + ?nsrc AS ?key)
    }
    GROUP BY ?hub
  }
  FILTER(?n_coord >= 2)
  BIND(FLOOR(?topkey / 100000000) AS ?top)
  BIND(FLOOR((?topkey - ?top * 100000000) / 10000) AS ?n_top)
  BIND(?topkey - ?top * 100000000 - ?n_top * 10000 AS ?n_src)
}
```

**Rows 4–5** need the precision logic, which is in `p3_measure.py` (`ground_res_km`). `p3_amandeep.py` imports it, adds the rounding box, and rebuilds the picked coordinate with main's own `DedupMineralSite.from_dedup_sites`:

```
cd ~/Documents/Aditi/ISI_usc/data_issues/p3
MAIN=~/Documents/Aditi/ISI_usc/ta2-minmod-kg-p3
CFG_FILE=$MAIN/tests/resources/config.yml PYTHONPATH=$MAIN:. \
  ~/minmod-p1-p4-fix/minmod_data_issues/.venv-p2/bin/python p3_amandeep.py run-main out
```

It takes about 2.5 min and writes `out/amandeep_funnel.json`, `out/amandeep_row5.csv` (168) and `out/amandeep_conflicts.csv` (3,205).

## Part 2 — Why did Sonora change?

**It didn't. The claim was an artifact of the first election script's tie handling. MinMod never kept `POINT(0 0)` for Sonora.**

**1. The earlier method.** The claim comes from `P3_AFFECTED_RECORDS.md`'s named-examples table, produced by `probe-runs/2026-09-14/p3_election2.py`. That script did not rebuild the merge.
- **What it compared:** live-graph `owl:sameAs` pairs where **both** records have an explicit EPSG:4326 CRS (`p3.4a-coord-pairs`), union-found into groups.
- **How it elected:** `max(ms, key=lambda m: scores.get(m["src"], -1.0))`, i.e. by source score alone. Python's `max` returns the first of equals, and the list order was the CSV's `ORDER BY ?s ?o`.
- **Why it picked `(0 0)`:** Sonora's members all score 0.8, and the first member listed is the sameAs hub `0205…`, the `POINT(0 0)` record (the hub is the group's first node). So it would flag Sonora whatever the merge actually did.
- **The rerun:** the 14 Sep rerun with the real tie-break (`v_election.py`, P3_VERIFIED) elected `02ec…`, and Sonora dropped out of the 1,269: there is no Sonora row in `v1-election-corrected.csv`. But the named example in P3_AFFECTED_RECORDS, and the slides, were never retracted.
- **A second bug in that rerun, not affecting Sonora:** `v_election.py` keyed source scores by `:uri`. Inferlink's DataSource has no `:uri`, so Inferlink was scored 0.5 instead of 0.8.

**2. Group members then vs now.** The merged site has 14 members: 7 Inferlink records and an SRI copy of each. The local `groups.json`, live SPARQL and the live API all agree.
- **What the earlier view saw:** 6 of the 14, i.e. hub `0205` plus `0232`, `0249`, `0263`, `02c7`, `02ec`. Its EPSG:4326 filter dropped `02c2` (no CRS node), and the 7 SRI copies have no location at all.
- **Data history:** I made a blobless clone of `DARPA-CRITICALMAAS/ta2-minmod-data` and ran `p3_sonora_history.py` (`out/sonora_history.txt`). All 14 records are identical at `4305af5` (2025-08-23, the repo's first import), `8c052d4` (2026-07-08) and `3a086a5` (2026-07-28) in `source_id`, `record_id`, `created_by`, `modified_at` and location. So are the 21 lines naming them in `data/same-as/umn/part-0030.csv` (only ever touched by `4305af5`), and the Inferlink score (0.8).
- **What did change:** `8c052d4` touched these files only to rewrite document URIs, and `650eb4a` only removed the Polymer viewer link from the data source. No records or links were added or removed.

**3. The ranking.** All 14 records score 0.8 and share one `source_id`, so the order is `record_id` descending, then `modified_at` descending (`out/sonora_ranking.txt`; the live API lists `sites` in exactly this order):

| rank | record_id | creator | modified_at | coordinate |
|--:|---|---|---|---|
| **1** | `02ec6335…` | inferlink | 2024-11-13 23:54 | **`POINT(-109.103889 29.774722)`** ← kept |
| 2 | `02ec6335…` | sri | 2024-10-29 | — |
| 3 | `02c7aaeb…` | inferlink | 2024-12-10 20:33 | `MULTIPOINT(-110.68 30.39)` |
| 5 | `02c2ae8f…` | inferlink | 2024-12-10 20:25 | `POINT(-110.0 30.0)` (no CRS) |
| 7 | `026332f7…` | inferlink | 2024-12-18 18:19 | `POINT(-110.9149 30.0142)` |
| 9 | `02497a30…` | inferlink | 2024-12-10 23:23 | `POINT(-110 31)` |
| 11 | `0232b37b…` | inferlink | 2024-11-14 00:20 | `POINT(-110.924 29.081)` |
| **13** | `0205e384…` | inferlink | 2024-12-11 20:16 | **`POINT(0 0)`** |

The even ranks are each record's SRI copy, with no location.

- **What could flip it:** `0205…` sorts last on `record_id`, so it could only be kept if every other Inferlink record lost its coordinate, or if its own score rose above 0.8.
- **What can't:** `modified_at` only orders the two copies of one record. `DEFAULT_SOURCE_SCORE` (0.5) doesn't apply, because Inferlink has an explicit 0.8.
- **Code history** (`git log -S` on main):
  - `SystemCmpKey`, i.e. the `(source_id, record_id, modified_at)` tie-break, arrived in `7b43c78` (2025-01-27, issue #85). `site_and_score.py` was last changed in `1124d88` (2025-02-04, issue #91, deserialising the key).
  - `DEFAULT_SOURCE_SCORE` was last changed in `b340ce3` (2025-01-14), and `get_score` in `b340ce3` / `3c6625d` (Dec 2024 – Jan 2025).
  - Before `7b43c78` the key was `(score, modified_at)`, which would keep the newest record, `0263…` → `POINT(-110.9149 30.0142)`. That isn't `(0 0)` either.

**4. Live prod today.** The live graph has no merged-site nodes (P3_VERIFIED probe `p3.s4`), so SPARQL can return the members (`live/s1-sonora-members.csv`) but not the merged coordinate. That comes from the public `GET /api/v1/dedup-mineral-sites/dedup_site__…0205e384…__inferlink` (`live/a1-sonora-dedup.json`): **lat 29.774722, lon −109.103889**, and `trace.coordinates` = `site__…02ec6335…__inferlink`, with 14 sites. **Identical to local main.**

There is nothing to explain between prod and local here. Prod was built from data identical to `3a086a5` for these records, and with a ranking unchanged since Feb 2025. The earlier 14 Sep pull shows the same members, coordinates and `modified_at` values as today.

**5. Verdict.** The claim was **wrong at the time**. It was never right and then fixed: no data commit and no code commit changed Sonora's members, their coordinates, their scores or the ranking between the analysis and today. Prod, local main, and every ranking rule MinMod has had since late 2024 (on today's data) all keep `POINT(-109.103889 29.774722)` (or, before Jan 2025, `POINT(-110.9149 30.0142)`), never `POINT(0 0)`. The `(0 0)` came from `p3_election2.py` breaking a 0.8-vs-0.8 tie by list order, where the sameAs hub, which happens to be the zero record, always came first. The 14 Sep correction removed Sonora from the count but left it in the named examples. **The slides and `P3_AFFECTED_RECORDS.md` should drop Sonora.** The issue text's Sonora line goes too.

## Files

- `p3_amandeep.py` (funnel) and `p3_measure.py` (precision definitions; refactored into `load`/`rebuild_kept`, output re-checked byte-identical).
- `p3_amandeep.sql` + `p3_sql_check.py` (local Postgres check).
- `p3_amandeep.rq`, `p3_amandeep_row1.rq` + `p3_sparql_check.py` (rdflib check).
- `p3_sonora_history.py`.
- `out/amandeep_*`, `out/sonora_*`, and `live/` (live queries and responses).
