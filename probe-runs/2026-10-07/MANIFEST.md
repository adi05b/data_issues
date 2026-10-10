# probe-runs/2026-10-07 — Problem 6 (issue ta2-minmod-kg#107) run manifest

*Aditi Bombe · run 2026-10-07 (US Pacific; UTC timestamps in `.meta.json` read 2026-10-08T00:4x–00:5x) · read-only.*

No SPARQL write was sent to any real store. Every live query is SELECT or ASK, sent by POST through
`../run_probe.py` to `https://minmod.isi.edu/sparql`. TLS verification was never disabled. No editor or API
route was called. No repository was modified: `ta2-minmod-kg`, `ta2-minmod-dashboard`, and `ta2-minmod-editor` were cloned read-only into `/tmp`,
and `git status` on the kg clone was still clean at the end.

## Code under test

| repo | commit | date |
|---|---|---|
| usc-isi-i2/ta2-minmod-kg | `83f9b7b2580790b2c7e197610ae905bd23c49a74` (main) | 2026-09-29 |
| usc-isi-i2/ta2-minmod-editor | `32723554acadfec8e9bc665bb685ffa94ab7b89f` (main) | 2026-09-24 |
| usc-isi-i2/ta2-minmod-dashboard | `f71800dd58b45bed3df4db1769f3c1933b67bc71` (main) | 2025-06-22 |

`p6-issue107.json` is a snapshot of the issue as read (title, body, author, no comments).

## Live queries (production, SELECT/ASK only)

| id | what | rows | ms |
|---|---|---|---|
| `p6-pf0-ask` | reachability (`ASK`; the runner's `KeyError: 'vars'` is just its CSV step on an ASK body) | true | 362 |
| `p6-pf1-double-any` | any `xsd:double` on the 10 edit-reachable numeric predicates, LIMIT 5 | **0** | 11,014 |
| `p6-c1-decimal-control` | same filter with `xsd:decimal`, as a control | 5 | 91 |
| `p6-c2-created-by` | sites per owner, first/last `modified_at` | 10 | 9,824 |
| `p6-c3-geochem-presence` | count of `gco:grade` triples | 0 | 78 |
| `p6-o1-untyped-numeric` | nodes that still have a numeric triple but no `rdf:type` (the orphan signature) | **0** | 11,416 |
| `p6-o2-issue-element-query` | the issue's own Element-orphan SELECT, LIMIT 100 added | **0** | 226 |
| `p6-v1-kg-version` | `mr:kg dcterms:hasVersion / dcterms:created` (ETL build stamp) | 3 | 102 |
| `p6-v2-curator-sites` | all 44 sites owned by `/users/u/*` or `/users/a/*` | 44 | 2,541 |
| `p6-n1-datatype-census` | literal count by datatype for 12 numeric predicates | 4 | 5,668 |
| `p6-n2-typed-counts` | typed `CandidateEntity` and `Measure` counts | 2 | 38,061 |
| `p6-n3-measures-with-value` | typed Measures that carry `mo:value` | 1 | 920 |
| `p6-x1-exponent-decimals` | `xsd:decimal` literals with an exponent (illegal lexical form) | 1 | 13,794 |
| `p6-x2-exponent-decimals-rows` | those 6 literals with parent site | 6 | 571 |

Each id has `.rq`, `.json`, `.csv`, `.headers`, `.curlerr`, and `.meta.json`.

## Offline reproduction (no live store)

| file | what |
|---|---|
| `p6_repro.py` | Imports the **real** `KGSyncListener` from the clone and calls `handle_site_add`, `handle_site_update`, `handle_sample_add`, and `handle_sample_update` on synthetic inputs. `MINMOD_KG._sparql_query` and `_sparql_update` are rerouted to the `tdb2.tdbquery` and `tdb2.tdbupdate` CLIs of **Apache Jena 5.2.0**, the same version as `containers/fuseki/Dockerfile`, against a throwaway TDB2 directory in a temp folder that is deleted at the end. `httpx.post` is replaced with a function that raises, and the config points both endpoints at `127.0.0.1:1`. No server was started. Docker was not used because the daemon was not running. |
| `p6-repro-sparql.log` | **Every** INSERT DATA and DELETE/INSERT the listener generated, verbatim, step by step |
| `p6-repro-results.json` | `norm_literal` behaviour table, plus a per-step census of datatypes, orphans, doubles, and attached duplicates, plus a detection check |
| `p6-repro-stdout.txt` | runner output |

The Jena download was checked against Apache's published SHA-512, and the two values match.

**Detection check.** The production `.rq` files `p6-pf1`, `p6-o1`, and `p6-o2` were run against the repro store, which is known to contain the bug. They returned 5, 8, and 2 rows. So the production zeros mean "absent", not "the query cannot see it".

## Steps in the repro

| step | action | orphans | doubles | attached dupes |
|---|---|---|---|---|
| S1 | site add | 0 | 0 | 0 |
| S2 | site update, **name only** | 11 | 11 | 0 |
| S3 | site update, grade 1.25 → 1.3 | 11 (no new) | 11 | 0 |
| S4 | sample add | 11 | 11 | 0 |
| S5 | sample update, **name only** | 15 | 15 | 0 |
| S6 | sample update, top_depth_m 12.5 → 12.75 | 15 (no new) | 16 | **1** |
